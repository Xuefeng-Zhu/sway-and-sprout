package com.togethermove.tv;

import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Frozen debug assets only. Ground-truth annotations are never read by inference. */
final class NativeCalibrationAssets {
    static final int MAX_IMAGE_BYTES = 8 * 1024 * 1024;
    static final int MAX_PIXELS = 4 * 1024 * 1024;
    static final class Image {
        final String id, asset, sha256, split;
        final int bytes, width, height;
        Image(JSONObject value) throws IOException, JSONException {
            id = value.getString("id"); asset = value.getString("asset"); sha256 = value.getString("sha256");
            split = value.getString("split"); bytes = integer(value, "bytes");
            width = integer(value, "width"); height = integer(value, "height");
            if (!id.matches("[A-Za-z0-9_-]{1,80}") || !sha256.matches("[0-9a-f]{64}")
                    || !asset.equals("calibration/" + sha256 + ".jpg")
                    || !(split.equals("calibration") || split.equals("heldout"))
                    || bytes < 1 || bytes > MAX_IMAGE_BYTES || width < 32 || height < 32
                    || width > 4096 || height > 4096 || (long) width * height > MAX_PIXELS) {
                throw new IOException("image_contract");
            }
        }
    }
    static List<Image> images(AssetManager assets, String selectedSplit) throws IOException, JSONException {
        if (!NativeCalibrationPins.ENABLED) throw new IOException("calibration_not_prepared");
        byte[] bytes = verified(assets, NativeCalibrationPins.MANIFEST_ASSET,
                NativeCalibrationPins.MANIFEST_BYTES, NativeCalibrationPins.MANIFEST_SHA256, 4 * 1024 * 1024);
        JSONObject manifest = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
        if (integer(manifest, "schemaVersion") != 1) throw new IOException("manifest_schema");
        JSONArray entries = manifest.getJSONArray("images");
        if (entries.length() < 2 || entries.length() > 1000) throw new IOException("manifest_count");
        List<Image> selected = new ArrayList<>(); Set<String> ids = new HashSet<>(), hashes = new HashSet<>();
        boolean calibration = false, heldout = false;
        for (int index = 0; index < entries.length(); index++) {
            Image image = new Image(entries.getJSONObject(index));
            if (!ids.add(image.id) || !hashes.add(image.sha256)) throw new IOException("duplicate_image");
            calibration |= image.split.equals("calibration"); heldout |= image.split.equals("heldout");
            if (image.split.equals(selectedSplit)) selected.add(image);
        }
        if (!calibration || !heldout || selected.isEmpty()) throw new IOException("split_contract");
        return selected;
    }
    static Bitmap bitmap(AssetManager assets, Image image) throws IOException {
        byte[] data = verified(assets, image.asset, image.bytes, image.sha256, MAX_IMAGE_BYTES);
        BitmapFactory.Options bounds = new BitmapFactory.Options(); bounds.inJustDecodeBounds = true; bounds.inScaled = false;
        BitmapFactory.decodeByteArray(data, 0, data.length, bounds);
        if (bounds.outWidth != image.width || bounds.outHeight != image.height
                || !"image/jpeg".equals(bounds.outMimeType)) throw new IOException("decoded_bounds");
        BitmapFactory.Options options = new BitmapFactory.Options(); options.inPreferredConfig = Bitmap.Config.ARGB_8888; options.inScaled = false;
        Bitmap bitmap = BitmapFactory.decodeByteArray(data, 0, data.length, options);
        if (bitmap == null) throw new IOException("image_decode");
        if (bitmap.getWidth() != image.width || bitmap.getHeight() != image.height) {
            bitmap.recycle(); throw new IOException("decoded_size");
        }
        return bitmap;
    }
    static ByteBuffer model(AssetManager assets, NativeVideoAssets.ModelPin pin) throws IOException {
        if (pin != NativeVideoAssets.INT8_MODEL && pin != NativeVideoAssets.FLOAT16_MODEL) throw new IOException("model_not_allowed");
        byte[] data = verified(assets, pin.asset, pin.bytes, pin.sha256, 8 * 1024 * 1024);
        ByteBuffer buffer = ByteBuffer.allocateDirect(data.length).order(ByteOrder.nativeOrder());
        buffer.put(data).rewind(); return buffer;
    }
    private static byte[] verified(AssetManager assets, String name, int expectedBytes, String expectedSha, int limit) throws IOException {
        if (expectedBytes < 1 || expectedBytes > limit || !expectedSha.matches("[0-9a-f]{64}")) throw new IOException("asset_pin");
        ByteArrayOutputStream output = new ByteArrayOutputStream(expectedBytes);
        try (InputStream input = assets.open(name)) {
            byte[] buffer = new byte[65536]; int size, total = 0;
            while ((size = input.read(buffer)) != -1) {
                total += size; if (total > expectedBytes) throw new IOException("asset_size");
                output.write(buffer, 0, size);
            }
        }
        byte[] data = output.toByteArray();
        if (data.length != expectedBytes || !sha256(data).equals(expectedSha)) throw new IOException("asset_integrity");
        return data;
    }
    private static String sha256(byte[] data) throws IOException {
        try {
            StringBuilder hex = new StringBuilder();
            for (byte value : MessageDigest.getInstance("SHA-256").digest(data)) hex.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
            return hex.toString();
        } catch (NoSuchAlgorithmException error) { throw new IOException("sha256_unavailable", error); }
    }
    private static int integer(JSONObject value, String name) throws IOException, JSONException {
        Object raw = value.get(name);
        if (!(raw instanceof Number)) throw new IOException("integer_required");
        double number = ((Number) raw).doubleValue();
        if (!Double.isFinite(number) || number != Math.rint(number) || number < Integer.MIN_VALUE || number > Integer.MAX_VALUE) throw new IOException("integer_required");
        return (int) number;
    }
    private NativeCalibrationAssets() {}
}
