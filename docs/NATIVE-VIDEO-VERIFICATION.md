# Android native video verification — 2026-10-20

The debug APK now has an opt-in **in-process Android inference path**. It runs without a Mac Python sidecar. This is a diagnostic implementation, not accepted Fire TV motion recognition: the first full seven-video emulator run produced zero events on all three six-event controls. The default web/OpenCV path and optional Mac Full IMAGE baseline remain unchanged.

The user has no physical Fire TV. The provisional reference is Fire OS7 / API28 / `armeabi-v7a`; no user-owned device is assumed. Actual runtime evidence is from the already-installed Android TV API34 **ARM64** emulator on this Mac. ARMv7 library presence is statically verified in the APK, not executed on a 32-bit guest. Fire OS, UVC camera access, Vega and sustained real-device performance remain unverified.

## What executes on Android

`NativeVideoFactory` activates only in debug with the `nativeVideo=true` intent extra and one of seven whitelisted `nativeVideoCase` names. It cannot accept a path, URI or camera. Release has an inert factory, no inference libraries/model/videos and no INTERNET or CAMERA permission. The normal debug route retains the existing fixed emulator-host proxy.

`NativeVideoAssets` verifies model/video bytes and SHA256, expected frame count/duration, runtime version, config schema and tensor shape/type. LiteRT core and API **1.4.2** are explicitly restored Google AARs; the Gradle debug preflight rejects a changed AAR. Their dependency closure has no Play Services requirement. The APK includes `armeabi-v7a/libtensorflowlite_jni.so` as ELF32 ARM, plus the ARM64 library actually exercised by this emulator.

`MediaMetadataRetriever.getFrameAtIndex` decodes every indexed frame from an uncompressed bundled MP4 asset (API28 minimum for this mode). `NativeMoveNet` uses the official pinned Lightning INT8 v4: UINT8 RGB `[1,192,192,3]` in, FLOAT32 `[1,1,17,3]` `(y,x,score)` out. A single CPU interpreter uses two threads. The transform is full-frame, aspect-preserving floor resize, integer-centered black padding and Android Canvas bilinear sampling; its actual per-axis scale/offset invert landmarks to source coordinates. There is no mirror, signed-int8 conversion, float normalization or claim of exact TensorFlow resize-with-pad parity. This baseline does not implement adaptive torso cropping.

Shoulders5/6 and wrists9/10 feed the ported gesture rules: confidence.65, neutral300ms, expected-arm hold350ms, cooldown500ms, maximum frame gap300ms, raise margin.30 and down margin.20 shoulder-width. MoveNet scores are keypoint scores, not MediaPipe visibility/presence or a measured person-global probability. SinglePose cannot establish person count; these clips are assumed to contain one intended person. Thresholds and annotations were not adjusted for this model.

`NativeVideoReplay` serves bounded same-origin semantic events and metadata-only preview directly to the WebView; it opens no socket. Source remains `video`, runtime identifies `litert` and its pinned model, and the existing JS reducer/ACK/UI path remains authoritative. File timestamps drive gesture dwell; monotonic wall time drives leases and event age. Pause/revision/epoch changes invalidate partial work. A separate host pause gate prevents a delayed request from restarting a paused Activity. One serialized worker owns native resources, including cleanup across Activity recreation.

Frames and transformed tensors remain in memory, then are recycled. No frame/preview export, screenshot or physical camera is used. Only bounded scalar diagnostics are logged, including input/output CRCs, means, landmark scores, confidence/geometry rejection counts and timings. CRCs diagnose changed input/output; they do not establish pixel parity. Instrumentation adds preprocessing work, so diagnostic timing is labelled separately.

## Actual result

All seven final-APK replays completed all **1,680 frames**. The clear, frontal and near-face expected-six controls produced **0 events / 0 rays / ACK0** each. The two negatives also produced0, and the two uncertified continuous clips produced0 (observations only). The runtime/source labels, HTTP-to-WebView integration, no-camera calls and unchanged stored progress were verified for all seven. Six-ray native-model scoring was not demonstrated; the separate generated-packet tests verify that UI/ACK boundary.

Every frame failed the unchanged four-joint .65 confidence gate. Clear/frontal/near-face input/output fingerprints had113/123/118 distinct values, with no blank inputs, invalid mappings or invalid native scores. This excludes fixed/black input and stale output for these runs; it does not prove pixel parity with the official preprocessing. Raw left/right/neutral geometry was also weak. Negative zero counts are therefore weak rejection evidence, because no confidence-admitted neutral calibration occurred.

With scalar instrumentation enabled, whole-interpreter mean time ranged **10.65–16.97ms** across the seven clips; native decode/preprocess/inference frame means ranged **20.45–33.11ms**. These exclude event polling, UI and intentional dwell, and are emulator/Mac measurements. App-process PSS snapshots ranged103,226–114,844KiB. A separate `dumpsys meminfo` snapshot reported PSS103,889KiB, RSS213,420KiB and swap PSS302KiB. Separate WebView renderer/decoder service memory and sustained peaks were not attributed; no complete TV RAM budget or hardware throughput guarantee follows.

Fresh required checks: **65 JavaScript tests**, production build, **381 pure Java synthetic assertions**,8 preparation boundary checks,2 fake-ADB physical-device-guard checks, and **5 actual emulator lifecycle assertions**. Debug and release APKs build offline. The saved portable runner was exercised on clear+both-up: it completed both, exited1 for the failed positive, and recorded the negative's matching zero count without claiming robust tracking.

## Boundaries of verification

The three positive clips contain disclosed held frames, cuts and reflected apparent-left poses; they do not certify natural alternating movement. Two negative clips are independently annotated controls. The two continuous clips have no complete independently certified expected sequence and remain `expectationKnown:false`; an empty placeholder array is never a negative expectation.

`acceptedFrames` in transport statistics means decoded frames committed to the current control epoch, not confidence-admitted pose frames. `poseDiagnostics.nativeConfidenceAcceptedFrames` reports that separate gate. A completed file or valid runtime does not mean recognition passed. Generated six-event JS tests and pure Java pose tests establish scoring/rule behavior independently from actual model results.

The detailed scalar record is [native-video-20261020.json](verification/native-video-20261020.json). It binds APKs, sources, runs and expectations. Real emulator lifecycle checks cover background pause, no advance on foreground without explicit resume, resumption and successful decoder/interpreter release. They do not substitute for extended device testing.

## Reproduce locally

Restore the seven source fixtures using their existing opt-in repository recipes. Models/media and generated debug assets remain ignored. Then explicitly copy already-audited artifacts or request the pinned official downloads:

```sh
python3 scripts/prepare-native-video.py --artifact-dir /path/to/audited-artifacts
# Alternative explicit network opt-in: python3 scripts/prepare-native-video.py --download
python3 scripts/prepare-native-video.py --check
npm test
npm run build
npm run android:sync
cd android
./gradlew --offline :app:assembleDebug :app:assembleRelease
```

For the already-installed Mac cache, `sh scripts/build-android-cached-mac.sh` is the explicit offline override. With an existing camera-disabled emulator and the debug APK installed, run:

```sh
node scripts/verify-native-video.mjs --adb /path/to/adb --adb-port 5038 --serial emulator-5556
node scripts/verify-native-lifecycle.mjs --adb /path/to/adb --adb-port 5038 --serial emulator-5556
```

Outputs default to ignored `verification-results/native-video`. Case names may be provided to select controls. A failed known positive returns exit1 after the remaining cases run; unknown expectations stay observed-only. Local debug installation uses `adb -P 5038 -s emulator-5556 install -r android/app/build/outputs/apk/debug/app-debug.apk`, only after verifying the intended emulator. No physical-device installation was done.

The existing exported AGP8.7.3/Gradle8.9 pins are preserved. This Mac's recorded build instead explicitly uses its cached Gradle8.13/AGP8.13.2/JDK17/SDK35, one worker, a768MB Gradle heap, no downloads and its existing debug keystore. No SDK installation, legal-term acceptance or key generation occurred. The debug APK is local only and contains exact third-party credits/notices.

The emulator was launched read-only with snapshots disabled, two cores,1536MB RAM, software graphics and **both cameras `none`**. Only one emulator was used. The Mac sidecar ports4173/8765 were not listening. External network was denied by the OS sandbox while localhost/Unix IPC remained available. The validation runner requires an emulator serial and `ro.kernel.qemu=1`; it never installs an APK, starts an emulator or operates a physical device.

The emulator, task-owned ADB server and scalar-log collection were stopped after verification; ports4173,8765,5038,5556 and5557 have no listener.

## Remaining implementation and acceptance

Do not promote this Lightning/full-frame candidate: positive recognition currently fails. Next work should compare its preprocessing/raw keypoints with the official reference, assess the official crop/loss-recovery strategy without fixture-derived tuning, and use independently annotated natural positive and negative controls for any cross-model confidence calibration. A useful fix must recover actual native positive scoring while preserving negatives; transport-only success is insufficient.

Actual TV capture still needs a proven third-party frame API on a selected supported platform. Fire OS does not imply universal Camera2/UVC support, and Cube video calling is not evidence for this app. Vega requires a separate capture/runtime/UI port rather than reusing APK/AAR. Hardware is unavailable, so real Fire OS loading,32-bit execution, webcam behavior and at least20-minute latency/memory/UI acceptance cannot be completed here. There is no pending permission request. No push, production deployment or upload occurred.
