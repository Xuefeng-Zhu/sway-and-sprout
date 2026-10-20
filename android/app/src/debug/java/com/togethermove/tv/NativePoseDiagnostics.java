package com.togethermove.tv;

import org.json.JSONException;
import org.json.JSONObject;
import java.util.HashSet;
import java.util.Set;

/** Aggregate scalars only. Observes accepted file frames; never changes recognition gates. */
final class NativePoseDiagnostics {
    private final Set<Long> inputs = new HashSet<>(), outputs = new HashSet<>(), decodedProbes = new HashSet<>();
    private final int[] weak = new int[4];
    private final Window rawLeft = new Window(350), rawRight = new Window(350), rawNeutral = new Window(300);
    private final Window validLeft = new Window(350), validRight = new Window(350), validNeutral = new Window(300);
    private int frames, blankInputs, invalidMappedFrames, invalidScoreFrames, confidenceRejectedFrames;
    private int geometryValidFrames, rawLeftFrames, rawRightFrames, rawBothUpFrames, rawNeutralFrames, rawOtherFrames;
    private int acceptedConfidenceFrames, acceptedLeftFrames, acceptedRightFrames, acceptedNeutralFrames;
    private int sameInputTransitions, sameOutputTransitions, armedFrames, holdingFrames, maxHeldMs;
    private int minNonzero = Integer.MAX_VALUE, maxNonzero;
    private Long previousInput, previousOutput;

    void observe(NativeMoveNet.Result result, double fileMs, PoseGestureMachine machine) {
        frames++;
        inputs.add(result.inputCrc32); outputs.add(result.outputCrc32); decodedProbes.add(result.decodedProbeCrc32);
        if (previousInput != null && previousInput == result.inputCrc32) sameInputTransitions++;
        if (previousOutput != null && previousOutput == result.outputCrc32) sameOutputTransitions++;
        previousInput = result.inputCrc32; previousOutput = result.outputCrc32;
        if (result.nonzeroInputBytes == 0) blankInputs++;
        minNonzero = Math.min(minNonzero, result.nonzeroInputBytes);
        maxNonzero = Math.max(maxNonzero, result.nonzeroInputBytes);
        boolean confidenceAccepted = true, invalidScore = false;
        for (int i = 0; i < 4; i++) {
            float score = result.requiredRaw[i * 3 + 2];
            boolean finiteRange = Float.isFinite(score) && score >= 0 && score <= 1;
            if (!finiteRange || score < PoseGestureMachine.MIN_CONFIDENCE) { weak[i]++; confidenceAccepted = false; }
            if (!finiteRange) invalidScore = true;
        }
        if (invalidScore) invalidScoreFrames++;
        if (result.invalidMappedKeypoints > 0) invalidMappedFrames++;
        if (confidenceAccepted) acceptedConfidenceFrames++;
        else confidenceRejectedFrames++;
        PoseGestureMachine.Observation observation = result.observation;
        double width = Math.hypot(observation.leftShoulder.x - observation.rightShoulder.x,
                observation.leftShoulder.y - observation.rightShoulder.y);
        boolean geometryValid = result.invalidMappedKeypoints == 0 && Double.isFinite(width) && width > 0.00001;
        boolean left = false, right = false, neutral = false;
        if (geometryValid) {
            geometryValidFrames++;
            boolean lu = observation.leftWrist.y < observation.leftShoulder.y - width * PoseGestureMachine.RAISE_MARGIN;
            boolean ru = observation.rightWrist.y < observation.rightShoulder.y - width * PoseGestureMachine.RAISE_MARGIN;
            boolean ld = observation.leftWrist.y > observation.leftShoulder.y + width * PoseGestureMachine.NEUTRAL_MARGIN;
            boolean rd = observation.rightWrist.y > observation.rightShoulder.y + width * PoseGestureMachine.NEUTRAL_MARGIN;
            left = lu && rd; right = ru && ld; neutral = ld && rd;
            if (left) rawLeftFrames++;
            else if (right) rawRightFrames++;
            else if (neutral) rawNeutralFrames++;
            else if (lu && ru) rawBothUpFrames++;
            else rawOtherFrames++;
        }
        boolean accepted = geometryValid && confidenceAccepted;
        if (accepted && left) acceptedLeftFrames++;
        if (accepted && right) acceptedRightFrames++;
        if (accepted && neutral) acceptedNeutralFrames++;
        rawLeft.update(geometryValid && left, fileMs); rawRight.update(geometryValid && right, fileMs);
        rawNeutral.update(geometryValid && neutral, fileMs);
        validLeft.update(accepted && left, fileMs); validRight.update(accepted && right, fileMs);
        validNeutral.update(accepted && neutral, fileMs);
        if (machine.armed) armedFrames++;
        if ("hold".equals(machine.status)) holdingFrames++;
        maxHeldMs = Math.max(maxHeldMs, machine.heldMs);
    }

    void breakSequence() {
        rawLeft.stop(); rawRight.stop(); rawNeutral.stop();
        validLeft.stop(); validRight.stop(); validNeutral.stop();
        previousInput = null; previousOutput = null;
    }

    JSONObject snapshot() {
        JSONObject output = new JSONObject();
        put(output,"frames",frames); put(output,"distinctInputCrc32",inputs.size());
        put(output,"distinctOutputCrc32",outputs.size()); put(output,"distinctDecodedProbeCrc32",decodedProbes.size());
        put(output,"sameInputTransitions",sameInputTransitions); put(output,"sameOutputTransitions",sameOutputTransitions);
        put(output,"blankInputFrames",blankInputs); put(output,"minNonzeroInputBytes",frames == 0 ? 0 : minNonzero);
        put(output,"maxNonzeroInputBytes",maxNonzero); put(output,"invalidMappedFrames",invalidMappedFrames);
        put(output,"invalidNativeScoreFrames",invalidScoreFrames); put(output,"nativeConfidenceRejectedFrames",confidenceRejectedFrames);
        put(output,"nativeConfidenceAcceptedFrames",acceptedConfidenceFrames);
        put(output,"weakLeftShoulderFrames",weak[0]); put(output,"weakRightShoulderFrames",weak[1]);
        put(output,"weakLeftWristFrames",weak[2]); put(output,"weakRightWristFrames",weak[3]);
        put(output,"geometryValidFrames",geometryValidFrames); put(output,"rawLeftFrames",rawLeftFrames);
        put(output,"rawRightFrames",rawRightFrames); put(output,"rawNeutralFrames",rawNeutralFrames);
        put(output,"rawBothUpFrames",rawBothUpFrames); put(output,"rawOtherFrames",rawOtherFrames);
        put(output,"acceptedLeftFrames",acceptedLeftFrames); put(output,"acceptedRightFrames",acceptedRightFrames);
        put(output,"acceptedNeutralFrames",acceptedNeutralFrames);
        put(output,"rawLeftMaxMs",rawLeft.longestMs); put(output,"rawRightMaxMs",rawRight.longestMs);
        put(output,"rawNeutralMaxMs",rawNeutral.longestMs);
        put(output,"acceptedLeftMaxMs",validLeft.longestMs); put(output,"acceptedRightMaxMs",validRight.longestMs);
        put(output,"acceptedNeutralMaxMs",validNeutral.longestMs);
        put(output,"acceptedLeftRunsAtLeast350Ms",validLeft.qualifiedRuns);
        put(output,"acceptedRightRunsAtLeast350Ms",validRight.qualifiedRuns);
        put(output,"acceptedNeutralRunsAtLeast300Ms",validNeutral.qualifiedRuns);
        put(output,"armedFrames",armedFrames); put(output,"holdingFrames",holdingFrames); put(output,"maxObservedPartialHeldMs",maxHeldMs);
        return output;
    }

    private static void put(JSONObject object, String name, Object value) {
        try { object.put(name, value); }
        catch (JSONException error) { throw new IllegalArgumentException("invalid_diagnostic_scalar",error); }
    }
    private static final class Window {
        final int requiredMs;
        Double start, last;
        double longestMs;
        int qualifiedRuns;
        boolean qualified;
        Window(int requiredMs) { this.requiredMs = requiredMs; }
        void update(boolean matches, double now) {
            if (!matches) { stop(); return; }
            if (last == null || now < last || now - last > PoseGestureMachine.MAX_FRAME_GAP_MS) {
                start = now; qualified = false;
            }
            last = now;
            double span = now - start;
            longestMs = Math.max(longestMs, span);
            if (!qualified && span >= requiredMs) { qualified = true; qualifiedRuns++; }
        }
        void stop() { start = null; last = null; qualified = false; }
    }
}
