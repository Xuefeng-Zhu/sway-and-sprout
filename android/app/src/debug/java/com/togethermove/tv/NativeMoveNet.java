package com.togethermove.tv;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
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

/** CPU-only, fixed full-frame letterbox baseline. Own and call on one worker thread. */
final class NativeMoveNet implements Closeable {
    private static final int SIZE = 192;
    private final Interpreter interpreter;
    private final ByteBuffer input = ByteBuffer.allocateDirect(SIZE * SIZE * 3).order(ByteOrder.nativeOrder());
    private final float[][][][] output = new float[1][1][17][3];
    private final int[] pixels = new int[SIZE * SIZE];
    private final Paint bilinear = new Paint(Paint.FILTER_BITMAP_FLAG);
    private final Bitmap padded = Bitmap.createBitmap(SIZE, SIZE, Bitmap.Config.ARGB_8888);
    private final Canvas canvas = new Canvas(padded);

    NativeMoveNet(ByteBuffer model) throws IOException {
        Interpreter.Options options = new Interpreter.Options().setNumThreads(2).setUseNNAPI(false);
        Interpreter candidate = new Interpreter(model, options);
        try {
            if (candidate.getInputTensorCount() != 1 || candidate.getOutputTensorCount() != 1) throw new IOException("model_tensor_count");
            check(candidate.getInputTensor(0), DataType.UINT8, new int[]{1, SIZE, SIZE, 3}, SIZE * SIZE * 3);
            check(candidate.getOutputTensor(0), DataType.FLOAT32, new int[]{1, 1, 17, 3}, 17 * 3 * 4);
        } catch (IOException | RuntimeException error) {
            candidate.close();
            padded.recycle();
            throw error;
        }
        interpreter = candidate;
    }

    private static void check(Tensor tensor, DataType type, int[] shape, int bytes) throws IOException {
        if (tensor.dataType() != type || !Arrays.equals(tensor.shape(), shape) || tensor.numBytes() != bytes) {
            throw new IOException("model_tensor_contract");
        }
    }

    Result infer(Bitmap frame) {
        long before = SystemClock.elapsedRealtimeNanos();
        PoseCoordinates.Plan plan = PoseCoordinates.plan(frame.getWidth(), frame.getHeight());
        CRC32 decodedProbe = new CRC32();
        // Bounded pixel probe distinguishes decoded bitmap changes without
        // allocating another full-frame buffer or retaining any source pixels.
        for (int row = 0; row < 4; row++) {
            for (int column = 0; column < 4; column++) {
                int pixel = frame.getPixel(column * (frame.getWidth() - 1) / 3,
                        row * (frame.getHeight() - 1) / 3);
                checksumInt(decodedProbe, pixel);
            }
        }
        canvas.drawColor(Color.BLACK);
        canvas.drawBitmap(frame, null, new Rect(plan.padLeft, plan.padTop,
                plan.padLeft + plan.resizedWidth, plan.padTop + plan.resizedHeight), bilinear);
        padded.getPixels(pixels, 0, SIZE, 0, 0, SIZE, SIZE);
        input.clear();
        long red = 0, green = 0, blue = 0;
        int nonzeroBytes = 0;
        for (int pixel : pixels) {
            // UINT8 RGB: no signed-int8 zero point, floating normalization, channel reversal or mirror.
            int r = (pixel >>> 16) & 255, g = (pixel >>> 8) & 255, b = pixel & 255;
            input.put((byte) r); input.put((byte) g); input.put((byte) b);
            red += r; green += g; blue += b;
            nonzeroBytes += (r == 0 ? 0 : 1) + (g == 0 ? 0 : 1) + (b == 0 ? 0 : 1);
        }
        input.rewind();
        CRC32 inputChecksum = new CRC32();
        inputChecksum.update(input.asReadOnlyBuffer());
        long prepared = SystemClock.elapsedRealtimeNanos();
        interpreter.run(input, output);
        long inferred = SystemClock.elapsedRealtimeNanos();
        int[] indices = {5, 6, 9, 10};
        PoseGestureMachine.Point[] points = new PoseGestureMachine.Point[4];
        float[] requiredRaw = new float[12];
        int invalidMapped = 0;
        for (int i = 0; i < indices.length; i++) {
            float[] raw = output[0][0][indices[i]];
            System.arraycopy(raw, 0, requiredRaw, i * 3, 3);
            points[i] = plan.restore(raw[0], raw[1], raw[2]);
            if (points[i] == null) {
                invalidMapped++;
                points[i] = new PoseGestureMachine.Point(0, 0, 0);
            }
        }
        CRC32 outputChecksum = new CRC32();
        for (float[] point : output[0][0]) {
            for (float value : point) checksumInt(outputChecksum, Float.floatToRawIntBits(value));
        }
        PoseGestureMachine.Point ls = points[0], rs = points[1], lw = points[2], rw = points[3];
        // MoveNet has keypoint scores, not a body-global confidence or person-count output.
        double minimum = Math.min(Math.min(ls.confidence, rs.confidence), Math.min(lw.confidence, rw.confidence));
        PoseGestureMachine.Observation observation = new PoseGestureMachine.Observation(ls, rs, lw, rw, minimum);
        return new Result(observation, (prepared - before) / 1000000.0, (inferred - prepared) / 1000000.0,
                minimum, decodedProbe.getValue(), inputChecksum.getValue(), outputChecksum.getValue(),
                red / (double) pixels.length, green / (double) pixels.length, blue / (double) pixels.length,
                nonzeroBytes, invalidMapped, requiredRaw, plan);
    }

    private static void checksumInt(CRC32 checksum, int value) {
        checksum.update(value >>> 24); checksum.update(value >>> 16);
        checksum.update(value >>> 8); checksum.update(value);
    }

    @Override public void close() {
        interpreter.close();
        padded.recycle();
    }

    static final class Result {
        final PoseGestureMachine.Observation observation;
        final double preprocessMs, inferenceMs, keypointMinimum;
        final long decodedProbeCrc32, inputCrc32, outputCrc32;
        final double meanR, meanG, meanB;
        final int nonzeroInputBytes, invalidMappedKeypoints;
        final float[] requiredRaw;
        final PoseCoordinates.Plan plan;
        Result(PoseGestureMachine.Observation observation, double preprocessMs, double inferenceMs,
               double keypointMinimum, long decodedProbeCrc32, long inputCrc32, long outputCrc32,
               double meanR, double meanG, double meanB, int nonzeroInputBytes,
               int invalidMappedKeypoints, float[] requiredRaw, PoseCoordinates.Plan plan) {
            this.observation = observation; this.preprocessMs = preprocessMs; this.inferenceMs = inferenceMs;
            this.keypointMinimum = keypointMinimum; this.decodedProbeCrc32 = decodedProbeCrc32;
            this.inputCrc32 = inputCrc32; this.outputCrc32 = outputCrc32;
            this.meanR = meanR; this.meanG = meanG; this.meanB = meanB;
            this.nonzeroInputBytes = nonzeroInputBytes; this.invalidMappedKeypoints = invalidMappedKeypoints;
            this.requiredRaw = requiredRaw; this.plan = plan;
        }
    }
}
