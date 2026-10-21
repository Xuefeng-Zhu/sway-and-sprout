package com.togethermove.tv;

/**
 * Pure eligibility check for a completed replay frame. Processing duration does
 * not extend or shorten the existing control lease: only fresh control polls do.
 * Reason codes are bounded primitive diagnostics, never pixels or landmarks.
 */
final class ReplayFrameGuard {
    static final long LEASE_MS = 1500;
    static final int ACCEPT = 0;
    static final int CLOSED = 1;
    static final int EPOCH_CHANGED = 2;
    static final int INACTIVE = 3;
    static final int LEASE_EXPIRED = 4;

    private ReplayFrameGuard() {}

    static boolean leaseFresh(long now, long lastPoll) {
        // The subtraction follows the monotonic clock used by the replay. A
        // backwards clock is not a fresh heartbeat and must not admit output.
        return now >= lastPoll && now - lastPoll <= LEASE_MS;
    }

    static int reason(boolean closed, long tokenEpoch, long currentEpoch,
                      boolean running, long now, long lastPoll) {
        if (closed) return CLOSED;
        if (tokenEpoch != currentEpoch) return EPOCH_CHANGED;
        if (!running) return INACTIVE;
        if (!leaseFresh(now, lastPoll)) return LEASE_EXPIRED;
        return ACCEPT;
    }
}
