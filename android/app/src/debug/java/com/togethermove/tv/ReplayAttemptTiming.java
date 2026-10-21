package com.togethermove.tv;

/** Pure immutable timing deltas for every decode attempt, including discarded frames. */
final class ReplayAttemptTiming {
    static final class Sample {
        final long wallNanos, workerCpuNanos, processCpuMs;

        Sample(long wallNanos, long workerCpuNanos, long processCpuMs) {
            this.wallNanos = wallNanos;
            this.workerCpuNanos = workerCpuNanos;
            this.processCpuMs = processCpuMs;
        }
    }

    private final Sample start, decoded, guardFinished, processingEnd, decision;

    ReplayAttemptTiming(Sample start, Sample decoded, Sample finished) {
        this(start, decoded, decoded, finished);
    }

    ReplayAttemptTiming(Sample start, Sample decoded, Sample guardFinished, Sample processingEnd) {
        this(start, decoded, guardFinished, processingEnd,
                processingEnd == null ? guardFinished : processingEnd);
    }

    ReplayAttemptTiming(Sample start, Sample decoded, Sample guardFinished, Sample processingEnd, Sample decision) {
        this.start = start;
        this.decoded = decoded;
        this.guardFinished = guardFinished;
        this.processingEnd = processingEnd;
        this.decision = decision;
    }

    boolean inferenceStarted() { return guardFinished != null && processingEnd != null; }
    double decWallMs() { return wall(start, decoded); }
    double decWorkerCpuMs() { return worker(start, decoded); }
    double decProcessCpuMs() { return process(start, decoded); }
    double guardWallMs() { return wall(decoded, guardFinished); }
    double guardWorkerCpuMs() { return worker(decoded, guardFinished); }
    double guardProcessCpuMs() { return process(decoded, guardFinished); }
    // The model stage covers the whole infer call, including preprocessing and reference checks.
    double modelWallMs() { return wall(guardFinished, processingEnd); }
    double modelWorkerCpuMs() { return worker(guardFinished, processingEnd); }
    double modelProcessCpuMs() { return process(guardFinished, processingEnd); }
    double postGuardWallMs() { return wall(processingEnd, decision); }
    double postGuardWorkerCpuMs() { return worker(processingEnd, decision); }
    double postGuardProcessCpuMs() { return process(processingEnd, decision); }
    // Retains the historical decode + model measurement, before the final eligibility lock.
    double processingWallMs() { return wall(start, processingEnd == null ? decoded : processingEnd); }
    double totalWallMs() { return wall(start, end()); }
    double totalWorkerCpuMs() { return worker(start, end()); }
    double totalProcessCpuMs() { return process(start, end()); }

    private Sample end() {
        if (decision != null) return decision;
        if (processingEnd != null) return processingEnd;
        return guardFinished == null ? decoded : guardFinished;
    }
    private static double delta(long first, long last, double divisor) {
        return first < 0 || last < first ? Double.NaN : (last - first) / divisor;
    }
    private static double wall(Sample first, Sample last) {
        return first == null || last == null ? Double.NaN : delta(first.wallNanos, last.wallNanos, 1000000.0);
    }
    private static double worker(Sample first, Sample last) {
        return first == null || last == null ? Double.NaN : delta(first.workerCpuNanos, last.workerCpuNanos, 1000000.0);
    }
    private static double process(Sample first, Sample last) {
        return first == null || last == null ? Double.NaN : delta(first.processCpuMs, last.processCpuMs, 1.0);
    }
}
