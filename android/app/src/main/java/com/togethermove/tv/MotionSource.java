package com.togethermove.tv;
import android.webkit.WebResourceResponse;
/** Local in-process debug input; no camera or network required. */
public interface MotionSource {
 WebResourceResponse events(String method,String rawQuery);
 WebResourceResponse preview(String method,String rawQuery);
 default void suspend() {}
 default void resume() {}
 void close();
}
