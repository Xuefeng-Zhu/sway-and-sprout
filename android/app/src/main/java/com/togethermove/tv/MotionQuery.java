package com.togethermove.tv;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

/** Pure validation shared by the fixed native proxy and its host-side tests. */
final class MotionQuery {
 private static final Pattern UUID = Pattern.compile("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
 private static final long MAX_SAFE_INTEGER = 9007199254740991L;
 private MotionQuery() {}

 static String canonicalize(String raw) {
  if (raw == null || raw.length() > 512) throw new IllegalArgumentException("query_size");
  Map<String, String> values = new HashMap<>();
  String[] pairs = raw.split("&", -1);
  if (pairs.length != 6) throw new IllegalArgumentException("query_fields");
  for (String pair : pairs) {
   int equals = pair.indexOf('=');
   if (equals <= 0 || equals != pair.lastIndexOf('=')) throw new IllegalArgumentException("query_pair");
   String key = pair.substring(0, equals), value = pair.substring(equals + 1);
   // None of the six fields needs URL escapes. Reject escapes, duplicate keys and unknown keys.
   if (!(key.equals("clientId") || key.equals("roundId") || key.equals("revision") || key.equals("active") || key.equals("mode") || key.equals("after")) || values.put(key, value) != null)
    throw new IllegalArgumentException("query_key");
  }
  String client = uuid(values.get("clientId")), round = uuid(values.get("roundId"));
  String revision = integer(values.get("revision")), after = integer(values.get("after"));
  String active = values.get("active"), mode = values.get("mode");
  if (!("0".equals(active) || "1".equals(active))) throw new IllegalArgumentException("query_active");
  if (!("seated".equals(mode) || "standing".equals(mode))) throw new IllegalArgumentException("query_mode");
  return "clientId=" + client + "&roundId=" + round + "&revision=" + revision + "&active=" + active + "&mode=" + mode + "&after=" + after;
 }

 private static String uuid(String value) {
  if (value == null || !UUID.matcher(value).matches()) throw new IllegalArgumentException("query_uuid");
  return value.toLowerCase(Locale.ROOT);
 }
 private static String integer(String value) {
  if (value == null || !value.matches("[0-9]{1,16}")) throw new IllegalArgumentException("query_integer");
  long parsed;
  try { parsed = Long.parseLong(value); } catch (NumberFormatException e) { throw new IllegalArgumentException("query_integer"); }
  if (parsed > MAX_SAFE_INTEGER) throw new IllegalArgumentException("query_integer");
  return Long.toString(parsed);
 }
}
