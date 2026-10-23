package com.togethermove.tv;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.SystemClock;
import org.tensorflow.lite.DataType;
import org.tensorflow.lite.Interpreter;
import org.tensorflow.lite.Tensor;
import java.io.Closeable;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import java.util.zip.CRC32;

/** CPU-only official Android crop flow; worker-owned state and sampled reference parity. */
final class NativeMoveNet implements Closeable {
    private final int inputSize;
    private final Interpreter interpreter;
    private final ByteBuffer input;
    private final float[][][][] output = new float[1][1][17][3];
    private final int[] pixels;
    private final byte[] rgb;
    private final boolean statelessCrop;
    private MoveNetCrop.Region crop;
    private int imageWidth, imageHeight;

    NativeMoveNet(ByteBuffer model) throws IOException { this(model, NativeVideoAssets.INT8_MODEL, true); }

    NativeMoveNet(ByteBuffer model, boolean statelessCrop) throws IOException { this(model, NativeVideoAssets.INT8_MODEL, statelessCrop); }

    NativeMoveNet(ByteBuffer model, NativeVideoAssets.ModelPin modelPin, boolean statelessCrop) throws IOException {
        if (modelPin != NativeVideoAssets.INT8_MODEL && modelPin != NativeVideoAssets.FLOAT16_MODEL
                && modelPin != NativeVideoAssets.THUNDER_MODEL) throw new IOException("unknown_model_pin");
        this.inputSize = modelPin.inputSize;
        this.input = ByteBuffer.allocateDirect(inputSize * inputSize * 3).order(ByteOrder.nativeOrder());
        this.pixels = new int[inputSize * inputSize];
        this.rgb = new byte[inputSize * inputSize * 3];
        this.statelessCrop = statelessCrop;
        Interpreter.Options options = new Interpreter.Options().setNumThreads(2).setUseNNAPI(false);
        Interpreter candidate = new Interpreter(model, options);
        try {
            if (candidate.getInputTensorCount() != 1 || candidate.getOutputTensorCount() != 1) throw new IOException("model_tensor_count");
            check(candidate.getInputTensor(0), DataType.UINT8, new int[]{1, inputSize, inputSize, 3}, inputSize * inputSize * 3);
            check(candidate.getOutputTensor(0), DataType.FLOAT32, new int[]{1, 1, 17, 3}, 17 * 3 * 4);
        } catch (IOException | RuntimeException error) {
            candidate.close();
            throw error;
        }
        interpreter = candidate;
    }

    private static void check(Tensor tensor, DataType type, int[] shape, int bytes) throws IOException {
        if (tensor.dataType() != type || !Arrays.equals(tensor.shape(), shape) || tensor.numBytes() != bytes
                || tensor.quantizationParams().getScale() != 0f || tensor.quantizationParams().getZeroPoint() != 0) {
            throw new IOException("model_tensor_contract");
        }
    }

    void resetTracking() { crop = null; }

    /** Official pose-classification still-image strategy: reset, then two same-image ROI refinements. */
    Result infer(Bitmap frame, boolean verifyReference) {
        if (!statelessCrop) return inferPass(frame, verifyReference);
        resetTracking();
        Result last = null;
        double prepared = 0, inference = 0, reference = 0, outputDelta = 0;
        double cropTime = 0, resizeTime = 0, packTime = 0;
        double referencePrepare = 0, referenceCompare = 0, referenceInference = 0;
        int byteDifferences = 0, byteDelta = 0;
        for (int pass = 0; pass < 3; pass++) {
            last = inferPass(frame, verifyReference);
            prepared += last.preprocessMs; inference += last.inferenceMs; reference += last.referenceMs;
            cropTime += last.cropMs; resizeTime += last.resizeMs; packTime += last.packMs;
            referencePrepare += last.referencePrepareMs;
            referenceCompare += last.referenceCompareMs;
            referenceInference += last.referenceInferenceMs;
            byteDifferences += last.parityByteDifferences;
            byteDelta = Math.max(byteDelta, last.parityMaxByteDelta);
            outputDelta = Math.max(outputDelta, last.parityOutputMaxDelta);
        }
        return new Result(last.observation, prepared, inference, last.keypointMinimum,
                last.decodedProbeCrc32, last.inputCrc32, last.outputCrc32, last.meanR, last.meanG, last.meanB,
                last.nonzeroInputBytes, last.invalidMappedKeypoints, last.requiredRaw, last.plan,
                last.imageWidth, last.imageHeight, last.defaultCrop, verifyReference,
                byteDifferences, byteDelta, outputDelta, reference, 3,
                cropTime, resizeTime, packTime, referencePrepare, referenceCompare, referenceInference);
    }

    private Result inferPass(Bitmap frame, boolean verifyReference) {
        long before = SystemClock.elapsedRealtimeNanos();
        if (crop == null || imageWidth != frame.getWidth() || imageHeight != frame.getHeight()) {
            imageWidth = frame.getWidth(); imageHeight = frame.getHeight();
            crop = MoveNetCrop.initial(imageWidth, imageHeight);
        }
        boolean usedDefaultCrop = crop.defaultCrop;
        MoveNetCrop.PixelPlan plan = crop.pixels(imageWidth, imageHeight, inputSize);
        CRC32 decodedProbe = new CRC32();
        for (int row = 0; row < 4; row++) for (int column = 0; column < 4; column++) {
            checksumInt(decodedProbe, frame.getPixel(column * (imageWidth - 1) / 3, row * (imageHeight - 1) / 3));
        }
        Bitmap detect = Bitmap.createBitmap(plan.detectWidth, plan.detectHeight, Bitmap.Config.ARGB_8888);
        Bitmap square = null, scaled = null;
        try {
            // Same source-space square/padding and floating origin as MoveNet.kt.
            new Canvas(detect).drawBitmap(frame, -plan.left, -plan.top, null);
            square = Bitmap.createBitmap(detect, plan.centerCropLeft, plan.centerCropTop, plan.squareSize, plan.squareSize);
            long cropped = SystemClock.elapsedRealtimeNanos();
            scaled = Bitmap.createScaledBitmap(square, inputSize, inputSize, true);
            scaled.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize);
            long resized = SystemClock.elapsedRealtimeNanos();
            input.clear();
            NativeRgbPacking.Totals totals = NativeRgbPacking.pack(pixels, rgb);
            input.put(rgb);
            input.rewind();
            CRC32 inputChecksum = new CRC32(); inputChecksum.update(rgb, 0, rgb.length);
            long prepared = SystemClock.elapsedRealtimeNanos();
            interpreter.run(input, output);
            long inferred = SystemClock.elapsedRealtimeNanos();
            int byteDifferences = 0, maxByteDelta = 0;
            double outputMaxDelta = 0;
            double referencePrepareMs = 0, referenceCompareMs = 0, referenceInferenceMs = 0;
            long parityStart = SystemClock.elapsedRealtimeNanos();
            long referencePrepared = parityStart, referenceInferenceStart = parityStart, referenceInferred = parityStart;
            if (verifyReference) {
                // Actual official Support API classes, same bitmap/crop and pinned model.
                ByteBuffer reference = MoveNetReferenceImage.prepare(detect, inputSize);
                referencePrepared = SystemClock.elapsedRealtimeNanos();
                ByteBuffer candidate = input.asReadOnlyBuffer(); candidate.rewind();
                if (reference.remaining() != candidate.remaining()) throw new IllegalStateException("reference_input_size");
                while (candidate.hasRemaining()) {
                    int delta = Math.abs((candidate.get() & 255) - (reference.get() & 255));
                    if (delta != 0) byteDifferences++;
                    maxByteDelta = Math.max(maxByteDelta, delta);
                }
                reference.rewind();
                float[][][][] referenceOutput = new float[1][1][17][3];
                referenceInferenceStart = SystemClock.elapsedRealtimeNanos();
                interpreter.run(reference, referenceOutput);
                referenceInferred = SystemClock.elapsedRealtimeNanos();
                for (int i = 0; i < 17; i++) for (int j = 0; j < 3; j++) {
                    outputMaxDelta = Math.max(outputMaxDelta, Math.abs((double) output[0][0][i][j] - referenceOutput[0][0][i][j]));
                }
            }
            long parityEnd = SystemClock.elapsedRealtimeNanos();
            double referenceMs = (parityEnd - parityStart) / 1000000.0;
            if (verifyReference) {
                referencePrepareMs = (referencePrepared - parityStart) / 1000000.0;
                referenceCompareMs = ((referenceInferenceStart - referencePrepared) + (parityEnd - referenceInferred)) / 1000000.0;
                referenceInferenceMs = (referenceInferred - referenceInferenceStart) / 1000000.0;
            }
            float[][] original = new float[17][3];
            for (int i = 0; i < 17; i++) {
                original[i][0] = plan.restoreX(output[0][0][i][1]);
                original[i][1] = plan.restoreY(output[0][0][i][0]);
                original[i][2] = output[0][0][i][2];
            }
            int[] indices = {5, 6, 9, 10};
            PoseGestureMachine.Point[] points = new PoseGestureMachine.Point[4];
            float[] requiredRaw = new float[12]; int invalidMapped = 0;
            for (int i = 0; i < 4; i++) {
                int index = indices[i]; float[] raw = output[0][0][index];
                System.arraycopy(raw, 0, requiredRaw, i * 3, 3);
                float x = original[index][0], y = original[index][1], confidence = raw[2];
                boolean valid = Float.isFinite(x) && Float.isFinite(y) && Float.isFinite(confidence)
                        && confidence >= 0 && confidence <= 1 && x >= 0 && x <= imageWidth && y >= 0 && y <= imageHeight
                        && raw[0] >= 0 && raw[0] <= 1 && raw[1] >= 0 && raw[1] <= 1;
                if (!valid) { invalidMapped++; points[i] = new PoseGestureMachine.Point(0, 0, 0); }
                else points[i] = new PoseGestureMachine.Point(x, y, confidence);
            }
            crop = MoveNetCrop.next(original, imageWidth, imageHeight);
            CRC32 outputChecksum = new CRC32();
            for (float[] point : output[0][0]) for (float value : point) checksumInt(outputChecksum, Float.floatToRawIntBits(value));
            PoseGestureMachine.Point ls = points[0], rs = points[1], lw = points[2], rw = points[3];
            double minimum = Math.min(Math.min(ls.confidence, rs.confidence), Math.min(lw.confidence, rw.confidence));
            PoseGestureMachine.Observation observation = new PoseGestureMachine.Observation(ls, rs, lw, rw, minimum,
                    optionalPoint(original, output[0][0], 11, imageWidth, imageHeight),
                    optionalPoint(original, output[0][0], 12, imageWidth, imageHeight));
            return new Result(observation, (prepared - before) / 1000000.0, (inferred - prepared) / 1000000.0,
                    minimum, decodedProbe.getValue(), inputChecksum.getValue(), outputChecksum.getValue(),
                    totals.red / (double) pixels.length, totals.green / (double) pixels.length, totals.blue / (double) pixels.length,
                    totals.nonzero, invalidMapped, requiredRaw, plan, imageWidth, imageHeight, usedDefaultCrop,
                    verifyReference, byteDifferences, maxByteDelta, outputMaxDelta, referenceMs, 1,
                    (cropped - before) / 1000000.0, (resized - cropped) / 1000000.0,
                    (prepared - resized) / 1000000.0, referencePrepareMs, referenceCompareMs, referenceInferenceMs);
        } finally {
            if (scaled != null && scaled != square && scaled != detect) scaled.recycle();
            if (square != null && square != detect) square.recycle();
            detect.recycle();
        }
    }

    private static PoseGestureMachine.Point optionalPoint(float[][] original, float[][] raw, int index, int width, int height) {
        float x = original[index][0], y = original[index][1], confidence = raw[index][2];
        boolean valid = Float.isFinite(x) && Float.isFinite(y) && Float.isFinite(confidence)
                && confidence >= 0 && confidence <= 1 && x >= 0 && x <= width && y >= 0 && y <= height
                && raw[index][0] >= 0 && raw[index][0] <= 1 && raw[index][1] >= 0 && raw[index][1] <= 1;
        return valid ? new PoseGestureMachine.Point(x, y, confidence) : new PoseGestureMachine.Point(0, 0, 0);
    }

    private static void checksumInt(CRC32 checksum, int value) {
        checksum.update(value >>> 24); checksum.update(value >>> 16);
        checksum.update(value >>> 8); checksum.update(value);
    }

    @Override public void close() {
        interpreter.close();
    }

    static final class Result {
        final PoseGestureMachine.Observation observation;
        final double preprocessMs, inferenceMs, keypointMinimum;
        final long decodedProbeCrc32, inputCrc32, outputCrc32;
        final double meanR, meanG, meanB;
        final int nonzeroInputBytes, invalidMappedKeypoints;
        final float[] requiredRaw;
        final MoveNetCrop.PixelPlan plan;
        final int imageWidth, imageHeight, modelCalls;
        final boolean defaultCrop, parityChecked;
        final int parityByteDifferences, parityMaxByteDelta;
        final double parityOutputMaxDelta, referenceMs;
        // Contiguous preprocessing phases. Crop includes plan/probe checksums,
        // bitmap allocation, drawing and square creation; resize includes getPixels;
        // pack includes RGB packing, diagnostic sums/nonzero counts and input CRC.
        final double cropMs, resizeMs, packMs;
        // Comparison includes buffer/output allocation and byte/output comparisons.
        // All reference phases are zero when verification is disabled. Existing
        // referenceMs still measures the whole branch, including its clock overhead.
        final double referencePrepareMs, referenceCompareMs, referenceInferenceMs;
        Result(PoseGestureMachine.Observation observation, double preprocessMs, double inferenceMs,
               double keypointMinimum, long decodedProbeCrc32, long inputCrc32, long outputCrc32,
               double meanR, double meanG, double meanB, int nonzeroInputBytes,
               int invalidMappedKeypoints, float[] requiredRaw, MoveNetCrop.PixelPlan plan, int imageWidth, int imageHeight, boolean defaultCrop,
               boolean parityChecked, int parityByteDifferences, int parityMaxByteDelta, double parityOutputMaxDelta, double referenceMs, int modelCalls,
               double cropMs, double resizeMs, double packMs,
               double referencePrepareMs, double referenceCompareMs, double referenceInferenceMs) {
            this.observation = observation; this.preprocessMs = preprocessMs; this.inferenceMs = inferenceMs;
            this.keypointMinimum = keypointMinimum; this.decodedProbeCrc32 = decodedProbeCrc32;
            this.inputCrc32 = inputCrc32; this.outputCrc32 = outputCrc32;
            this.meanR = meanR; this.meanG = meanG; this.meanB = meanB;
            this.nonzeroInputBytes = nonzeroInputBytes; this.invalidMappedKeypoints = invalidMappedKeypoints;
            this.requiredRaw = requiredRaw; this.plan = plan; this.imageWidth = imageWidth; this.imageHeight = imageHeight;
            this.defaultCrop = defaultCrop; this.parityChecked = parityChecked;
            this.parityByteDifferences = parityByteDifferences; this.parityMaxByteDelta = parityMaxByteDelta;
            this.parityOutputMaxDelta = parityOutputMaxDelta; this.referenceMs = referenceMs; this.modelCalls = modelCalls;
            this.cropMs = cropMs; this.resizeMs = resizeMs; this.packMs = packMs;
            this.referencePrepareMs = referencePrepareMs; this.referenceCompareMs = referenceCompareMs;
            this.referenceInferenceMs = referenceInferenceMs;
        }
    }
}
