package com.togethermove.tv;
import android.app.Activity;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import java.io.ByteArrayInputStream;
/** Local asset host. Debug builds opt into bounded recorded-video inference; no TV camera or JS bridge. */
public class MainActivity extends Activity {
 private WebView web;
 private MotionSource nativeVideo;
 private static boolean isAppOrigin(android.net.Uri url) {
  return "https".equals(url.getScheme()) && "app.togethermove.local".equals(url.getHost()) && (url.getPort() == -1 || url.getPort() == 443);
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
  nativeVideo=NativeVideoFactory.create(this,getIntent());
  if(BuildConfig.DEBUG)WebView.setWebContentsDebuggingEnabled(true);
  web=new WebView(this);
  WebSettings settings=web.getSettings();
  settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
  settings.setAllowFileAccess(false); settings.setAllowContentAccess(false);
  // Remote keys reach the app through evaluateJavascript, not trusted DOM gestures.
  // The app's default-off spoken-prompts control explicitly gates bundled audio.
  settings.setMediaPlaybackRequiresUserGesture(false);
  web.setWebViewClient(new WebViewClient(){
   @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
    if (!isAppOrigin(request.getUrl())) return new WebResourceResponse("text/plain","UTF-8",new ByteArrayInputStream(new byte[0]));
    if ("/motion/events".equals(request.getUrl().getEncodedPath())) return nativeVideo!=null?nativeVideo.events(request.getMethod(),request.getUrl().getEncodedQuery()):MotionProxy.events(request.getMethod(),request.getUrl().getEncodedQuery());
    if (nativeVideo!=null && "/motion/preview".equals(request.getUrl().getEncodedPath())) return nativeVideo.preview(request.getMethod(),request.getUrl().getEncodedQuery());
    String path=request.getUrl().getPath(); if(path==null||path.equals("/"))path="/index.html";
    if(path.contains(".."))return new WebResourceResponse("text/plain","UTF-8",new ByteArrayInputStream(new byte[0]));
    String mime=path.endsWith(".js")?"application/javascript":path.endsWith(".css")?"text/css":path.endsWith(".png")?"image/png":path.endsWith(".svg")?"image/svg+xml":path.endsWith(".mp3")?"audio/mpeg":path.endsWith(".json")?"application/json":"text/html";
    try{return new WebResourceResponse(mime,mime.startsWith("audio/")?null:"UTF-8",getAssets().open("web"+path));}
    catch(Exception e){return new WebResourceResponse("text/plain","UTF-8",new ByteArrayInputStream(new byte[0]));}
   }
   @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){return !isAppOrigin(request.getUrl());}
  });
  setContentView(web); web.loadUrl("https://app.togethermove.local/"+(nativeVideo!=null?"?input=video-verification":""));
 }
 @Override public boolean dispatchKeyEvent(KeyEvent event){
  String key=null;
  switch(event.getKeyCode()){
   case KeyEvent.KEYCODE_DPAD_UP:key="ArrowUp";break;
   case KeyEvent.KEYCODE_DPAD_DOWN:key="ArrowDown";break;
   case KeyEvent.KEYCODE_DPAD_LEFT:key="ArrowLeft";break;
   case KeyEvent.KEYCODE_DPAD_RIGHT:key="ArrowRight";break;
   case KeyEvent.KEYCODE_DPAD_CENTER: case KeyEvent.KEYCODE_ENTER:key="Enter";break;
   case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:key="MediaPlayPause";break;
   case KeyEvent.KEYCODE_BACK:
    if(event.getAction()==KeyEvent.ACTION_DOWN && event.getRepeatCount()==0)
     web.evaluateJavascript("window.togetherMoveKey && window.togetherMoveKey('Back')", result->{if("false".equals(result))finish();});
    return true;
  }
  if(key!=null){if(event.getAction()==KeyEvent.ACTION_DOWN && event.getRepeatCount()==0)web.evaluateJavascript("window.togetherMoveKey && window.togetherMoveKey('"+key+"')",null);return true;}
  return super.dispatchKeyEvent(event);
 }
 @Override protected void onPause(){if(nativeVideo!=null)nativeVideo.suspend();web.evaluateJavascript("window.togetherMoveSuspend && window.togetherMoveSuspend()",null);web.onPause();super.onPause();}
 @Override protected void onResume(){super.onResume();if(web!=null)web.onResume();if(nativeVideo!=null)nativeVideo.resume();}
 @Override protected void onDestroy(){if(nativeVideo!=null)nativeVideo.close();web.destroy();super.onDestroy();}
}
