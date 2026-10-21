package com.togethermove.tv;

/** Build-time-only authorization; no intent can select a dataset or hash. */
final class NativeCalibrationPins {
    static final boolean ENABLED = BuildConfig.NATIVE_CALIBRATION_ENABLED;
    static final String DATASET_ID = BuildConfig.NATIVE_CALIBRATION_DATASET_ID;
    static final String MANIFEST_SHA256 = BuildConfig.NATIVE_CALIBRATION_MANIFEST_SHA256;
    static final int MANIFEST_BYTES = BuildConfig.NATIVE_CALIBRATION_MANIFEST_BYTES;
    static final String MANIFEST_ASSET = "calibration/manifest.json";
    private NativeCalibrationPins() {}
}
