package com.togethermove.tv;

/**
 * Deterministic gesture rules ported from sidecar/motion.py.
 * Coordinates use anatomical sides in an unmirrored image. The clock is the
 * source file timestamp in milliseconds; no wall clock or Android API is used.
 */
public final class PoseGestureMachine {
    public static final int HOLD_MS = 350;
    public static final int NEUTRAL_MS = 300;
    public static final int COOLDOWN_MS = 500;
    public static final int MAX_FRAME_GAP_MS = 300;
    public static final double MIN_CONFIDENCE = 0.65;
    public static final double RAISE_MARGIN = 0.30;
    public static final double NEUTRAL_MARGIN = 0.20;

    public static final class Point {
        public final double x;
        public final double y;
        public final double confidence;

        public Point(double x, double y, double confidence) {
            this.x = x;
            this.y = y;
            this.confidence = confidence;
        }
    }

    public static final class Observation {
        public final Point leftShoulder;
        public final Point rightShoulder;
        public final Point leftWrist;
        public final Point rightWrist;
        public final double confidence;
        public final Point leftHip;
        public final Point rightHip;

        public Observation(Point leftShoulder, Point rightShoulder,
                           Point leftWrist, Point rightWrist, double confidence) {
            this(leftShoulder, rightShoulder, leftWrist, rightWrist, confidence, null, null);
        }

        public Observation(Point leftShoulder, Point rightShoulder,
                           Point leftWrist, Point rightWrist, double confidence,
                           Point leftHip, Point rightHip) {
            this.leftShoulder = leftShoulder;
            this.rightShoulder = rightShoulder;
            this.leftWrist = leftWrist;
            this.rightWrist = rightWrist;
            this.confidence = confidence;
            this.leftHip = leftHip;
            this.rightHip = rightHip;
        }
    }

    public static final class Event {
        public final String gesture;
        public final double confidence;

        public Event(String gesture, double confidence) {
            this.gesture = gesture;
            this.confidence = confidence;
        }
    }

    public String expected = "left";
    public String status = "waiting";
    public boolean armed;
    public int heldMs;

    private Double neutralSince;
    private Double holdSince;
    private Double lastObserved;
    private double lastEmitted = Double.NEGATIVE_INFINITY;

    /** Clears readiness and partial timers, retaining the expected anatomical side. */
    public void resetTemporal() {
        armed = false;
        neutralSince = null;
        holdSince = null;
        heldMs = 0;
        status = "waiting";
        lastObserved = null;
    }

    /** A new round starts with left and has no cooldown inherited from the prior round. */
    public void newRound() {
        expected = "left";
        lastEmitted = Double.NEGATIVE_INFINITY;
        resetTemporal();
    }

    public void lost(String lostStatus) {
        resetTemporal();
        status = lostStatus;
    }

    /** Returns one completed raise, or null. Equal timestamps do not advance timers. */
    public Event update(Observation observation, double fileMs) {
        if (!Double.isFinite(fileMs)) {
            throw new IllegalArgumentException("finite monotonic time required");
        }
        if (lastObserved != null) {
            double gap = fileMs - lastObserved;
            if (gap < 0) {
                throw new IllegalArgumentException("time must be monotonic");
            }
            if (gap > MAX_FRAME_GAP_MS) {
                resetTemporal();
            }
        }
        lastObserved = fileMs;
        if (observation == null) {
            lost("no-person");
            return null;
        }
        if (!validConfidence(observation.confidence)
                || !validPoint(observation.leftShoulder)
                || !validPoint(observation.rightShoulder)
                || !validPoint(observation.leftWrist)
                || !validPoint(observation.rightWrist)) {
            lost("low-confidence");
            return null;
        }

        Point ls = observation.leftShoulder;
        Point rs = observation.rightShoulder;
        Point lw = observation.leftWrist;
        Point rw = observation.rightWrist;
        double width = Math.hypot(ls.x - rs.x, ls.y - rs.y);
        if (width <= 0.00001) {
            lost("low-confidence");
            return null;
        }
        boolean leftUp = lw.y < ls.y - width * RAISE_MARGIN;
        boolean rightUp = rw.y < rs.y - width * RAISE_MARGIN;
        boolean leftDown = lw.y > ls.y + width * NEUTRAL_MARGIN;
        boolean rightDown = rw.y > rs.y + width * NEUTRAL_MARGIN;

        if (leftDown && rightDown) {
            holdSince = null;
            heldMs = 0;
            if (neutralSince == null) {
                neutralSince = fileMs;
            }
            if (fileMs - neutralSince >= NEUTRAL_MS) {
                armed = true;
            }
            status = armed ? "tracking" : "neutral";
            return null;
        }
        neutralSince = null;
        boolean expectsLeft = "left".equals(expected);
        boolean correct = expectsLeft ? leftUp && rightDown : rightUp && leftDown;
        if (!correct) {
            // Only the expected wrist may cross shoulder height while armed.
            // Even that transition always discards any partially completed hold.
            boolean transitioning = expectsLeft
                    ? !leftUp && !leftDown && rightDown
                    : !rightUp && !rightDown && leftDown;
            if (!transitioning) {
                armed = false;
            }
            holdSince = null;
            heldMs = 0;
            status = "neutral";
            return null;
        }
        if (!armed || fileMs - lastEmitted < COOLDOWN_MS) {
            holdSince = null;
            heldMs = 0;
            status = "neutral";
            return null;
        }
        if (holdSince == null) {
            holdSince = fileMs;
        }
        heldMs = (int) Math.max(0, fileMs - holdSince);
        status = "hold";
        if (heldMs < HOLD_MS) {
            return null;
        }
        String gesture = expected + "-raise";
        double minimum = Math.min(observation.confidence,
                Math.min(Math.min(ls.confidence, rs.confidence),
                        Math.min(lw.confidence, rw.confidence)));
        expected = expectsLeft ? "right" : "left";
        lastEmitted = fileMs;
        resetTemporal();
        status = "neutral";
        return new Event(gesture, minimum);
    }

    private static boolean validConfidence(double confidence) {
        return Double.isFinite(confidence) && confidence >= MIN_CONFIDENCE && confidence <= 1;
    }

    private static boolean validPoint(Point point) {
        return point != null && Double.isFinite(point.x) && Double.isFinite(point.y)
                && validConfidence(point.confidence);
    }
}
