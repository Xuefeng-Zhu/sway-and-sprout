package com.togethermove.tv;

/** Debug benchmark identity only; it never changes primary inference or control guards. */
enum ReplayReferenceProfile {
    SAMPLED("sampled"), OFF("off");

    final String id;
    ReplayReferenceProfile(String id) { this.id = id; }

    static ReplayReferenceProfile parse(String value) {
        if (value == null || "sampled".equals(value)) return SAMPLED;
        if ("off".equals(value)) return OFF;
        throw new IllegalArgumentException("Unknown native reference-check profile");
    }

    boolean checkFrame(int index, int frames) {
        if (frames < 1 || index < 0 || index >= frames) throw new IllegalArgumentException("Invalid frame index");
        return this == SAMPLED && (index < 3 || index % 30 == 0 || index + 1 == frames);
    }
}
