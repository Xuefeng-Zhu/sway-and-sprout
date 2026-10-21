package com.togethermove.tv;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;

/** Pure movement-first policy mirrored in sidecar/activity.py. Gameplay settings
 * are provisional; synthetic rule tests do not establish recognition accuracy. */
public final class ActivityMachine {
    public static final double MIN_CONFIDENCE = 0.65;
    public static final int MAX_GAP_MS = 300, WINDOW_MS = 1500, COOLDOWN_MS = 1000, MIN_MOVEMENT_MS = 250;
    public static final double DEADBAND = 0.025, PATH_REQUIRED = 0.20, MAX_JUMP = 0.75;
    public String expected = "any", status = "waiting";
    public boolean armed;
    public int heldMs;
    private Double lastObserved;
    private double lastEmitted = Double.NEGATIVE_INFINITY;
    private final Map<String, Channel> channels = new LinkedHashMap<>();

    public void newRound() { lastEmitted = Double.NEGATIVE_INFINITY; resetTemporal(); }
    public void resetTemporal() {
        expected = "any"; status = "waiting"; armed = false; heldMs = 0;
        lastObserved = null; channels.clear();
    }
    public void lost(String value) { resetTemporal(); status = value; }
    private static boolean valid(PoseGestureMachine.Point p) {
        return p != null && Double.isFinite(p.x) && Double.isFinite(p.y)
                && Double.isFinite(p.confidence) && p.confidence >= MIN_CONFIDENCE && p.confidence <= 1;
    }
    private static Map<String, double[]> features(PoseGestureMachine.Observation o) {
        Map<String, double[]> values = new LinkedHashMap<>();
        if (o == null || !valid(o.leftShoulder) || !valid(o.rightShoulder)) return values;
        PoseGestureMachine.Point ls = o.leftShoulder, rs = o.rightShoulder;
        double span = Math.hypot(rs.x - ls.x, rs.y - ls.y);
        if (span <= 1e-5) return values;
        double confidence = Math.min(ls.confidence, rs.confidence);
        PoseGestureMachine.Point[] wrists = {o.leftWrist, o.rightWrist};
        PoseGestureMachine.Point[] shoulders = {ls, rs};
        String[] names = {"left", "right"};
        for (int i = 0; i < 2; i++) if (valid(wrists[i])) {
            values.put(names[i], new double[]{(wrists[i].x - shoulders[i].x) / span,
                    (wrists[i].y - shoulders[i].y) / span, Math.min(confidence, wrists[i].confidence)});
        }
        if (valid(o.leftHip) && valid(o.rightHip)) {
            values.put("torso", new double[]{((ls.x + rs.x) - (o.leftHip.x + o.rightHip.x)) / (2 * span),
                    ((ls.y + rs.y) - (o.leftHip.y + o.rightHip.y)) / (2 * span),
                    Math.min(confidence, Math.min(o.leftHip.confidence, o.rightHip.confidence))});
        }
        return values;
    }
    public PoseGestureMachine.Event update(PoseGestureMachine.Observation observation, double nowMs) {
        if (!Double.isFinite(nowMs)) throw new IllegalArgumentException("finite monotonic time required");
        Double previous = lastObserved;
        if (previous != null && nowMs < previous) throw new IllegalArgumentException("time must be monotonic");
        if (previous != null && nowMs - previous > MAX_GAP_MS) { resetTemporal(); previous = null; }
        Map<String, double[]> values = features(observation);
        if (values.isEmpty()) { lost(observation == null ? "no-person" : "low-confidence"); return null; }
        lastObserved = nowMs; status = "tracking"; armed = true;
        channels.keySet().retainAll(values.keySet());
        double candidate = -1;
        for (Map.Entry<String, double[]> entry : values.entrySet()) {
            double[] value = entry.getValue(); double x = value[0], y = value[1], confidence = value[2];
            Channel channel = channels.get(entry.getKey());
            if (channel == null) { channels.put(entry.getKey(), new Channel(x, y, nowMs)); continue; }
            if (previous != null && previous == nowMs) continue;
            if (Math.hypot(x - channel.x, y - channel.y) > MAX_JUMP) {
                channels.put(entry.getKey(), new Channel(x, y, nowMs)); continue;
            }
            double alpha = Math.min(1, (nowMs - channel.at) / 100.0);
            channel.x += alpha * (x - channel.x); channel.y += alpha * (y - channel.y); channel.at = nowMs;
            double distance = Math.hypot(channel.x - channel.anchorX, channel.y - channel.anchorY);
            channel.history.removeIf(row -> nowMs - row[0] > WINDOW_MS);
            if (distance < DEADBAND) continue;
            channel.anchorX = channel.x; channel.anchorY = channel.y;
            channel.history.add(new double[]{nowMs, distance});
            double path = 0; for (double[] row : channel.history) path += row[1];
            if (channel.history.size() >= 3 && nowMs - channel.history.get(0)[0] >= MIN_MOVEMENT_MS
                    && path >= PATH_REQUIRED && nowMs - lastEmitted >= COOLDOWN_MS) candidate = Math.max(candidate, confidence);
        }
        if (candidate < 0) return null;
        lastEmitted = nowMs; for (Channel channel : channels.values()) channel.history.clear();
        return new PoseGestureMachine.Event("activity", candidate);
    }
    private static final class Channel {
        double x, y, anchorX, anchorY, at;
        final ArrayList<double[]> history = new ArrayList<>();
        Channel(double x, double y, double at) { this.x = this.anchorX = x; this.y = this.anchorY = y; this.at = at; }
    }
}
