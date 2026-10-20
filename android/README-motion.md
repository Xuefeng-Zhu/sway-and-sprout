# Local motion debug wrapper

This prototype keeps the exported release application identity (`com.togethermove.tv`).
The debug application remains separate: `com.togethermove.tv.motion`. New builds use the visible label **Sway & Sprout Motion**; preserved TogetherMove Motion APKs retain their original label.
Its launch activity is `com.togethermove.tv.MainActivity` (the namespace does not acquire the suffix).

An opt-in debug-only native recorded-video mode is now available: see [actual native results](../docs/NATIVE-VIDEO-VERIFICATION.md). It runs LiteRT inside Android with no Mac service. Its three positive controls currently fail0/6, so it is a diagnostic harness rather than accepted recognition. Launch only on an intended emulator with `--ez nativeVideo true --es nativeVideoCase clear`; seven whitelisted case names are supported. The WebView clearly labels the replay and does not save participation. Release has no native model/runtime/media.

The default debug WebView remains on `https://app.togethermove.local`. Only its exact
`GET /motion/events` route is proxied by native Java to the fixed
`http://10.0.2.2:8765/motion/events` endpoint. `10.0.2.2` is the Android Emulator's
alias for this Mac's loopback; this is not a physical Fire TV connection scheme.
The sidecar must listen on the Mac at `127.0.0.1:8765`.

The query requires exactly six fields: `clientId` and `roundId` (canonical UUID
strings), `revision` and `after` (nonnegative JavaScript-safe integers), `active`
(`0` or `1`) and `mode` (`seated` or `standing`). No arbitrary destination or
additional fields are accepted. Native requests do not follow redirects, use
750 ms connect/read timeouts, allow one request at a time, and accept at most 32 KiB of JSON. The response is
not cached. No camera frames cross this interface.

Only the debug source set requests `INTERNET` and permits cleartext for the
single host `10.0.2.2`. The default network policy rejects cleartext everywhere
else, release has no network permission, and the release proxy is disabled.
The WebView does not enable mixed content, file access, external navigation or
a JavaScript-to-native object. Android does not request a camera permission.

## Build

Build the web app and synchronize its assets before packaging:

```sh
python3 scripts/prepare-native-video.py --artifact-dir /path/to/audited-artifacts
python3 scripts/prepare-native-video.py --check
npm run build
npm run android:sync
cd android
./gradlew assembleDebug
```

The original exported build pins AGP 8.7.3 and Gradle 8.9. They were not installed
on the test Mac. The evidence folder records an explicit local init-script
override using the already-installed AGP 8.13.2 / Gradle 8.13 / JDK 17 / SDK 35,
with offline dependency resolution. The exported version pins are preserved.
No new SDK, Gradle distribution, legal terms or debug signing key are needed
for that recorded build; it uses an existing local debug keystore.

From the canonical repository root, the recorded cached build is runnable as:

```sh
sh scripts/build-android-cached-mac.sh
```

## Host-side query tests

These tests require a JDK; they do not contact a device, camera or server:

```sh
mkdir -p build/query-tests
javac -d build/query-tests app/src/main/java/com/togethermove/tv/MotionQuery.java tests/com/togethermove/tv/MotionQueryTest.java
java -cp build/query-tests com.togethermove.tv.MotionQueryTest
```

Passing these synthetic parser tests does not establish camera recognition,
Android runtime behavior, Fire OS compatibility or contest eligibility.

## Launcher branding

New builds display **Sway & Sprout** (release) or **Sway & Sprout Motion** (debug). Internal package names, the WebView origin, and native JavaScript bridges keep their TogetherMove identifiers for compatibility. Existing APKs and dated verification records are unchanged.

The editable launcher banner is `android/branding/launcher-banner.svg`. Rasterize it at the required 320×180 size, retaining the existing Android resource filename:

```sh
rsvg-convert --width 320 --height 180 --output android/app/src/main/res/drawable-nodpi/banner.png android/branding/launcher-banner.svg
```

Web assets must still be rebuilt and synced, and an APK rebuilt, before these display changes appear in an installed native app.
