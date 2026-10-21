package com.togethermove.tv;

/** Fake-clock checks of the production frame predicate; no decoder or device. */
public final class ReplayFrameGuardTest {
    private static int assertions;

    public static void main(String[] args) {
        long frameEpoch = 7;
        long lastPoll = 0;
        // One six-second inference is still eligible while healthy heartbeats
        // arrive every 200ms. Inference elapsed time is not the control lease.
        for (long now = 0; now <= 6000; now += 200) {
            lastPoll = now;
            equal(ReplayFrameGuard.ACCEPT,
                    ReplayFrameGuard.reason(false, frameEpoch, frameEpoch, true, now, lastPoll),
                    "healthy heartbeat during slow frame at " + now);
        }
        equal(ReplayFrameGuard.ACCEPT,
                ReplayFrameGuard.reason(false, frameEpoch, frameEpoch, true, 6000, lastPoll),
                "six-second frame with healthy heartbeat accepted");
        equal(ReplayFrameGuard.ACCEPT,
                ReplayFrameGuard.reason(false, frameEpoch, frameEpoch, true, 7500, lastPoll),
                "lease boundary remains inclusive");
        equal(ReplayFrameGuard.LEASE_EXPIRED,
                ReplayFrameGuard.reason(false, frameEpoch, frameEpoch, true, 7501, lastPoll),
                "1501ms heartbeat stall rejects completed frame");
        equal(ReplayFrameGuard.LEASE_EXPIRED,
                ReplayFrameGuard.reason(false, frameEpoch, frameEpoch, true, 5999, lastPoll),
                "backwards monotonic clock is never fresh");
        equal(ReplayFrameGuard.EPOCH_CHANGED,
                ReplayFrameGuard.reason(false, frameEpoch, frameEpoch + 1, true, 8000, 8000),
                "new control revision rejects old in-flight frame despite fresh heartbeat");
        equal(ReplayFrameGuard.INACTIVE,
                ReplayFrameGuard.reason(false, frameEpoch, frameEpoch, false, 8000, 8000),
                "pause rejects output despite fresh heartbeat");
        equal(ReplayFrameGuard.CLOSED,
                ReplayFrameGuard.reason(true, frameEpoch, frameEpoch, true, 8000, 8000),
                "closing the activity rejects output");
        // The same source index can be retried after expiry. The expired token
        // stays invalid even after polling resumes; a new attempt can succeed.
        long resumedEpoch = frameEpoch + 1;
        equal(ReplayFrameGuard.EPOCH_CHANGED,
                ReplayFrameGuard.reason(false, frameEpoch, resumedEpoch, true, 8200, 8200),
                "recovery cannot resurrect discarded epoch");
        equal(ReplayFrameGuard.ACCEPT,
                ReplayFrameGuard.reason(false, resumedEpoch, resumedEpoch, true, 8400, 8400),
                "retry under new epoch and fresh heartbeat recovers");
        check(ReplayFrameGuard.LEASE_MS == 1500, "lease duration was not weakened");
        System.out.println("ReplayFrameGuardTest: " + assertions + " assertions passed (fake clock; no emulator)");
    }

    private static void equal(int expected, int actual, String message) {
        check(expected == actual, message + " expected " + expected + " got " + actual);
    }

    private static void check(boolean condition, String message) {
        assertions++;
        if (!condition) throw new AssertionError(message);
    }
}
