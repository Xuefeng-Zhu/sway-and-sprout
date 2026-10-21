package com.togethermove.tv;

/** Supplied clock values only; no Android clocks, sleeping or runtime processing. */
public final class ReplayAttemptTimingTest {
    private static int assertions;

    public static void main(String[] args) {
        ReplayAttemptTiming.Sample start = sample(1000000000L, 10000000L, 30);
        ReplayAttemptTiming.Sample decoded = sample(1500000000L, 20000000L, 55);
        ReplayAttemptTiming.Sample finished = sample(3000000000L, 80000000L, 200);
        ReplayAttemptTiming accepted = new ReplayAttemptTiming(start, decoded, finished);
        check(accepted.inferenceStarted(), "finished sample identifies model call");
        equal(500, accepted.decWallMs(), "decode wall nanoseconds converted to ms");
        equal(10, accepted.decWorkerCpuMs(), "decode worker CPU nanoseconds converted to ms");
        equal(25, accepted.decProcessCpuMs(), "decode process CPU already measured in ms");
        equal(1500, accepted.modelWallMs(), "whole model-call wall interval");
        equal(60, accepted.modelWorkerCpuMs(), "model worker CPU");
        equal(145, accepted.modelProcessCpuMs(), "model process CPU");
        equal(2000, accepted.totalWallMs(), "total wall");
        equal(70, accepted.totalWorkerCpuMs(), "total worker CPU");
        equal(170, accepted.totalProcessCpuMs(), "total process CPU");

        ReplayAttemptTiming guarded = new ReplayAttemptTiming(sample(0, 0, 0),
                sample(100000000L, 10000000L, 20), sample(600000000L, 12000000L, 25),
                sample(900000000L, 60000000L, 95));
        check(guarded.inferenceStarted(), "four snapshots identify actual model invocation");
        equal(100, guarded.decWallMs(), "decode ends before eligibility wait");
        equal(500, guarded.guardWallMs(), "eligibility wait measured separately");
        equal(2, guarded.guardWorkerCpuMs(), "guard worker CPU interval");
        equal(5, guarded.guardProcessCpuMs(), "guard process CPU interval");
        equal(300, guarded.modelWallMs(), "model excludes guard wait");
        equal(48, guarded.modelWorkerCpuMs(), "model worker CPU excludes guard");
        equal(70, guarded.modelProcessCpuMs(), "model process CPU excludes guard");
        equal(900, guarded.totalWallMs(), "total includes decode guard and model");

        ReplayAttemptTiming.Sample fiveStart = sample(0, 0, 0);
        ReplayAttemptTiming.Sample fiveDecoded = sample(500000000L, 10000000L, 25);
        ReplayAttemptTiming.Sample fiveGuard = sample(500000000L, 10000000L, 25);
        ReplayAttemptTiming.Sample fiveProcessed = sample(1500000000L, 60000000L, 170);
        ReplayAttemptTiming.Sample fiveDecision = sample(3500000000L, 70000000L, 190);
        ReplayAttemptTiming finalGuard = new ReplayAttemptTiming(fiveStart, fiveDecoded, fiveGuard,
                fiveProcessed, fiveDecision);
        equal(500, finalGuard.decWallMs(), "five samples preserve decode wall");
        equal(1000, finalGuard.modelWallMs(), "model excludes final eligibility wait");
        equal(2000, finalGuard.postGuardWallMs(), "final eligibility wait measured independently");
        equal(10, finalGuard.postGuardWorkerCpuMs(), "final guard worker CPU stays distinct");
        equal(20, finalGuard.postGuardProcessCpuMs(), "final guard process CPU stays distinct");
        equal(1500, finalGuard.processingWallMs(), "historical processing wall stops before final guard");
        equal(3500, finalGuard.totalWallMs(), "total reaches final eligibility decision");
        equal(70, finalGuard.totalWorkerCpuMs(), "whole attempt worker CPU includes final guard");
        equal(190, finalGuard.totalProcessCpuMs(), "whole attempt process CPU includes final guard");
        check(finalGuard.inferenceStarted(), "five sample model invocation present");
        // Timing survives a final-guard rejection; acceptance is deliberately not a helper input.
        ReplayAttemptTiming inferenceDiscard = new ReplayAttemptTiming(fiveStart, fiveDecoded, fiveGuard,
                fiveProcessed, fiveDecision);
        equal(3500, inferenceDiscard.totalWallMs(), "inference discard retains final wait");
        equal(1500, inferenceDiscard.processingWallMs(), "discard retains separate processing wall");
        equal(2000, inferenceDiscard.postGuardWallMs(), "discard retains post-inference guard wall");
        ReplayAttemptTiming noDecision = new ReplayAttemptTiming(fiveStart, fiveDecoded, fiveGuard,
                fiveProcessed, null);
        equal(1500, noDecision.totalWallMs(), "missing decision falls back to latest known milestone");
        unavailable(noDecision.postGuardWallMs(), "missing decision cannot fabricate a guard duration");

        ReplayAttemptTiming skipped = new ReplayAttemptTiming(start, decoded, null);
        check(!skipped.inferenceStarted(), "decode discard never claims inference started");
        equal(500, skipped.totalWallMs(), "discard total stops at decode");
        equal(10, skipped.totalWorkerCpuMs(), "discard worker CPU retained");
        equal(25, skipped.totalProcessCpuMs(), "discard process CPU retained");
        unavailable(skipped.modelWallMs(), "skipped model wall unavailable");
        unavailable(skipped.modelWorkerCpuMs(), "skipped model worker CPU unavailable");
        unavailable(skipped.modelProcessCpuMs(), "skipped model process CPU unavailable");

        ReplayAttemptTiming rejectedAfterGuard = new ReplayAttemptTiming(sample(0, 0, 0),
                sample(500000000L, 10000000L, 20), sample(2500000000L, 15000000L, 40), null);
        equal(500, rejectedAfterGuard.decWallMs(), "discard keeps actual decode interval");
        equal(2000, rejectedAfterGuard.guardWallMs(), "discard retains long guard wait before rejection");
        equal(2500, rejectedAfterGuard.totalWallMs(), "discard total reaches guard decision");
        equal(5, rejectedAfterGuard.guardWorkerCpuMs(), "discard guard CPU remains distinct from wait");
        equal(15, rejectedAfterGuard.totalWorkerCpuMs(), "discard total includes guard CPU");
        equal(40, rejectedAfterGuard.totalProcessCpuMs(), "discard process CPU reaches guard decision");
        check(!rejectedAfterGuard.inferenceStarted(), "guard rejection never claims inference");
        unavailable(rejectedAfterGuard.modelWallMs(), "rejected guard has no model time");
        ReplayAttemptTiming guardDiscard = new ReplayAttemptTiming(start, decoded, null, null);
        check(!guardDiscard.inferenceStarted(), "discard before model has no invocation");
        equal(500, guardDiscard.totalWallMs(), "guard discard total retains completed decode");
        equal(500, guardDiscard.processingWallMs(), "decode discard preserves processing duration");
        unavailable(guardDiscard.guardWallMs(), "missing model start cannot fabricate guard time");
        unavailable(guardDiscard.guardWorkerCpuMs(), "missing guard worker CPU unavailable");
        unavailable(guardDiscard.guardProcessCpuMs(), "missing guard process CPU unavailable");
        unavailable(guardDiscard.modelWallMs(), "guard discard has no model timing");

        ReplayAttemptTiming slow = new ReplayAttemptTiming(sample(0, 0, 0), sample(6000000000L, 12000000L, 20), null);
        equal(6000, slow.totalWallMs(), "slow attempt wall retained independently");
        equal(12, slow.totalWorkerCpuMs(), "small worker CPU does not become wall time");
        equal(20, slow.totalProcessCpuMs(), "process and worker CPU stay distinct");
        ReplayAttemptTiming busy = new ReplayAttemptTiming(sample(0, 0, 0), sample(1000000000L, 900000000L, 1800), null);
        equal(1800, busy.totalProcessCpuMs(), "multi-thread process CPU may exceed wall time");

        ReplayAttemptTiming missing = new ReplayAttemptTiming(sample(0, -1, -1), sample(1000000, -1, -1), sample(2000000, -1, -1));
        equal(2, missing.totalWallMs(), "missing CPU preserves available wall time");
        for (double value : new double[]{missing.decWorkerCpuMs(), missing.decProcessCpuMs(), missing.modelWorkerCpuMs(),
                missing.modelProcessCpuMs(), missing.totalWorkerCpuMs(), missing.totalProcessCpuMs()}) {
            unavailable(value, "unsupported CPU is unavailable");
        }
        ReplayAttemptTiming backwards = new ReplayAttemptTiming(sample(2000000, 2000000, 2), sample(1000000, 1000000, 1), null);
        unavailable(backwards.totalWallMs(), "backward wall clock cannot produce a duration");
        unavailable(backwards.decWorkerCpuMs(), "regressing worker CPU unavailable");
        unavailable(backwards.decProcessCpuMs(), "regressing process CPU unavailable");
        ReplayAttemptTiming absent = new ReplayAttemptTiming(null, null, null);
        unavailable(absent.totalWallMs(), "missing sample cannot fabricate zero duration");
        check(!absent.inferenceStarted(), "missing samples never claim inference");
        ReplayAttemptTiming zero = new ReplayAttemptTiming(sample(0, 0, 0), sample(0, 0, 0), null);
        equal(0, zero.totalWallMs(), "valid zero remains available");
        System.out.println("ReplayAttemptTimingTest: " + assertions + " assertions passed (supplied samples only)");
    }

    private static ReplayAttemptTiming.Sample sample(long wallNanos, long workerCpuNanos, long processCpuMs) {
        return new ReplayAttemptTiming.Sample(wallNanos, workerCpuNanos, processCpuMs);
    }
    private static void unavailable(double actual, String message) { check(Double.isNaN(actual), message); }
    private static void equal(double expected, double actual, String message) { check(expected == actual, message); }
    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }
}
