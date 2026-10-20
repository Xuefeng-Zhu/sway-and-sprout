package com.togethermove.tv;
import android.graphics.Bitmap;
import java.nio.ByteBuffer;
import org.tensorflow.lite.DataType;
import org.tensorflow.lite.support.image.ImageProcessor;
import org.tensorflow.lite.support.image.TensorImage;
import org.tensorflow.lite.support.image.ops.ResizeOp;
import org.tensorflow.lite.support.image.ops.ResizeWithCropOrPadOp;
/** Pinned official Support API path from TensorFlow Android MoveNet.kt. Debug parity only. */
final class MoveNetReferenceImage {
 static ByteBuffer prepare(Bitmap bitmap, int size) {
  int square = Math.min(bitmap.getWidth(), bitmap.getHeight());
  ImageProcessor processor = new ImageProcessor.Builder()
    .add(new ResizeWithCropOrPadOp(square, square))
    .add(new ResizeOp(size, size, ResizeOp.ResizeMethod.BILINEAR)).build();
  TensorImage image = new TensorImage(DataType.UINT8); image.load(bitmap);
  ByteBuffer result = processor.process(image).getBuffer().asReadOnlyBuffer(); result.rewind(); return result;
 }
}
