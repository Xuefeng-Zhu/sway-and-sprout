package com.togethermove.tv;

import android.app.Activity;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Log;
import android.widget.TextView;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/** Opt-in finite public-image diagnostic. No WebView, scoring, persistence or camera. */
public final class NativeCalibrationActivity extends Activity {
    private static final String TAG = "SwayCalibration";
    private static final ExecutorService WORKER = Executors.newSingleThreadExecutor();
    private volatile boolean cancelled, destroyed;
    private boolean started;
    private Future<?> task;
    private String runId, split;
    private NativeVideoAssets.ModelPin pin;
    private TextView status;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        status = new TextView(this); status.setText("Local keypoint calibration — camera off"); setContentView(status);
        try {
            runId = getIntent().getStringExtra("calibrationRunId");
            if (runId == null || !UUID.fromString(runId).toString().equals(runId)) throw new IllegalArgumentException("run_id");
            split = getIntent().getStringExtra("calibrationSplit");
            if (!("calibration".equals(split) || "heldout".equals(split))) throw new IllegalArgumentException("split");
            String model = getIntent().getStringExtra("nativeModel");
            if ("float16".equals(model)) pin = NativeVideoAssets.FLOAT16_MODEL;
            else if ("int8".equals(model)) pin = NativeVideoAssets.INT8_MODEL;
            else throw new IllegalArgumentException("model");
            if (!NativeCalibrationPins.ENABLED) throw new IllegalStateException("calibration_not_prepared");
        } catch (RuntimeException error) {
            cancelled = true; reportFailure(error); status.setText("Calibration unavailable; camera remains off");
        }
    }
    @Override public void onResume() {
        super.onResume();
        if (!started && !cancelled) { started = true; task = WORKER.submit(this::runDataset); }
    }
    @Override public void onPause() { cancel(); super.onPause(); }
    @Override public void onDestroy() { destroyed = true; cancel(); super.onDestroy(); }
    private void cancel() { cancelled = true; if (task != null) task.cancel(true); }
    private boolean stopping() { return cancelled || Thread.currentThread().isInterrupted(); }

    private void runDataset() {
        NativeMoveNet model = null; int processed = 0; boolean complete = false, resourcesClosed = true;
        long startedAt = SystemClock.elapsedRealtimeNanos();
        try {
            List<NativeCalibrationAssets.Image> images = NativeCalibrationAssets.images(getAssets(), split);
            if (stopping()) return;
            model = new NativeMoveNet(NativeCalibrationAssets.model(getAssets(), pin), pin, true);
            JSONObject began = base("started"); put(began, "expectedSamples", images.size()); emit(began);
            for (NativeCalibrationAssets.Image image : images) {
                if (stopping()) return;
                long before = SystemClock.elapsedRealtimeNanos();
                Bitmap bitmap = NativeCalibrationAssets.bitmap(getAssets(), image);
                NativeMoveNet.Result result;
                try { result = model.infer(bitmap, false); }
                finally { bitmap.recycle(); }
                if (stopping()) return;
                JSONObject row = base("sample");
                put(row, "id", image.id); put(row, "imageSha256", image.sha256);
                put(row, "width", image.width); put(row, "height", image.height);
                put(row, "minimumScore", result.observation.confidence); // Retained legacy diagnostic alias.
                put(row, "classifierMinimumScore", result.observation.confidence);
                double rawMinimumScore = Math.min(Math.min(result.requiredRaw[2], result.requiredRaw[5]),
                        Math.min(result.requiredRaw[8], result.requiredRaw[11]));
                put(row, "rawMinimumScore", rawMinimumScore);
                put(row, "invalidMappedKeypoints", result.invalidMappedKeypoints);
                put(row, "preprocessMs", result.preprocessMs); put(row, "inferenceMs", result.inferenceMs);
                put(row, "sampleMs", (SystemClock.elapsedRealtimeNanos() - before) / 1000000.0);
                String[] names = {"leftShoulder", "rightShoulder", "leftWrist", "rightWrist"};
                PoseGestureMachine.Point[] points = {result.observation.leftShoulder, result.observation.rightShoulder,
                        result.observation.leftWrist, result.observation.rightWrist};
                for (int joint = 0; joint < names.length; joint++) {
                    JSONObject point = new JSONObject();
                    // Preserve unmodified native score even when the classifier would mask an invalid mapping.
                    float rawY = result.requiredRaw[joint * 3], rawX = result.requiredRaw[joint * 3 + 1];
                    float rawScore = result.requiredRaw[joint * 3 + 2];
                    put(point, "x", (double) result.plan.restoreX(rawX)); put(point, "y", (double) result.plan.restoreY(rawY));
                    put(point, "score", (double) rawScore); put(point, "normalizedX", (double) rawX); put(point, "normalizedY", (double) rawY);
                    put(point, "classifierMappedX", points[joint].x); put(point, "classifierMappedY", points[joint].y);
                    put(point, "classifierScore", points[joint].confidence);
                    put(row, names[joint], point);
                }
                emit(row); processed++;
                final int shown = processed;
                runOnUiThread(() -> { if (!destroyed && !isFinishing()) status.setText("Local keypoint calibration: " + shown + "/" + images.size() + " — camera off"); });
            }
            complete = true;
            JSONObject finished = base("finished"); put(finished, "samples", processed);
            put(finished, "wallMs", (SystemClock.elapsedRealtimeNanos() - startedAt) / 1000000.0); emit(finished);
        } catch (Exception | LinkageError error) {
            reportFailure(error);
        } finally {
            try { if (model != null) model.close(); }
            catch (RuntimeException | LinkageError error) { resourcesClosed = false; reportFailure(error); }
            JSONObject closed = base("closed"); put(closed, "resourcesClosed", resourcesClosed);
            put(closed, "complete", complete); put(closed, "samples", processed); put(closed, "cancelled", cancelled); emit(closed);
        }
    }
    private JSONObject base(String kind) {
        JSONObject out = new JSONObject();
        put(out, "kind", kind); put(out, "runId", runId == null ? "invalid" : runId);
        put(out, "datasetId", NativeCalibrationPins.DATASET_ID); put(out, "manifestSha256", NativeCalibrationPins.MANIFEST_SHA256);
        put(out, "split", split == null ? "invalid" : split); put(out, "modelId", pin == null ? "invalid" : pin.id);
        put(out, "modelSha256", pin == null ? "invalid" : pin.sha256);
        put(out, "inputSize", pin == null ? 0 : pin.inputSize); put(out, "engine", "litert");
        put(out, "engineVersion", NativeVideoAssets.RUNTIME_VERSION); put(out, "profile", "image");
        put(out, "modelInferencesPerImage", 3); put(out, "referenceCalls", 0);
        put(out, "scoreSemantics", "native-movenet-joint-score-uncalibrated");
        put(out, "coordinateSemantics", "official-crop-inverse-source-pixels");
        put(out, "cameraEnabled", false); put(out, "scoringEnabled", false); return out;
    }
    private void reportFailure(Throwable error) {
        JSONObject failed = base("failure"); put(failed, "errorType", error.getClass().getSimpleName());
        String reason = error.getMessage() == null ? "unspecified" : error.getMessage().replaceAll("[^A-Za-z0-9_. -]", "_");
        put(failed, "reason", reason.substring(0, Math.min(120, reason.length()))); emit(failed);
    }
    private static void put(JSONObject out, String key, Object value) {
        try { out.put(key, value); } catch (JSONException error) { throw new IllegalArgumentException("nonfinite_diagnostic", error); }
    }
    private static void emit(JSONObject out) { Log.i(TAG, out.toString()); }
}
