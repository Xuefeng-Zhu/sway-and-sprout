package com.togethermove.tv;

import com.togethermove.tv.PoseGestureMachine.Event;
import com.togethermove.tv.PoseGestureMachine.Observation;
import com.togethermove.tv.PoseGestureMachine.Point;

/**
 * Host-JDK tests using explicit synthetic observations and analytic geometry.
 * These fixtures establish rule/math behavior; they are not inference or camera evidence.
 */
public final class NativePoseMathTest {
    private static int assertions;

    public static void main(String[] args) {
        thresholdAndAlternation();
        transitionDiscardsPartialHold();
        transitionsNeverArm();
        ambiguousPosesRequireNeutral();
        gapsAndClockValidation();
        lossAndConfidence();
        eventUsesAllFiveConfidenceValues();
        cooldownDiscardsHold();
        resetAndNewRound();
        strictGeometryAndShoulderDistance();
        analyticLandscapeAndPortrait();
        fractionalAndOddPadding();
        invalidCoordinatesAndDimensions();
        System.out.println("NativePoseMathTest: " + assertions + " assertions passed (synthetic host Java only)");
    }

    private static void thresholdAndAlternation() {
        PoseGestureMachine m = new PoseGestureMachine();
        equal("left", m.expected, "round starts anatomical left");
        noEvent(m, neutral(), 0);
        noEvent(m, neutral(), 299);
        check(!m.armed, "299ms neutral is insufficient");
        noEvent(m, neutral(), 300);
        check(m.armed, "300ms neutral arms");
        equal("tracking", m.status, "armed neutral status");
        noEvent(m, left(), 350);
        noEvent(m, left(), 600);
        noEvent(m, left(), 699.99);
        equal(349, m.heldMs, "hold milliseconds truncate like Python int");
        event(m.update(left(), 700), "left-raise", 1);
        equal("right", m.expected, "one completed left changes side");
        check(!m.armed && m.heldMs == 0, "emission clears all temporal state");
        noEvent(m, right(), 900);
        noEvent(m, right(), 1150);
        check(!m.armed, "a raised wrist cannot rearm after emission");
        noEvent(m, neutral(), 1200);
        noEvent(m, neutral(), 1500);
        noEvent(m, right(), 1550);
        noEvent(m, right(), 1750);
        event(m.update(right(), 1900), "right-raise", 1);
        equal("left", m.expected, "alternation returns to left");
    }

    private static void transitionDiscardsPartialHold() {
        PoseGestureMachine m = armed();
        noEvent(m, left(), 350);
        noEvent(m, left(), 550);
        equal(200, m.heldMs, "partial hold accumulates");
        noEvent(m, pose(0.40, 0.75), 600);
        check(m.armed, "expected wrist transition retains arming");
        equal(0, m.heldMs, "transition discards partial hold");
        noEvent(m, left(), 650);
        noEvent(m, left(), 950);
        equal(300, m.heldMs, "hold restarts after transition");
        event(m.update(left(), 1000), "left-raise", 1);
    }

    private static void transitionsNeverArm() {
        PoseGestureMachine m = new PoseGestureMachine();
        noEvent(m, pose(0.40, 0.75), 0);
        noEvent(m, pose(0.40, 0.75), 300);
        check(!m.armed, "transition cannot arm without neutral");
        noEvent(m, left(), 350);
        noEvent(m, left(), 600);
        noEvent(m, left(), 850);
        equal(0, m.heldMs, "unarmed correct pose cannot start hold");
        noEvent(m, neutral(), 900);
        noEvent(m, neutral(), 1100);
        noEvent(m, pose(0.40, 0.75), 1150);
        noEvent(m, neutral(), 1200);
        noEvent(m, neutral(), 1400);
        check(!m.armed, "transition also interrupts partial neutral settlement");
        noEvent(m, neutral(), 1500);
        check(m.armed, "new contiguous neutral interval can arm");
    }

    private static void ambiguousPosesRequireNeutral() {
        Observation[] invalid = {right(), pose(0.15, 0.15), pose(0.40, 0.40), pose(0.75, 0.40)};
        for (Observation ambiguous : invalid) {
            PoseGestureMachine m = armed();
            noEvent(m, left(), 350);
            noEvent(m, left(), 550);
            noEvent(m, ambiguous, 600);
            check(!m.armed, "wrong side, both up or ambiguity clears arming");
            equal(0, m.heldMs, "ambiguity clears partial hold");
            noEvent(m, left(), 650);
            noEvent(m, left(), 900);
            noEvent(m, left(), 1150);
            equal(0, m.heldMs, "correct pose after ambiguity still needs neutral");
        }
    }

    private static void gapsAndClockValidation() {
        PoseGestureMachine exact = armed();
        noEvent(exact, left(), 350);
        noEvent(exact, left(), 650);
        event(exact.update(left(), 700), "left-raise", 1);

        PoseGestureMachine stale = armed();
        noEvent(stale, left(), 350);
        noEvent(stale, left(), 651);
        check(!stale.armed && stale.heldMs == 0, "301ms gap loses readiness and partial hold");
        noEvent(stale, left(), 900);
        noEvent(stale, left(), 1150);

        PoseGestureMachine settling = new PoseGestureMachine();
        noEvent(settling, neutral(), 0);
        noEvent(settling, neutral(), 301);
        check(!settling.armed, "stale neutral does not arm");
        noEvent(settling, neutral(), 601);
        check(settling.armed, "300ms after fresh neutral can arm");
        throwsArgument(() -> settling.update(neutral(), 600), "decreasing timestamp rejects");
        throwsArgument(() -> settling.update(neutral(), Double.NaN), "NaN timestamp rejects");
        throwsArgument(() -> settling.update(neutral(), Double.POSITIVE_INFINITY), "infinite timestamp rejects");
        noEvent(settling, neutral(), 601);
        equal(0, settling.heldMs, "repeated timestamp adds no time");
        settling.resetTemporal();
        noEvent(settling, neutral(), 0);
        check(!settling.armed, "explicit reset permits file timestamp restart");
    }

    private static void lossAndConfidence() {
        PoseGestureMachine m = armed();
        noEvent(m, left(), 350);
        noEvent(m, left(), 550);
        noEvent(m, null, 600);
        equal("no-person", m.status, "missing observation reports no-person");
        check(!m.armed && m.heldMs == 0, "missing person loses partial hold");
        noEvent(m, left(), 0);
        equal(0, m.heldMs, "missing person clears prior timestamp and readiness");

        double[] invalidScores = {0.649999, -1, 1.000001, Double.NaN, Double.POSITIVE_INFINITY};
        for (double score : invalidScores) {
            PoseGestureMachine weak = armed();
            noEvent(weak, new Observation(point(0.65, 0.40, score), point(0.35, 0.40, 1),
                    point(0.65, 0.15, 1), point(0.35, 0.75, 1), 1), 350);
            equal("low-confidence", weak.status, "invalid joint confidence reports loss");
            check(!weak.armed && weak.heldMs == 0, "invalid confidence resets temporal state");
        }
        for (double coordinate : new double[] {Double.NaN, Double.NEGATIVE_INFINITY}) {
            PoseGestureMachine invalid = armed();
            noEvent(invalid, new Observation(point(0.65, 0.40, 1), point(0.35, 0.40, 1),
                    point(coordinate, 0.15, 1), point(0.35, 0.75, 1), 1), 350);
            equal("low-confidence", invalid.status, "nonfinite coordinates lose tracking");
        }
        PoseGestureMachine collapsed = armed();
        noEvent(collapsed, new Observation(point(1, 1, 1), point(1, 1, 1),
                point(1, 0, 1), point(1, 2, 1), 1), 350);
        equal("low-confidence", collapsed.status, "coincident shoulders reject");
        m.lost("paused");
        equal("paused", m.status, "caller loss status is retained");
    }

    private static void eventUsesAllFiveConfidenceValues() {
        for (int weakest = 0; weakest < 5; weakest++) {
            double[] scores = {0.96, 0.95, 0.94, 0.93, 0.92};
            scores[weakest] = 0.65;
            Observation o = new Observation(point(0.65, 0.40, scores[1]), point(0.35, 0.40, scores[2]),
                    point(0.65, 0.15, scores[3]), point(0.35, 0.75, scores[4]), scores[0]);
            PoseGestureMachine m = armed();
            noEvent(m, o, 350);
            noEvent(m, o, 600);
            event(m.update(o, 700), "left-raise", 0.65);
        }
    }

    private static void cooldownDiscardsHold() {
        PoseGestureMachine m = emittedLeft();
        noEvent(m, neutral(), 750);
        noEvent(m, neutral(), 1000);
        noEvent(m, neutral(), 1050);
        check(m.armed, "neutral can arm during cooldown");
        noEvent(m, right(), 1100);
        equal(0, m.heldMs, "400ms since event is still cooldown");
        noEvent(m, right(), 1199);
        equal(0, m.heldMs, "499ms cooldown does not accumulate hold");
        noEvent(m, right(), 1200);
        equal("hold", m.status, "exact500ms begins fresh hold");
        noEvent(m, right(), 1500);
        equal(300, m.heldMs, "hold starts only after cooldown");
        event(m.update(right(), 1550), "right-raise", 1);
    }

    private static void resetAndNewRound() {
        PoseGestureMachine m = emittedLeft();
        m.resetTemporal();
        equal("right", m.expected, "temporal reset preserves expected side");
        noEvent(m, neutral(), 0);
        noEvent(m, neutral(), 300);
        noEvent(m, right(), 350);
        equal(0, m.heldMs, "temporal reset preserves last event cooldown");
        m.newRound();
        equal("left", m.expected, "new round resets expected side");
        equal("waiting", m.status, "new round starts waiting");
        noEvent(m, neutral(), 0);
        noEvent(m, neutral(), 300);
        noEvent(m, left(), 350);
        noEvent(m, left(), 600);
        event(m.update(left(), 700), "left-raise", 1);
    }

    private static void strictGeometryAndShoulderDistance() {
        // Shoulder distance is exactly100 pixels: a 60/80 right triangle.
        // The anatomical left shoulder has the smaller x in this fixture.
        Observation neutral = new Observation(point(100, 100, 1), point(160, 180, 1),
                point(100, 121, 1), point(160, 201, 1), 1);
        Observation boundary = new Observation(point(100, 100, 1), point(160, 180, 1),
                point(100, 70, 1), point(160, 201, 1), 1);
        Observation raised = new Observation(point(100, 100, 1), point(160, 180, 1),
                point(100, 69, 1), point(160, 201, 1), 1);
        PoseGestureMachine m = new PoseGestureMachine();
        noEvent(m, neutral, 0);
        noEvent(m, neutral, 300);
        noEvent(m, boundary, 350);
        check(m.armed, "exact raise margin is a transition, preserving readiness");
        equal(0, m.heldMs, "exact raise margin cannot hold");
        noEvent(m, raised, 400);
        noEvent(m, raised, 650);
        event(m.update(raised, 750), "left-raise", 1);

        PoseGestureMachine exactDown = new PoseGestureMachine();
        Observation downBoundary = new Observation(point(100, 100, 1), point(200, 100, 1),
                point(100, 120, 1), point(200, 120, 1), 1);
        noEvent(exactDown, downBoundary, 0);
        noEvent(exactDown, downBoundary, 300);
        check(!exactDown.armed, "exact down margin does not count as neutral");
    }

    private static void analyticLandscapeAndPortrait() {
        PoseCoordinates.Plan landscape = PoseCoordinates.plan(1280, 720);
        equal(192, landscape.resizedWidth, "16:9 resized width");
        equal(108, landscape.resizedHeight, "16:9 resized height");
        equal(0, landscape.padLeft, "landscape horizontal padding");
        equal(42, landscape.padTop, "landscape vertical padding");
        pointEquals(landscape.restore(0.5, 0.25, 0.83), 320, 360, 0.83,
                "landscape analytic interior point");
        pointEquals(landscape.restore(42.0 / 192, 0, 1), 0, 0, 1, "image top-left");
        pointEquals(landscape.restore(150.0 / 192, 1, 1), 1280, 720, 1, "image bottom-right");
        check(landscape.restore(41.0 / 192, 0.5, 1) == null, "top padding is not an image landmark");
        check(landscape.restore(151.0 / 192, 0.5, 1) == null, "bottom padding is rejected");

        PoseCoordinates.Plan portrait = PoseCoordinates.plan(720, 1280);
        equal(108, portrait.resizedWidth, "portrait resized width");
        equal(192, portrait.resizedHeight, "portrait resized height");
        equal(42, portrait.padLeft, "portrait horizontal padding");
        equal(0, portrait.padTop, "portrait vertical padding");
        pointEquals(portrait.restore(0.25, 0.5, 0.4), 360, 320, 0.4,
                "restore uses model y,x ordering and retains low score");
        check(portrait.restore(0.5, 41.0 / 192, 1) == null, "left padding is rejected");
        check(portrait.restore(0.5, 151.0 / 192, 1) == null, "right padding is rejected");

        PoseCoordinates.Plan square = PoseCoordinates.plan(400, 400);
        pointEquals(square.restore(0.75, 0.25, 1), 100, 300, 1, "square analytic mapping");
    }

    private static void fractionalAndOddPadding() {
        PoseCoordinates.Plan odd = PoseCoordinates.plan(641, 480);
        equal(192, odd.resizedWidth, "fractional resize uses192 width");
        equal(143, odd.resizedHeight, "fractional resized height floors");
        equal(24, odd.padTop, "odd spare pixel goes to bottom");
        pointEquals(odd.restore(0.5, 0.5, 1), 320.5, 34560.0 / 143, 1,
                "restoration uses actual integer resize on each axis");
        pointEquals(odd.restore(167.0 / 192, 0.5, 1), 320.5, 480, 1,
                "odd-padding image bottom");
        check(odd.restore(168.0 / 192, 0.5, 1) == null, "asymmetric bottom padding rejects");

        PoseCoordinates.Plan fractional = PoseCoordinates.plan(645, 480);
        equal(142, fractional.resizedHeight, "645x480 integer resized height");
        equal(25, fractional.padTop, "centering follows floored image dimension");
        pointEquals(fractional.restore(0.5, 0.5, 1), 322.5, 240, 1,
                "fractional dimensions center by integer image bounds");
        // Analytic source->model->source fixture: x215 maps to64, y120 maps
        // to25+35.5=60.5 in the actual192x142 rectangle, then returns unchanged.
        pointEquals(fractional.restore(60.5 / 192, 64.0 / 192, 0.77), 215, 120, 0.77,
                "645x480 explicit source-point roundtrip");

        PoseCoordinates.Plan alternateTarget = PoseCoordinates.plan(640, 480, 256);
        equal(256, alternateTarget.targetSize, "explicit target size");
        equal(192, alternateTarget.resizedHeight, "explicit target height");
        pointEquals(alternateTarget.restore(0.5, 0.5, 1), 320, 240, 1, "alternate target mapping");
    }

    private static void invalidCoordinatesAndDimensions() {
        PoseCoordinates.Plan p = PoseCoordinates.plan(1280, 720);
        double[][] invalid = {
                {Double.NaN, 0.5, 1}, {0.5, Double.POSITIVE_INFINITY, 1},
                {-0.01, 0.5, 1}, {0.5, 1.01, 1}, {0.5, 0.5, -0.01},
                {0.5, 0.5, 1.01}, {0.5, 0.5, Double.NaN}
        };
        for (double[] landmark : invalid) {
            check(p.restore(landmark[0], landmark[1], landmark[2]) == null,
                    "invalid model landmark rejects without clipping");
        }
        throwsArgument(() -> PoseCoordinates.plan(0, 720), "zero width rejects");
        throwsArgument(() -> PoseCoordinates.plan(720, -1), "negative height rejects");
        throwsArgument(() -> PoseCoordinates.plan(720, 720, 0), "zero target rejects");
        throwsArgument(() -> PoseCoordinates.plan(Integer.MAX_VALUE, 1), "empty resized dimension rejects");
    }

    private static PoseGestureMachine armed() {
        PoseGestureMachine m = new PoseGestureMachine();
        noEvent(m, neutral(), 0);
        noEvent(m, neutral(), 150);
        noEvent(m, neutral(), 300);
        check(m.armed, "fixture is armed from contiguous neutral");
        return m;
    }

    private static PoseGestureMachine emittedLeft() {
        PoseGestureMachine m = armed();
        noEvent(m, left(), 350);
        noEvent(m, left(), 550);
        event(m.update(left(), 700), "left-raise", 1);
        return m;
    }

    private static Point point(double x, double y, double confidence) {
        return new Point(x, y, confidence);
    }

    private static Observation pose(double leftY, double rightY) {
        return new Observation(point(0.65, 0.40, 1), point(0.35, 0.40, 1),
                point(0.65, leftY, 1), point(0.35, rightY, 1), 1);
    }

    private static Observation neutral() { return pose(0.75, 0.75); }
    private static Observation left() { return pose(0.15, 0.75); }
    private static Observation right() { return pose(0.75, 0.15); }

    private static void noEvent(PoseGestureMachine m, Observation o, double timestamp) {
        check(m.update(o, timestamp) == null, "no gesture expected at fileMs=" + timestamp);
    }

    private static void event(Event event, String gesture, double confidence) {
        check(event != null, "completed gesture is emitted");
        equal(gesture, event.gesture, "event anatomical side");
        close(confidence, event.confidence, "event minimum confidence");
    }

    private static void pointEquals(Point p, double x, double y, double confidence, String message) {
        check(p != null, message + " is in image");
        close(x, p.x, message + " x");
        close(y, p.y, message + " y");
        close(confidence, p.confidence, message + " confidence");
    }

    private static void throwsArgument(Runnable action, String message) {
        try {
            action.run();
        } catch (IllegalArgumentException expected) {
            assertions++;
            return;
        }
        throw new AssertionError(message);
    }

    private static void equal(Object expected, Object actual, String message) {
        check(expected.equals(actual), message + ": expected=" + expected + ", actual=" + actual);
    }

    private static void close(double expected, double actual, String message) {
        check(Math.abs(expected - actual) < 1e-9,
                message + ": expected=" + expected + ", actual=" + actual);
    }

    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }
}
