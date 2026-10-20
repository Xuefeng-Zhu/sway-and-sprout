package com.togethermove.tv;

/**
 * Letterbox geometry shared by preprocessing and MoveNet landmark restoration.
 * This is the explicit integer Canvas baseline. The runtime bilinearly samples
 * into this rectangle; this class supplies geometry, not an image sampler.
 * It does not assert TensorFlow resize_with_pad pixel or rounding parity.
 */
public final class PoseCoordinates {
    public static final int MODEL_SIZE = 192;

    private PoseCoordinates() {}

    /**
     * Integer resize and centered padding for an aspect preserving model input.
     * Pixel geometry is retained explicitly because floor rounding can give the
     * two axes slightly different effective resize scales.
     */
    public static final class Plan {
        public final int originalWidth;
        public final int originalHeight;
        public final int targetSize;
        public final int resizedWidth;
        public final int resizedHeight;
        public final int padLeft;
        public final int padTop;
        public final double scaleX;
        public final double scaleY;

        private Plan(int width, int height, int target) {
            if (width <= 0 || height <= 0 || target <= 0) {
                throw new IllegalArgumentException("positive image and target dimensions required");
            }
            originalWidth = width;
            originalHeight = height;
            targetSize = target;
            double scale = Math.min((double) target / width, (double) target / height);
            resizedWidth = (int) Math.floor(width * scale);
            resizedHeight = (int) Math.floor(height * scale);
            if (resizedWidth == 0 || resizedHeight == 0) {
                throw new IllegalArgumentException("image aspect ratio produces an empty model image");
            }
            padLeft = (target - resizedWidth) / 2;
            padTop = (target - resizedHeight) / 2;
            scaleX = (double) resizedWidth / width;
            scaleY = (double) resizedHeight / height;
        }

        /**
         * Restores a [normalized y, normalized x, confidence] model landmark to
         * original image pixels. Padding, invalid values and invalid confidence
         * return null; low but valid confidence is retained for the gesture gate.
         * Image-edge coordinates are inclusive, matching normalized image bounds.
         */
        public PoseGestureMachine.Point restore(double normalizedY, double normalizedX,
                                                double confidence) {
            if (!Double.isFinite(normalizedY) || !Double.isFinite(normalizedX)
                    || !Double.isFinite(confidence) || confidence < 0 || confidence > 1
                    || normalizedY < 0 || normalizedY > 1
                    || normalizedX < 0 || normalizedX > 1) {
                return null;
            }
            double modelX = normalizedX * targetSize;
            double modelY = normalizedY * targetSize;
            if (modelX < padLeft || modelX > padLeft + resizedWidth
                    || modelY < padTop || modelY > padTop + resizedHeight) {
                return null;
            }
            return new PoseGestureMachine.Point((modelX - padLeft) / scaleX,
                    (modelY - padTop) / scaleY, confidence);
        }
    }

    public static Plan plan(int width, int height) {
        return plan(width, height, MODEL_SIZE);
    }

    public static Plan plan(int width, int height, int targetSize) {
        return new Plan(width, height, targetSize);
    }
}
