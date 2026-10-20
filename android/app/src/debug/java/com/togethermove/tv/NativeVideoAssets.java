package com.togethermove.tv;

import android.content.res.AssetManager;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Debug APK assets only. Never accepts a filesystem path, URI, camera, or network source. */
final class NativeVideoAssets {
    static final String RUNTIME_VERSION = "1.4.2";
    static final String MODEL_SHA256 = "cd7cc22fa946e5d146a7b98d496853e1923e22828d3972d579973f27f91bb105";
    static final int MODEL_BYTES = 2894840;
    static final ModelPin INT8_MODEL = new ModelPin("int8", "verification/movenet-lightning-int8.tflite", MODEL_SHA256, MODEL_BYTES, 192);
    static final ModelPin FLOAT16_MODEL = new ModelPin("float16", "verification/movenet-lightning-float16.tflite",
            "0fac2226112d0371903ca86e3853cec24ef603a0b2f96f589b180f0ebdd135ab", 4758512, 192);
    static final ModelPin THUNDER_MODEL = new ModelPin("thunder", "verification/movenet-thunder-float16.tflite",
            "41641538679ec79b07d4101e591dda47d098c09af29607674b2a40b8a3798dd3", 12584128, 256);
    static final class ModelPin {
        final String id, asset, sha256;
        final int bytes, inputSize;
        private ModelPin(String id, String asset, String sha256, int bytes, int inputSize) {
            this.id = id; this.asset = asset; this.sha256 = sha256; this.bytes = bytes; this.inputSize = inputSize;
        }
    }
    static ModelPin modelPin(String configAsset) {
        if (configAsset == null || !configAsset.matches("verification/(clear|frontal|nearface|right-negative|both-up-negative|natural-original|natural-mirror)(\\.(float16|thunder))?\\.json")) {
            throw new IllegalArgumentException("config_asset_not_allowed");
        }
        return configAsset.endsWith(".thunder.json") ? THUNDER_MODEL : configAsset.endsWith(".float16.json") ? FLOAT16_MODEL : INT8_MODEL;
    }
    static final int MAX_VIDEO_BYTES = 256 * 1024 * 1024;
    final ModelPin modelPin;
    final String configAsset;
    final String modelAsset;
    final String videoAsset;
    final String videoSha256;
    final int videoBytes;
    final double fps;
    final int frames;
    final List<String> expectedGestures;
    final boolean expectationKnown;
    final ByteBuffer modelBuffer;

    NativeVideoAssets(AssetManager assets, String configPath) throws IOException, JSONException {
        modelPin = modelPin(configPath);
        configAsset = configPath;
        JSONObject config = new JSONObject(new String(read(assets, configPath, 65536), java.nio.charset.StandardCharsets.UTF_8));
        if (config.getInt("schemaVersion") != 1 || !RUNTIME_VERSION.equals(config.getString("runtimeVersion"))) {
            throw new IOException("config_schema_or_runtime");
        }
        JSONObject model = config.getJSONObject("model");
        modelAsset = localAsset(model.getString("asset"), "tflite");
        if (!modelPin.asset.equals(modelAsset) || model.getLong("bytes") != modelPin.bytes || !modelPin.sha256.equals(model.getString("sha256"))) {
            throw new IOException("model_pin_mismatch");
        }
        JSONObject fixture = config.getJSONObject("fixture");
        videoAsset = localAsset(fixture.getString("asset"), "mp4");
        videoSha256 = fixture.getString("sha256");
        long declaredBytes = fixture.getLong("bytes");
        if (!videoSha256.matches("[0-9a-f]{64}") || declaredBytes < 1 || declaredBytes > MAX_VIDEO_BYTES) {
            throw new IOException("fixture_pin_invalid");
        }
        videoBytes = (int) declaredBytes;
        fps = fixture.getDouble("fps");
        frames = fixture.getInt("frames");
        if (!Double.isFinite(fps) || fps < 1 || fps > 120 || frames < 1 || frames > 3600 || frames * 1000.0 / fps > 30000.1) {
            throw new IOException("fixture_duration_invalid");
        }
        expectationKnown = fixture.getBoolean("expectationKnown");
        JSONArray expected = fixture.getJSONArray("expectedGestures");
        if (expected.length() > 64) throw new IOException("expected_gestures_limit");
        List<String> names = new ArrayList<>();
        for (int i = 0; i < expected.length(); i++) {
            String name = expected.getString(i);
            if (!("left-raise".equals(name) || "right-raise".equals(name))) throw new IOException("expected_gesture_invalid");
            names.add(name);
        }
        expectedGestures = Collections.unmodifiableList(names);
        byte[] modelBytes = read(assets, modelAsset, modelPin.bytes);
        if (modelBytes.length != modelPin.bytes || !modelPin.sha256.equals(sha256(modelBytes))) throw new IOException("model_hash_or_size_mismatch");
        modelBuffer = ByteBuffer.allocateDirect(modelPin.bytes).order(ByteOrder.nativeOrder());
        modelBuffer.put(modelBytes).rewind();
        verifyStreaming(assets, videoAsset, videoBytes, videoSha256);
    }

    private static String localAsset(String path, String extension) throws IOException {
        if (path == null || !path.matches("verification/[A-Za-z0-9_-][A-Za-z0-9._-]*\\." + extension)) {
            throw new IOException("asset_path_not_allowed");
        }
        return path;
    }

    private static byte[] read(AssetManager assets, String path, int limit) throws IOException {
        try (InputStream input = assets.open(path); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int total = 0;
            int size;
            while ((size = input.read(buffer)) != -1) {
                total += size;
                if (total > limit) throw new IOException("asset_size_limit");
                output.write(buffer, 0, size);
            }
            return output.toByteArray();
        }
    }

    private static void verifyStreaming(AssetManager assets, String path, int bytes, String expected) throws IOException {
        MessageDigest digest = digest();
        long total = 0;
        try (InputStream input = assets.open(path)) {
            byte[] buffer = new byte[65536];
            int size;
            while ((size = input.read(buffer)) != -1) {
                total += size;
                if (total > bytes || total > MAX_VIDEO_BYTES) throw new IOException("fixture_size_mismatch");
                digest.update(buffer, 0, size);
            }
        }
        if (total != bytes || !expected.equals(hex(digest.digest()))) throw new IOException("fixture_hash_or_size_mismatch");
    }

    private static String sha256(byte[] bytes) throws IOException {
        return hex(digest().digest(bytes));
    }

    private static MessageDigest digest() throws IOException {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException e) { throw new IOException("sha256_unavailable", e); }
    }

    private static String hex(byte[] bytes) {
        char[] chars = "0123456789abcdef".toCharArray();
        char[] output = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            output[i * 2] = chars[(bytes[i] & 255) >>> 4];
            output[i * 2 + 1] = chars[bytes[i] & 15];
        }
        return new String(output);
    }
}
