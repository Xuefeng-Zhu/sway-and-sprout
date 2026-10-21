package com.togethermove.tv;

import android.annotation.TargetApi;
import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.media.MediaMetadataRetriever;
import android.os.Build;
import android.os.Debug;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.webkit.WebResourceResponse;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.ExecutionException;

/**
 * Debug-only bundled video inference, inside the Android app process.
 * Frames exist only in memory. There is no camera, image export, socket or sidecar.
 * One bounded worker owns the decoder and CPU interpreter. File time drives the
 * classifier; monotonic wall time drives transport leases and event freshness.
 */
public final class NativeVideoReplay implements MotionSource {
    private static final String TAG = "SwayNativeVideo";
    private static final long EVENT_TTL_MS = 1500;
    // Serial process-wide ownership also covers Activity recreation while an old
    // decoder finishes its in-flight frame. No second graph starts in parallel.
    private static final ExecutorService WORKER = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "SwayNativeVideo");
        thread.setDaemon(true);
        return thread;
    });
    private final Object lock = new Object();
    private final AssetManager assets;
    private final String configAsset;
    private final NativeVideoAssets.ModelPin modelPin;
    private final boolean statelessCrop;
    private final PoseGestureMachine machine = new PoseGestureMachine();
    private final ActivityMachine activity = new ActivityMachine();
    private final List<PendingEvent> pending = new ArrayList<>();
    private final List<PendingEvent> history = new ArrayList<>();
    private final LinkedHashSet<String> retiredClients = new LinkedHashSet<>();
    private final Future<?> workerTask;
    private Thread workerThread;
    private NativeVideoAssets config;
    private Control context;
    private boolean verified;
    private boolean failed;
    private boolean closed;
    private boolean hostSuspended;
    private boolean hostPaused;
    private boolean leaseExpired;
    private boolean completed;
    private boolean resourcesClosed;
    private boolean cleanupSucceeded = true;
    private long suspendedRevision = -1;
    private long epoch;
    private long seq;
    private long ackSeq;
    private String ackExpected = "left";
    private String failure = "";
    private long lastPollWall;
    private long nextFrameWall;
    private int frameIndex;
    private RunStats stats = new RunStats();

    public NativeVideoReplay(Context context) {
        this(context, "verification/clear.json");
    }

    public NativeVideoReplay(Context context, String configAsset) { this(context, configAsset, true); }

    public NativeVideoReplay(Context context, String configAsset, boolean statelessCrop) {
        this.statelessCrop = statelessCrop;
        assets = context.getApplicationContext().getAssets();
        this.configAsset = configAsset;
        this.modelPin = NativeVideoAssets.modelPin(configAsset);
        workerTask = WORKER.submit(this::run);
    }

    @Override public WebResourceResponse events(String method, String rawQuery) {
        if (!"GET".equals(method)) return error(405, "method_not_allowed");
        final Control incoming;
        try { incoming = Control.parse(rawQuery); }
        catch (IllegalArgumentException error) { return error(400, "invalid_motion_query"); }
        synchronized (lock) {
            if (closed) return error(410, "video_source_closed");
            long now = wall();
            String conflict = applyControl(incoming, now);
            if (conflict != null) return error(409, conflict);
            lock.notifyAll();
            return json(200, packet(incoming, now));
        }
    }

    /** Metadata only: no frame pixels and no transport lease/ACK mutation. */
    @Override public WebResourceResponse preview(String method, String rawQuery) {
        if (!"GET".equals(method)) return error(405, "method_not_allowed");
        final Control incoming;
        try { incoming = Control.parse(rawQuery); }
        catch (IllegalArgumentException error) { return error(400, "invalid_motion_query"); }
        synchronized (lock) {
            JSONObject output = identity(incoming);
            put(output, "available", false);
            put(output, "status", closed ? "stopped" : failed ? "camera-error" : completed ? "paused" :
                    isRunning(wall()) ? "waiting" : "paused");
            put(output, "expected", expected());
            put(output, "heldMs", heldMs());
            return json(200, output);
        }
    }

    @Override public void suspend() {
        synchronized (lock) {
            if (closed) return;
            hostPaused = true;
            hostSuspended = true;
            suspendedRevision = context == null ? -1 : context.revision;
            invalidate("paused");
            report("suspended");
            lock.notifyAll();
        }
    }

    @Override public void resume() {
        synchronized (lock) {
            if (closed) return;
            hostPaused = false;
            if (hostSuspended && context != null) {
                suspendedRevision = Math.max(suspendedRevision, context.revision);
            }
            lock.notifyAll();
        }
    }

    @Override public void close() {
        Thread activeThread;
        synchronized (lock) {
            if (closed) return;
            closed = true;
            epoch++;
            lose("paused");
            pending.clear();
            activeThread = workerThread;
            if (activeThread != null) activeThread.interrupt();
            lock.notifyAll();
        }
        // Activity teardown must not wait for a decoder/native invocation on the
        // UI thread. The one process-wide serial worker drains and closes its
        // resources before another NativeVideoReplay task can initialize.
        if (Looper.myLooper() != Looper.getMainLooper() && Thread.currentThread() != activeThread) {
            try { workerTask.get(5, TimeUnit.SECONDS); }
            catch (InterruptedException error) { Thread.currentThread().interrupt(); }
            catch (TimeoutException error) { Log.w(TAG, "{\"kind\":\"stop-pending\",\"reason\":\"worker-finishing-inflight-frame\"}"); }
            catch (ExecutionException error) { Log.e(TAG, "{\"kind\":\"worker-stop-failure\"}"); }
        }
    }

    /** Caller holds lock. One lease, revision, round, and acknowledgement ledger. */
    private String applyControl(Control incoming, long now) {
        if (retiredClients.contains(incoming.clientId)) return "retired_client";
        if (context != null && !context.clientId.equals(incoming.clientId)) {
            if (ReplayFrameGuard.leaseFresh(now, lastPollWall)) return "client_lease_owned";
            if (retiredClients.size() >= 32) return "client_bound_reached";
            retiredClients.add(context.clientId);
            report("client-replaced");
            context = null;
        }
        if (context != null) {
            if (incoming.revision < context.revision) return "stale_revision";
            if (!MotionQuery.policyChangeAllowed(context.roundId, context.policy, incoming.roundId, incoming.policy)) return "policy_change_requires_new_round";
            if (incoming.revision == context.revision && (!incoming.roundId.equals(context.roundId)
                    || incoming.active != context.active || !incoming.mode.equals(context.mode)
                    || !incoming.policy.equals(context.policy))) return "revision_conflict";
        }
        if (incoming.after > seq) return "future_ack";
        long pollGap = context == null ? 0 : Math.max(0, now - lastPollWall);
        boolean newRound = context == null || !incoming.roundId.equals(context.roundId);
        boolean newRevision = context == null || incoming.revision != context.revision;
        if (newRound) {
            if (context != null) report("round-replaced");
            machine.newRound();
            activity.newRound();
            pending.clear();
            history.clear();
            ackSeq = 0;
            ackExpected = "activity".equals(incoming.policy) ? "any" : "left";
            frameIndex = 0;
            stats = new RunStats();
            completed = false;
            nextFrameWall = 0;
            epoch++;
        } else {
            acknowledge(incoming.after);
            if (newRevision || leaseExpired || !ReplayFrameGuard.leaseFresh(now, lastPollWall)) {
                if (!ReplayFrameGuard.leaseFresh(now, lastPollWall)) stats.controlLeaseBreaks++;
                invalidate("waiting");
            }
        }
        context = incoming;
        stats.lastPollGapMs = pollGap;
        lastPollWall = now;
        leaseExpired = false;
        // Lifecycle suspension requires a newer control revision before resuming;
        // an in-flight GET from before onPause cannot restart video advancement.
        if (hostSuspended && !hostPaused && incoming.revision > suspendedRevision) hostSuspended = false;
        expirePending(now);
        if (!incoming.active || hostSuspended || hostPaused) lose("paused");
        if (!incoming.active && stats.acceptedFrames > 0 && (newRevision || newRound)) report("paused");
        return null;
    }

    private void acknowledge(long after) {
        if (after < ackSeq) return;
        for (PendingEvent event : history) {
            if (event.seq > ackSeq && event.seq <= after) {
                if (!activityPolicy()) ackExpected = "left-raise".equals(event.gesture) ? "right" : "left";
                stats.acknowledgedEvents++;
            }
        }
        ackSeq = after;
        pending.removeIf(event -> event.seq <= after);
        if (activityPolicy()) return;
        String expected = ackExpected;
        for (PendingEvent event : pending) {
            if (!event.gesture.equals(expected + "-raise")) {
                invalidate("waiting");
                return;
            }
            expected = "left".equals(expected) ? "right" : "left";
        }
        if (!machine.expected.equals(expected)) {
            epoch++;
            stats.pose.breakSequence();
            machine.resetTemporal();
            machine.expected = expected;
            nextFrameWall = 0;
        }
    }

    private void expirePending(long now) {
        for (PendingEvent event : pending) {
            if (now - event.createdWall > EVENT_TTL_MS) {
                invalidate("waiting");
                return;
            }
        }
    }

    private void invalidate(String status) {
        epoch++;
        pending.clear();
        stats.pose.breakSequence();
        machine.resetTemporal();
        machine.expected = ackExpected;
        machine.status = status;
        activity.lost(status);
        nextFrameWall = 0;
    }

    private boolean activityPolicy() { return context != null && "activity".equals(context.policy); }
    private String expected() { return activityPolicy() ? activity.expected : machine.expected; }
    private String status() { return activityPolicy() ? activity.status : machine.status; }
    private boolean armed() { return activityPolicy() ? activity.armed : machine.armed; }
    private int heldMs() { return activityPolicy() ? activity.heldMs : machine.heldMs; }
    private void lose(String value) { machine.lost(value); activity.lost(value); }
    private boolean lifecycleActive() {
        return verified && !failed && !completed && context != null && context.active && !hostSuspended && !hostPaused;
    }
    private boolean isRunning(long now) {
        return lifecycleActive() && !closed && !leaseExpired && ReplayFrameGuard.leaseFresh(now, lastPollWall);
    }

    /** Caller holds lock; used both after decode and after inference. */
    private int frameDiscardReason(long token) {
        int reason = ReplayFrameGuard.reason(closed, token, epoch, lifecycleActive(), wall(), lastPollWall);
        return reason == ReplayFrameGuard.ACCEPT && leaseExpired ? ReplayFrameGuard.LEASE_EXPIRED : reason;
    }

    private JSONObject packet(Control incoming, long now) {
        JSONObject output = identity(incoming);
        put(output, "protocol", 1);
        put(output, "runtime", runtime());
        put(output, "status", failed ? "camera-error" : completed || !incoming.active || hostSuspended || hostPaused || leaseExpired
                ? "paused" : status());
        put(output, "expected", expected());
        put(output, "heldMs", heldMs());
        put(output, "seq", seq);
        JSONArray events = new JSONArray();
        for (PendingEvent event : pending) {
            JSONObject row = new JSONObject();
            put(row, "seq", event.seq);
            put(row, "roundId", incoming.roundId);
            put(row, "gesture", event.gesture);
            put(row, "confidence", event.confidence);
            put(row, "ageMs", Math.max(0, now - event.createdWall));
            events.put(row);
        }
        put(output, "events", events);
        JSONObject metrics = new JSONObject();
        put(metrics, "armed", armed());
        put(metrics, "decodedFrames", stats.decodedFrames);
        put(metrics, "attemptedFrames", stats.attemptedFrames);
        put(metrics, "acceptedFrames", stats.acceptedFrames);
        put(metrics, "discardedEpochFrames", stats.discardedEpochFrames);
        put(metrics, "videoFrames", config == null ? 0 : config.frames);
        put(metrics, "fileMs", config == null ? 0 : frameIndex * 1000.0 / config.fps);
        put(metrics, "fps", config == null ? 0 : config.fps);
        put(metrics, "decodeMs", stats.lastDecodeMs);
        put(metrics, "preprocessMs", stats.lastPreprocessMs);
        put(metrics, "inferenceMs", stats.lastInferenceMs);
        put(metrics, "keypointMinimum", stats.lastMinimum);
        put(metrics, "nativeRecognizedEvents", stats.observed.size());
        put(metrics, "acknowledgedEvents", stats.acknowledgedEvents);
        put(metrics, "fullFileProcessed", completed);
        put(metrics, "singlePoseAssumption", true);
        put(metrics, "fixedFullFrameLetterbox", false);
        put(metrics, "dynamicPersonCrop", true);
        put(metrics, "statelessCropRefinement", statelessCrop);
        put(metrics, "modelInferencesPerFrame", statelessCrop ? 3 : 1);
        put(metrics, "cameraEnabled", false);
        put(metrics, "controlEpoch", epoch);
        put(metrics, "lastPollGapMs", stats.lastPollGapMs);
        put(metrics, "controlLeaseBreaks", stats.controlLeaseBreaks);
        put(metrics, "lastDiscardReason", stats.lastDiscardReason);
        put(metrics, "skippedStaleInferences", stats.skippedStaleInferences);
        put(output, "metrics", metrics);
        if (failed) put(output, "error", failure);
        return output;
    }

    private JSONObject runtime() {
        JSONObject output = new JSONObject();
        put(output, "engine", "litert");
        put(output, "engineVersion", NativeVideoAssets.RUNTIME_VERSION);
        put(output, "platform", "android");
        put(output, "modelSha256", modelPin.sha256);
        put(output, "modelId", modelPin.id);
        put(output, "inputSize", modelPin.inputSize);
        put(output, "verified", verified);
        return output;
    }

    private static JSONObject identity(Control incoming) {
        JSONObject output = new JSONObject();
        put(output, "source", "video");
        put(output, "clientId", incoming.clientId);
        put(output, "roundId", incoming.roundId);
        put(output, "revision", incoming.revision);
        put(output, "active", incoming.active);
        put(output, "mode", incoming.mode);
        put(output, "policy", incoming.policy);
        return output;
    }

    @TargetApi(28)
    private void run() {
        NativeMoveNet model = null;
        MediaMetadataRetriever video = null;
        try {
            synchronized (lock) {
                workerThread = Thread.currentThread();
                if (closed) return;
            }
            if (Build.VERSION.SDK_INT < 28) throw new IOException("recorded_video_requires_api_28");
            NativeVideoAssets loaded = new NativeVideoAssets(assets, configAsset);
            model = new NativeMoveNet(loaded.modelBuffer, loaded.modelPin, statelessCrop);
            video = new MediaMetadataRetriever();
            try (AssetFileDescriptor file = assets.openFd(loaded.videoAsset)) {
                if (file.getLength() != loaded.videoBytes) throw new IOException("fixture_fd_size_mismatch");
                video.setDataSource(file.getFileDescriptor(), file.getStartOffset(), file.getLength());
            }
            validateVideo(video, loaded);
            synchronized (lock) {
                config = loaded;
                if (closed) return;
                verified = true;
                Log.i(TAG, logBase("init").toString());
                lock.notifyAll();
            }
            long inferenceEpoch = Long.MIN_VALUE;
            while (true) {
                long token;
                long attemptId;
                int index;
                String attemptRound;
                RunStats attemptStats;
                synchronized (lock) {
                    while (!closed) {
                        long now = wall();
                        if (context != null && context.active && !leaseExpired && !ReplayFrameGuard.leaseFresh(now, lastPollWall)) {
                            leaseExpired = true;
                            stats.controlLeaseBreaks++;
                            invalidate("paused");
                            report("lease-expired");
                        }
                        expirePending(now);
                        if (isRunning(now) && now >= nextFrameWall) break;
                        lock.wait(isRunning(now) ? Math.max(1, Math.min(100, nextFrameWall - now)) : 100);
                    }
                    if (closed) break;
                    token = epoch;
                    index = frameIndex;
                    attemptStats = stats;
                    attemptId = ++attemptStats.attemptedFrames;
                    attemptRound = context.roundId;
                }
                if (token != inferenceEpoch) { model.resetTracking(); inferenceEpoch = token; }
                ReplayAttemptTiming.Sample started = timingSample();
                Bitmap bitmap;
                try { bitmap = video.getFrameAtIndex(index); }
                catch (RuntimeException | LinkageError error) {
                    ReplayAttemptTiming.Sample decodeFailed = timingSample();
                    synchronized (lock) {
                        frameAttempt(attemptId, attemptRound, index, token, "decode-error", -1,
                                new ReplayAttemptTiming(started, decodeFailed, timingSample(), null), null);
                    }
                    throw error;
                }
                ReplayAttemptTiming.Sample decoded = timingSample();
                if (bitmap == null) {
                    synchronized (lock) {
                        frameAttempt(attemptId, attemptRound, index, token, "decode-error", -1,
                                new ReplayAttemptTiming(started, decoded, timingSample(), null), null);
                    }
                    throw new IOException("video_decode_returned_no_frame");
                }
                int beforeInference;
                synchronized (lock) {
                    // Decode may have outlived its control epoch. Do not spend
                    // three inference passes on an already-invalid frame.
                    attemptStats.decodedFrames++;
                    expirePending(wall());
                    beforeInference = frameDiscardReason(token);
                    if (beforeInference != ReplayFrameGuard.ACCEPT) {
                        attemptStats.lastDiscardReason = beforeInference;
                        attemptStats.discardedEpochFrames++;
                        attemptStats.skippedStaleInferences++;
                        frameAttempt(attemptId, attemptRound, index, token, "decode-discard", beforeInference,
                                new ReplayAttemptTiming(started, decoded, timingSample(), null), null);
                    }
                }
                if (beforeInference != ReplayFrameGuard.ACCEPT) {
                    bitmap.recycle();
                    continue;
                }
                NativeMoveNet.Result result;
                ReplayAttemptTiming.Sample modelStarted = timingSample();
                try { result = model.infer(bitmap, index < 3 || index % 30 == 0 || index + 1 == loaded.frames); }
                catch (RuntimeException | LinkageError error) {
                    ReplayAttemptTiming.Sample inferenceFailed = timingSample();
                    synchronized (lock) {
                        frameAttempt(attemptId, attemptRound, index, token, "inference-error", -1,
                                new ReplayAttemptTiming(started, decoded, modelStarted, inferenceFailed, timingSample()), null);
                    }
                    throw error;
                }
                finally { bitmap.recycle(); }
                ReplayAttemptTiming.Sample processingEnd = timingSample();
                synchronized (lock) {
                    expirePending(wall());
                    int discardReason = frameDiscardReason(token);
                    ReplayAttemptTiming timing = new ReplayAttemptTiming(started, decoded, modelStarted, processingEnd, timingSample());
                    if (discardReason != ReplayFrameGuard.ACCEPT) {
                        // A new round can replace stats while this frame runs.
                        // Attribute discarded work to its original round only.
                        attemptStats.lastDiscardReason = discardReason;
                        attemptStats.discardedEpochFrames++;
                        frameAttempt(attemptId, attemptRound, index, token, "inference-discard", discardReason, timing, result);
                        continue;
                    }
                    stats.lastDiscardReason = ReplayFrameGuard.ACCEPT;
                    frameAttempt(attemptId, attemptRound, index, token, "accepted", ReplayFrameGuard.ACCEPT, timing, result);
                    double decodeMs = timing.decWallMs();
                    // Preserve historical frameMean/pace semantics: processing ends before the decision lock wait.
                    double totalMs = timing.processingWallMs();
                    stats.record(decodeMs, result, totalMs);
                    PoseGestureMachine.Event recognized = activityPolicy()
                            ? activity.update(result.observation, index * 1000.0 / loaded.fps)
                            : machine.update(result.observation, index * 1000.0 / loaded.fps);
                    if (!activityPolicy()) stats.pose.observe(result, index * 1000.0 / loaded.fps, machine);
                    JSONObject poseFrame = new JSONObject();
                    put(poseFrame, "kind", "pose-frame"); put(poseFrame, "configAsset", configAsset);
                    put(poseFrame, "frameIndex", index); put(poseFrame, "fileMs", index * 1000.0 / loaded.fps);
                    put(poseFrame, "confidence", result.observation.confidence);
                    PoseGestureMachine.Point[] framePoints = {result.observation.leftShoulder, result.observation.rightShoulder,
                            result.observation.leftWrist, result.observation.rightWrist};
                    String[] frameNames = {"ls", "rs", "lw", "rw"};
                    for (int joint = 0; joint < 4; joint++) {
                        put(poseFrame, frameNames[joint] + "X", framePoints[joint].x);
                        put(poseFrame, frameNames[joint] + "Y", framePoints[joint].y);
                        put(poseFrame, frameNames[joint] + "Score", framePoints[joint].confidence);
                    }
                    put(poseFrame, "status", status()); put(poseFrame, "armed", armed());
                    put(poseFrame, "policy", context.policy);
                    Log.i(TAG, poseFrame.toString());
                    if (index < 3 || index % 30 == 0 || index + 1 == loaded.frames) {
                        frameDiagnostic(result, index, index * 1000.0 / loaded.fps);
                    }
                    if (recognized != null) {
                        PendingEvent event = new PendingEvent(++seq, recognized.gesture, recognized.confidence, wall());
                        pending.add(event);
                        history.add(event);
                        stats.observed.add(recognized.gesture);
                        if (pending.size() > 64 || history.size() > 64) throw new IOException("event_bound_exceeded");
                        JSONObject emitted = logBase("event");
                        put(emitted, "seq", seq);
                        put(emitted, "gesture", recognized.gesture);
                        put(emitted, "confidence", recognized.confidence);
                        put(emitted, "eventFileMs", index * 1000.0 / loaded.fps);
                        Log.i(TAG, emitted.toString());
                    }
                    frameIndex++;
                    nextFrameWall = wall() + Math.max(0, Math.round(1000.0 / loaded.fps - totalMs));
                    if (frameIndex >= loaded.frames) {
                        completed = true;
                        lose("paused");
                        report("finished");
                    }
                }
            }
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
        } catch (IOException | JSONException | RuntimeException | LinkageError error) {
            synchronized (lock) {
                failed = true;
                failure = failureCode(error);
                invalidate("camera-error");
                JSONObject report = logBase("failure");
                put(report, "reason", failure);
                put(report, "errorType", error.getClass().getSimpleName());
                Log.e(TAG, report.toString());
            }
        } finally {
            // These resources are never touched by the WebView request threads.
            try {
                if (model != null) model.close();
            } catch (RuntimeException | LinkageError error) {
                cleanupSucceeded = false;
                Log.e(TAG, "{\"kind\":\"cleanup-failure\",\"resource\":\"interpreter\"}");
            } finally {
                try {
                    if (video != null) video.release();
                } catch (IOException | RuntimeException | LinkageError error) {
                    cleanupSucceeded = false;
                    Log.e(TAG, "{\"kind\":\"cleanup-failure\",\"resource\":\"decoder\"}");
                }
            }
            synchronized (lock) {
                verified = false;
                workerThread = null;
                resourcesClosed = cleanupSucceeded;
                report("stopped");
                lock.notifyAll();
            }
        }
    }

    private static void validateVideo(MediaMetadataRetriever video, NativeVideoAssets config) throws IOException {
        try {
            String count = video.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT);
            String duration = video.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION);
            String rotation = video.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION);
            if (count == null || Integer.parseInt(count) != config.frames) throw new IOException("fixture_frame_count_mismatch");
            long durationMs = Long.parseLong(duration == null ? "0" : duration);
            double declaredDuration = config.frames * 1000.0 / config.fps;
            if (durationMs <= 0 || durationMs > 31000 || Math.abs(durationMs - declaredDuration) > Math.max(250, 1000.0 / config.fps)) {
                throw new IOException("fixture_duration_mismatch");
            }
            if (rotation != null && Integer.parseInt(rotation) % 360 != 0) throw new IOException("rotated_fixture_not_supported");
        } catch (NumberFormatException error) { throw new IOException("fixture_metadata_invalid", error); }
    }

    private JSONObject logBase(String kind) {
        JSONObject output = new JSONObject();
        put(output, "kind", kind);
        put(output, "source", "video");
        put(output, "engine", "litert");
        put(output, "engineVersion", NativeVideoAssets.RUNTIME_VERSION);
        put(output, "modelSha256", modelPin.sha256);
        put(output, "modelId", modelPin.id);
        put(output, "inputSize", modelPin.inputSize);
        put(output, "verified", verified);
        put(output, "configAsset", configAsset);
        put(output, "policy", context == null ? "strict" : context.policy);
        put(output, "api", Build.VERSION.SDK_INT);
        put(output, "abi", Build.SUPPORTED_ABIS.length == 0 ? "unknown" : Build.SUPPORTED_ABIS[0]);
        put(output, "threads", 2);
        put(output, "scalarFrameDiagnostics", true);
        put(output, "capture", NativeVideoCase.isSynthetic(configAsset) ? "generated-synthetic-video" : "bundled-public-video");
        put(output, "personCount", NativeVideoCase.isSynthetic(configAsset) ? "synthetic-no-person" : "unknown-singlepose-model");
        put(output, "inputTransform", (statelessCrop ? "official-three-pass-stateless" : "official-android-tracked") + "-crop-square-before-bilinear-rgb-uint8-" + modelPin.inputSize + "-no-mirror");
        put(output, "decodedFrames", stats.decodedFrames);
        put(output, "attemptedFrames", stats.attemptedFrames);
        put(output, "acceptedFrames", stats.acceptedFrames);
        put(output, "discardedEpochFrames", stats.discardedEpochFrames);
        put(output, "nextFrameIndex", frameIndex);
        put(output, "fullFileProcessed", completed);
        put(output, "resourcesClosed", resourcesClosed);
        put(output, "cleanupSucceeded", cleanupSucceeded);
        put(output, "nativeRecognizedEvents", stats.observed.size());
        put(output, "acknowledgedEvents", stats.acknowledgedEvents);
        return output;
    }

    private void report(String kind) {
        JSONObject output = logBase(kind);
        put(output, "observedGestures", new JSONArray(stats.observed));
        put(output, "expectedGestures", activityPolicy() || config == null ? new JSONArray() : new JSONArray(config.expectedGestures));
        put(output, "expectationKnown", !activityPolicy() && config != null && config.expectationKnown);
        put(output, "expectedSequenceEvaluated", !activityPolicy() && completed && config != null && config.expectationKnown);
        if (!activityPolicy() && completed && config != null && config.expectationKnown) {
            put(output, "exactExpectedSequence", stats.observed.equals(config.expectedGestures));
        }
        put(output, "declaredVideoFrames", config == null ? 0 : config.frames);
        put(output, "declaredFps", config == null ? 0 : config.fps);
        put(output, "decodeMeanMs", stats.mean(stats.decode));
        put(output, "preprocessMeanMs", stats.mean(stats.preprocess));
        put(output, "inferenceMeanMs", stats.mean(stats.inference));
        put(output, "inferenceP95Ms", stats.percentile(stats.inference, 0.95));
        put(output, "frameMeanMs", stats.mean(stats.total));
        put(output, "frameP95Ms", stats.percentile(stats.total, 0.95));
        put(output, "poseDiagnostics", stats.pose.snapshot());
        put(output, "referenceParityChecks", stats.parityChecks);
        put(output, "referenceByteDifferences", stats.parityByteDifferences);
        put(output, "referenceMaxByteDelta", stats.parityMaxByteDelta);
        put(output, "referenceOutputMaxDelta", stats.parityOutputMaxDelta);
        put(output, "referenceMeanMs", stats.parityChecks == 0 ? 0 : stats.referenceTotalMs / stats.parityChecks);
        put(output, "modelInferencesPerFrame", statelessCrop ? 3 : 1);
        put(output, "defaultCropFrames", stats.defaultCropFrames);
        put(output, "processPssKiB", Debug.getPss());
        Log.i(TAG, output.toString());
    }

    private void frameDiagnostic(NativeMoveNet.Result result, int index, double fileMs) {
        JSONObject output = new JSONObject();
        put(output, "kind", "frame-diagnostic");
        put(output, "configAsset", configAsset);
        put(output, "policy", context == null ? "strict" : context.policy);
        put(output, "frameIndex", index); put(output, "fileMs", fileMs);
        put(output, "decodedProbeCrc32", result.decodedProbeCrc32);
        put(output, "inputCrc32", result.inputCrc32); put(output, "outputCrc32", result.outputCrc32);
        put(output, "meanR", result.meanR); put(output, "meanG", result.meanG); put(output, "meanB", result.meanB);
        put(output, "nonzeroInputBytes", result.nonzeroInputBytes);
        put(output, "invalidMappedKeypoints", result.invalidMappedKeypoints);
        put(output, "modelInputSize", result.plan.inputSize);
        put(output, "imageWidth", result.imageWidth); put(output, "imageHeight", result.imageHeight);
        put(output, "cropLeft", result.plan.left); put(output, "cropTop", result.plan.top);
        put(output, "cropRight", result.plan.right); put(output, "cropBottom", result.plan.bottom);
        put(output, "detectWidth", result.plan.detectWidth); put(output, "detectHeight", result.plan.detectHeight);
        put(output, "squareSize", result.plan.squareSize); put(output, "defaultCrop", result.defaultCrop);
        put(output, "referenceParityChecked", result.parityChecked);
        put(output, "referenceByteDifferences", result.parityByteDifferences);
        put(output, "referenceOutputMaxDelta", result.parityOutputMaxDelta);
        String[] names = {"leftShoulder", "rightShoulder", "leftWrist", "rightWrist"};
        String[] fields = {"Y", "X", "Score"};
        for (int i = 0; i < names.length; i++) {
            for (int j = 0; j < fields.length; j++) {
                float value = result.requiredRaw[i * 3 + j];
                put(output, names[i] + fields[j], Float.isFinite(value) ? value : JSONObject.NULL);
            }
        }
        put(output, "machineExpected", expected()); put(output, "machineStatus", status());
        put(output, "machineArmed", armed()); put(output, "machineHeldMs", heldMs());
        Log.i(TAG, output.toString());
    }

    /** Caller holds lock. Attempts stay separate from accepted pose-frame coverage. */
    private void frameAttempt(long attemptId, String attemptRound, int index, long token, String phase,
                              int reason, ReplayAttemptTiming timing, NativeMoveNet.Result result) {
        JSONObject output = new JSONObject();
        put(output, "kind", "frame-attempt"); put(output, "source", "video");
        put(output, "configAsset", configAsset); put(output, "modelSha256", modelPin.sha256);
        put(output, "attemptId", attemptId); put(output, "roundId", attemptRound);
        put(output, "frameIndex", index); put(output, "attemptEpoch", token); put(output, "controlEpoch", epoch);
        put(output, "phase", phase); put(output, "discardReason", reason);
        put(output, "controlPollAgeMs", Math.max(0, wall() - lastPollWall));
        put(output, "controlLeaseMs", ReplayFrameGuard.LEASE_MS);
        put(output, "inferenceStarted", timing.inferenceStarted());
        put(output, "wallTimingAvailable", Double.isFinite(timing.totalWallMs()));
        put(output, "workerCpuAvailable", Double.isFinite(timing.totalWorkerCpuMs()));
        put(output, "processCpuAvailable", Double.isFinite(timing.totalProcessCpuMs()));
        put(output, "decodeWallMs", finiteOrNull(timing.decWallMs()));
        put(output, "decodeWorkerCpuMs", finiteOrNull(timing.decWorkerCpuMs()));
        put(output, "decodeProcessCpuMs", finiteOrNull(timing.decProcessCpuMs()));
        put(output, "guardWallMs", finiteOrNull(timing.guardWallMs()));
        put(output, "guardWorkerCpuMs", finiteOrNull(timing.guardWorkerCpuMs()));
        put(output, "guardProcessCpuMs", finiteOrNull(timing.guardProcessCpuMs()));
        put(output, "modelWallMs", finiteOrNull(timing.modelWallMs()));
        put(output, "modelWorkerCpuMs", finiteOrNull(timing.modelWorkerCpuMs()));
        put(output, "modelProcessCpuMs", finiteOrNull(timing.modelProcessCpuMs()));
        put(output, "postGuardWallMs", finiteOrNull(timing.postGuardWallMs()));
        put(output, "postGuardWorkerCpuMs", finiteOrNull(timing.postGuardWorkerCpuMs()));
        put(output, "postGuardProcessCpuMs", finiteOrNull(timing.postGuardProcessCpuMs()));
        put(output, "processingWallMs", finiteOrNull(timing.processingWallMs()));
        put(output, "totalWallMs", finiteOrNull(timing.totalWallMs()));
        put(output, "totalWorkerCpuMs", finiteOrNull(timing.totalWorkerCpuMs()));
        put(output, "totalProcessCpuMs", finiteOrNull(timing.totalProcessCpuMs()));
        put(output, "preprocessMs", result == null ? JSONObject.NULL : finiteOrNull(result.preprocessMs));
        put(output, "inferenceMs", result == null ? JSONObject.NULL : finiteOrNull(result.inferenceMs));
        put(output, "referenceMs", result == null ? JSONObject.NULL : finiteOrNull(result.referenceMs));
        // Worker CPU excludes interpreter threads; process CPU includes other app work.
        put(output, "cpuScope", "worker-thread-and-app-process");
        Log.i(TAG, output.toString());
    }

    private static ReplayAttemptTiming.Sample timingSample() {
        return new ReplayAttemptTiming.Sample(SystemClock.elapsedRealtimeNanos(), Debug.threadCpuTimeNanos(),
                android.os.Process.getElapsedCpuTime());
    }

    private static Object finiteOrNull(double value) { return Double.isFinite(value) ? value : JSONObject.NULL; }

    private static String failureCode(Throwable error) {
        String message = error.getMessage();
        return message != null && message.matches("[a-z0-9_]{1,80}") ? message : "native_video_initialization_or_inference_failed";
    }

    private static long wall() { return SystemClock.elapsedRealtime(); }
    private static void put(JSONObject object, String name, Object value) {
        try { object.put(name, value); }
        catch (JSONException error) { throw new IllegalArgumentException("invalid_json_scalar", error); }
    }
    private static WebResourceResponse error(int status, String reason) {
        JSONObject output = new JSONObject();
        put(output, "error", reason);
        return json(status, output);
    }
    private static WebResourceResponse json(int status, JSONObject output) {
        Map<String, String> headers = new HashMap<>();
        headers.put("Cache-Control", "no-store");
        headers.put("X-Content-Type-Options", "nosniff");
        return new WebResourceResponse("application/json", "UTF-8", status,
                status == 200 ? "OK" : "Motion request rejected", headers,
                new ByteArrayInputStream(output.toString().getBytes(StandardCharsets.UTF_8)));
    }

    private static final class Control {
        final String clientId, roundId, mode, policy;
        final long revision, after;
        final boolean active;
        private Control(String[] values) {
            clientId = values[0]; roundId = values[1]; revision = Long.parseLong(values[2]);
            active = "1".equals(values[3]); mode = values[4]; after = Long.parseLong(values[5]); policy = values[6];
        }
        static Control parse(String raw) {
            String[] pairs = MotionQuery.canonicalize(raw).split("&");
            String[] values = new String[7];
            values[6] = "strict";
            for (int i = 0; i < pairs.length; i++) values[i] = pairs[i].substring(pairs[i].indexOf('=') + 1);
            return new Control(values);
        }
    }
    private static final class PendingEvent {
        final long seq, createdWall;
        final String gesture;
        final double confidence;
        PendingEvent(long seq, String gesture, double confidence, long createdWall) {
            this.seq = seq; this.gesture = gesture; this.confidence = confidence; this.createdWall = createdWall;
        }
    }
    private static final class RunStats {
        int decodedFrames, acceptedFrames, discardedEpochFrames, acknowledgedEvents;
        long attemptedFrames;
        int controlLeaseBreaks, lastDiscardReason, skippedStaleInferences;
        long lastPollGapMs;
        int parityChecks, parityByteDifferences, parityMaxByteDelta, defaultCropFrames;
        double parityOutputMaxDelta, referenceTotalMs;
        double lastDecodeMs, lastPreprocessMs, lastInferenceMs, lastMinimum;
        final List<Double> decode = new ArrayList<>(), preprocess = new ArrayList<>(), inference = new ArrayList<>(), total = new ArrayList<>();
        final List<String> observed = new ArrayList<>();
        final NativePoseDiagnostics pose = new NativePoseDiagnostics();
        void record(double decodeMs, NativeMoveNet.Result result, double totalMs) {
            acceptedFrames++;
            if (result.defaultCrop) defaultCropFrames++;
            if (result.parityChecked) {
                parityChecks += result.modelCalls; parityByteDifferences += result.parityByteDifferences;
                parityMaxByteDelta = Math.max(parityMaxByteDelta, result.parityMaxByteDelta);
                parityOutputMaxDelta = Math.max(parityOutputMaxDelta, result.parityOutputMaxDelta);
                referenceTotalMs += result.referenceMs;
            }
            lastDecodeMs = decodeMs; lastPreprocessMs = result.preprocessMs;
            lastInferenceMs = result.inferenceMs; lastMinimum = result.keypointMinimum;
            decode.add(decodeMs); preprocess.add(result.preprocessMs); inference.add(result.inferenceMs); total.add(totalMs);
        }
        double mean(List<Double> values) {
            if (values.isEmpty()) return 0;
            double sum = 0; for (double value : values) sum += value;
            return sum / values.size();
        }
        double percentile(List<Double> values, double percentile) {
            if (values.isEmpty()) return 0;
            List<Double> sorted = new ArrayList<>(values); Collections.sort(sorted);
            return sorted.get(Math.max(0, (int) Math.ceil(percentile * sorted.size()) - 1));
        }
    }
}
