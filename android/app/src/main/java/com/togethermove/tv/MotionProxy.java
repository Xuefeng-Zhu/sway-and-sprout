package com.togethermove.tv;

import android.webkit.WebResourceResponse;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Semaphore;

/** Debug-only, fixed-destination event transport. It never accepts images or arbitrary URLs. */
final class MotionProxy {
 private static final String ENDPOINT = "http://10.0.2.2:8765/motion/events?";
 private static final int MAX_RESPONSE_BYTES = 32768;
 private static final Semaphore REQUEST_SLOT = new Semaphore(1);
 private MotionProxy() {}

 static WebResourceResponse events(String method, String rawQuery) {
  if (!BuildConfig.DEBUG) return error(503, "proxy_disabled");
  if (!"GET".equals(method)) return error(405, "method_not_allowed");
  String query;
  try { query = MotionQuery.canonicalize(rawQuery); }
  catch (IllegalArgumentException e) { return error(400, "invalid_motion_query"); }
  if (!REQUEST_SLOT.tryAcquire()) return error(429, "motion_proxy_busy");
  HttpURLConnection connection = null;
  long deadline = System.nanoTime() + 2000000000L;
  try {
   connection = (HttpURLConnection) new URL(ENDPOINT + query).openConnection();
   connection.setRequestMethod("GET");
   connection.setInstanceFollowRedirects(false);
   connection.setConnectTimeout(750);
   connection.setReadTimeout(750);
   connection.setUseCaches(false);
   connection.setRequestProperty("Accept", "application/json");
   connection.setRequestProperty("Cache-Control", "no-store");
   if (connection.getResponseCode() != 200) return error(502, "sidecar_unavailable");
   String contentType = connection.getContentType();
   if (contentType == null || !contentType.split(";", 2)[0].trim().equalsIgnoreCase("application/json")) return error(502, "invalid_sidecar_response");
   int declaredLength = connection.getContentLength();
   if (declaredLength > MAX_RESPONSE_BYTES) return error(502, "sidecar_response_too_large");
   ByteArrayOutputStream body = new ByteArrayOutputStream();
   try (InputStream input = connection.getInputStream()) {
    byte[] chunk = new byte[2048];
    int count;
    while ((count = input.read(chunk)) != -1) {
     if (System.nanoTime() > deadline) return error(504, "sidecar_timeout");
     if (body.size() + count > MAX_RESPONSE_BYTES) return error(502, "sidecar_response_too_large");
     body.write(chunk, 0, count);
    }
   }
   byte[] json = body.toByteArray();
   new JSONObject(new String(json, StandardCharsets.UTF_8));
   return response(200, json);
  } catch (java.net.SocketTimeoutException e) { return error(504, "sidecar_timeout"); }
  catch (Exception e) { return error(502, "sidecar_unavailable"); }
  finally { if (connection != null) connection.disconnect(); REQUEST_SLOT.release(); }
 }

 private static WebResourceResponse error(int status, String code) {
  return response(status, ("{\"ok\":false,\"error\":\"" + code + "\",\"events\":[]}").getBytes(StandardCharsets.UTF_8));
 }
 private static WebResourceResponse response(int status, byte[] body) {
  Map<String, String> headers = new HashMap<>();
  headers.put("Cache-Control", "no-store, max-age=0");
  headers.put("Pragma", "no-cache");
  headers.put("X-Content-Type-Options", "nosniff");
  return new WebResourceResponse("application/json", "UTF-8", status, status == 200 ? "OK" : "Motion transport error", headers, new ByteArrayInputStream(body));
 }
}
