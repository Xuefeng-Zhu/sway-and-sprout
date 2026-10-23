package com.togethermove.tv;

import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Random;
import java.util.zip.CRC32;

/** Compare complete tensor bytes and checksums against the previous per-byte recipe. */
public final class NativeRgbPackingTest {
    public static void main(String[] args) {
        Random random = new Random(20261023L);
        for (int size : new int[]{0, 1, 256, 192 * 192, 256 * 256}) {
            int[] pixels = new int[size];
            for (int i = 0; i < size; i++) pixels[i] = random.nextInt();
            if (size >= 4) { pixels[0] = 0; pixels[1] = -1; pixels[2] = 0xFF0080FF; pixels[3] = 0x00FF8000; }
            ByteBuffer previous = ByteBuffer.allocateDirect(size * 3);
            long red = 0, green = 0, blue = 0;
            int nonzero = 0;
            for (int pixel : pixels) {
                int r = (pixel >>> 16) & 255, g = (pixel >>> 8) & 255, b = pixel & 255;
                previous.put((byte) r); previous.put((byte) g); previous.put((byte) b);
                red += r; green += g; blue += b;
                nonzero += (r == 0 ? 0 : 1) + (g == 0 ? 0 : 1) + (b == 0 ? 0 : 1);
            }
            previous.flip();
            byte[] expected = new byte[size * 3]; previous.asReadOnlyBuffer().get(expected);
            byte[] actual = new byte[size * 3]; Arrays.fill(actual, (byte) 42);
            NativeRgbPacking.Totals totals = NativeRgbPacking.pack(pixels, actual);
            check(Arrays.equals(expected, actual), "RGB bytes differ");
            CRC32 oldCrc = new CRC32(); oldCrc.update(previous.asReadOnlyBuffer());
            CRC32 newCrc = new CRC32(); newCrc.update(actual, 0, actual.length);
            check(oldCrc.getValue() == newCrc.getValue(), "checksum differs");
            check(totals.red == red && totals.green == green && totals.blue == blue && totals.nonzero == nonzero, "diagnostic totals differ");
            NativeRgbPacking.pack(pixels, actual);
            check(Arrays.equals(expected, actual), "reuse changes bytes");
        }
        try { NativeRgbPacking.pack(new int[1], new byte[2]); throw new AssertionError("invalid size accepted"); }
        catch (IllegalArgumentException expected) {}
        System.out.println("NativeRgbPackingTest passed (RGB byte/checksum parity; no inference)");
    }
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
}
