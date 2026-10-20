package com.togethermove.tv;

/** Deterministic host-Java contract tests; no Android device, camera or network. */
public final class MotionQueryTest {
 private static int assertions;
 private static final String BASE = "clientId=12345678-1234-1234-1234-123456789abc&roundId=87654321-abcd-abcd-abcd-cba987654321&revision=0&active=1&mode=seated&after=0";
 private static void accepts(String query) {
  String canonical = MotionQuery.canonicalize(query);
  if (!canonical.startsWith("clientId=") || canonical.indexOf('%') >= 0) throw new AssertionError("noncanonical");
  assertions++;
 }
 private static void rejects(String query) {
  try { MotionQuery.canonicalize(query); } catch (IllegalArgumentException expected) { assertions++; return; }
  throw new AssertionError("Accepted invalid query: " + query);
 }
 public static void main(String[] args) {
  accepts(BASE);
  accepts(BASE.replace("seated", "standing").replace("active=1", "active=0"));
  accepts(BASE.replace("revision=0", "revision=9007199254740991").replace("after=0", "after=9007199254740991"));
  accepts(BASE.toUpperCase(java.util.Locale.ROOT).replace("CLIENTID", "clientId").replace("ROUNDID", "roundId").replace("REVISION", "revision").replace("ACTIVE", "active").replace("MODE", "mode").replace("AFTER", "after").replace("SEATED", "seated"));
  rejects(null); rejects(""); rejects(BASE + "&url=http://example.com");
  rejects(BASE.replace("after=0", "mode=standing"));
  rejects(BASE.replace("active=1", "active=true"));
  rejects(BASE.replace("seated", "unknown"));
  rejects(BASE.replace("revision=0", "revision=-1"));
  rejects(BASE.replace("revision=0", "revision=1.5"));
  rejects(BASE.replace("revision=0", "revision=9007199254740992"));
  rejects(BASE.replace("after=0", "after=9999999999999999999999"));
  rejects(BASE.replace("after=0", "after=0=1"));
  rejects(BASE.replace("roundId=87654321-abcd-abcd-abcd-cba987654321", "roundId=1-1-1-1-1"));
  rejects(BASE.replace("clientId=", "clientId=%20"));
  rejects(BASE.replace("after=0", "after=%30"));
  rejects(BASE.replace("after=0", "after=0#fragment"));
  rejects(BASE.replace("after=0", "after=0\r\nHost:example.com"));
  rejects(BASE.replace("after=0", "after="));
  rejects(BASE + "&");
  rejects(new String(new char[513]).replace('\0', 'x'));
  System.out.println("MotionQueryTest: " + assertions + " assertions passed (synthetic, no camera/network)");
 }
}
