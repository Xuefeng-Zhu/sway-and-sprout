/* Copyright 2021 The TensorFlow Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.togethermove.tv;

/**
 * Geometry port of TensorFlow's Android MoveNet.kt dynamic crop algorithm.
 * Source commit bda6a8741864b7bc934345c47c25f8e17fd67bdc; source SHA256
 * bf2c97ccbe9d2abe154167c13b39749d38027fdfaf0a23e34b3480d602fc4ac8.
 * Input points are all 17 anatomical keypoints as original-pixel {x,y,score}.
 * .2 is the official crop-support score; it is NOT the game's confidence gate.
 * Uses Java float arithmetic to retain the Kotlin/RectF operation order.
 * This supplies geometry only; it does not claim image sampler pixel parity.
 */
public final class MoveNetCrop {
    public static final float MIN_CROP_KEYPOINT_SCORE = .2f;
    private static final float TORSO_EXPANSION_RATIO = 1.9f;
    private static final float BODY_EXPANSION_RATIO = 1.2f;
    private static final int LEFT_SHOULDER = 5, RIGHT_SHOULDER = 6;
    private static final int LEFT_HIP = 11, RIGHT_HIP = 12;
    private static final int[] TORSO = {LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP};
    private MoveNetCrop() {}

    public static final class Region {
        public final float left, top, right, bottom;
        public final boolean defaultCrop;
        private Region(float left, float top, float right, float bottom, boolean defaultCrop) {
            this.left = left; this.top = top; this.right = right; this.bottom = bottom;
            this.defaultCrop = defaultCrop;
        }
        public PixelPlan pixels(int imageWidth, int imageHeight, int inputSize) {
            dimensions(imageWidth, imageHeight);
            if (inputSize < 1) throw new IllegalArgumentException("positive model size required");
            return new PixelPlan(this, imageWidth, imageHeight, inputSize);
        }
    }

    /**
     * Mirrors RectF corner multiplication, width subtraction and Float.toInt.
     * detectWidth/Height are the temporary Bitmap dimensions. The official
     * sample then center-crops that bitmap to min(width,height) before resize.
     */
    public static final class PixelPlan {
        public final float left, top, right, bottom;
        public final int detectWidth, detectHeight, squareSize, centerCropLeft, centerCropTop, inputSize;
        public final float widthRatio, heightRatio;
        private PixelPlan(Region region, int width, int height, int inputSize) {
            this.inputSize = inputSize;
            left = region.left * width; top = region.top * height;
            right = region.right * width; bottom = region.bottom * height;
            detectWidth = (int) (right - left); detectHeight = (int) (bottom - top);
            if (detectWidth < 1 || detectHeight < 1) throw new IllegalArgumentException("empty integer crop");
            squareSize = Math.min(detectWidth, detectHeight);
            centerCropLeft = (detectWidth - squareSize) / 2;
            centerCropTop = (detectHeight - squareSize) / 2;
            widthRatio = (float) detectWidth / inputSize;
            heightRatio = (float) detectHeight / inputSize;
        }
        /** Exact sample output operation order, including its detect-dimension ratio. */
        public float restoreX(float normalizedX) {
            return normalizedX * inputSize * widthRatio + left;
        }
        public float restoreY(float normalizedY) {
            return normalizedY * inputSize * heightRatio + top;
        }
    }

    public static Region initial(int imageWidth, int imageHeight) {
        dimensions(imageWidth, imageHeight);
        float xMin, yMin, width, height;
        if (imageWidth > imageHeight) {
            width = 1f;
            height = (float) imageWidth / imageHeight;
            xMin = 0f;
            yMin = (imageHeight / 2f - imageWidth / 2f) / imageHeight;
        } else {
            height = 1f;
            width = (float) imageHeight / imageWidth;
            yMin = 0f;
            // Deliberately retain the source's integer imageHeight / 2 here.
            xMin = (imageWidth / 2f - imageHeight / 2) / imageWidth;
        }
        return new Region(xMin, yMin, xMin + width, yMin + height, true);
    }

    public static boolean torsoVisible(float[][] points) {
        pointsShape(points);
        return (points[LEFT_HIP][2] > MIN_CROP_KEYPOINT_SCORE || points[RIGHT_HIP][2] > MIN_CROP_KEYPOINT_SCORE)
                && (points[LEFT_SHOULDER][2] > MIN_CROP_KEYPOINT_SCORE || points[RIGHT_SHOULDER][2] > MIN_CROP_KEYPOINT_SCORE);
    }

    public static Region next(float[][] points, int imageWidth, int imageHeight) {
        dimensions(imageWidth, imageHeight);
        pointsShape(points);
        // Safety extension: the sample assumes valid model outputs. A malformed
        // or degenerate crop must not allocate an invalid bitmap or retain ROI.
        for (float[] point : points) {
            if (!Float.isFinite(point[0]) || !Float.isFinite(point[1]) || !Float.isFinite(point[2])
                    || point[2] < 0 || point[2] > 1) return initial(imageWidth, imageHeight);
        }
        if (!torsoVisible(points)) return initial(imageWidth, imageHeight);
        float centerX = (points[LEFT_HIP][0] + points[RIGHT_HIP][0]) / 2f;
        float centerY = (points[LEFT_HIP][1] + points[RIGHT_HIP][1]) / 2f;
        float maxTorsoX = 0f, maxTorsoY = 0f, maxBodyX = 0f, maxBodyY = 0f;
        for (int joint : TORSO) {
            float dx = Math.abs(centerX - points[joint][0]);
            float dy = Math.abs(centerY - points[joint][1]);
            if (dx > maxTorsoX) maxTorsoX = dx;
            if (dy > maxTorsoY) maxTorsoY = dy;
        }
        for (float[] point : points) {
            // Equality .2 is included in body extents; torso uses strict >.2.
            if (point[2] < MIN_CROP_KEYPOINT_SCORE) continue;
            float dx = Math.abs(centerX - point[0]);
            float dy = Math.abs(centerY - point[1]);
            if (dx > maxBodyX) maxBodyX = dx;
            if (dy > maxBodyY) maxBodyY = dy;
        }
        float half = Math.max(Math.max(maxTorsoX * TORSO_EXPANSION_RATIO, maxTorsoY * TORSO_EXPANSION_RATIO),
                Math.max(maxBodyX * BODY_EXPANSION_RATIO, maxBodyY * BODY_EXPANSION_RATIO));
        float edge = Math.max(Math.max(centerX, imageWidth - centerX), Math.max(centerY, imageHeight - centerY));
        half = Math.min(half, edge);
        float cornerY = centerY - half, cornerX = centerX - half;
        if (!Float.isFinite(half) || half <= 0 || half > Math.max(imageWidth, imageHeight) / 2f) {
            return initial(imageWidth, imageHeight);
        }
        float length = half * 2;
        Region result = new Region(cornerX / imageWidth, cornerY / imageHeight,
                (cornerX + length) / imageWidth, (cornerY + length) / imageHeight, false);
        // Valid very small float crops may truncate to zero in the source.
        // Retain a full-frame fallback instead of allowing Bitmap.createBitmap(0,...).
        if ((int) (result.right * imageWidth - result.left * imageWidth) < 1
                || (int) (result.bottom * imageHeight - result.top * imageHeight) < 1) return initial(imageWidth, imageHeight);
        return result;
    }

    private static void pointsShape(float[][] points) {
        if (points == null || points.length != 17) throw new IllegalArgumentException("17 {x,y,score} points required");
        for (float[] point : points) if (point == null || point.length != 3) throw new IllegalArgumentException("17 {x,y,score} points required");
    }
    private static void dimensions(int width, int height) {
        if (width < 1 || height < 1) throw new IllegalArgumentException("positive image dimensions required");
    }
}
