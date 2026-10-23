package com.togethermove.tv;

/** Reusable RGB bytes for the UINT8 model and API-25-compatible CRC32.update(byte[]). */
final class NativeRgbPacking {
    static final class Totals {
        final long red, green, blue;
        final int nonzero;
        Totals(long red, long green, long blue, int nonzero) {
            this.red = red; this.green = green; this.blue = blue; this.nonzero = nonzero;
        }
    }
    private NativeRgbPacking() {}

    static Totals pack(int[] pixels, byte[] rgb) {
        if (pixels == null || rgb == null || (long) pixels.length * 3 != rgb.length) {
            throw new IllegalArgumentException("Exact RGB output size required");
        }
        long red = 0, green = 0, blue = 0;
        int nonzero = 0, offset = 0;
        for (int pixel : pixels) {
            int r = (pixel >>> 16) & 255, g = (pixel >>> 8) & 255, b = pixel & 255;
            rgb[offset++] = (byte) r; rgb[offset++] = (byte) g; rgb[offset++] = (byte) b;
            red += r; green += g; blue += b;
            nonzero += (r == 0 ? 0 : 1) + (g == 0 ? 0 : 1) + (b == 0 ? 0 : 1);
        }
        return new Totals(red, green, blue, nonzero);
    }
}
