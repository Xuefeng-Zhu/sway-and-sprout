# Native confidence pilot — 2026-10-21

The Mac resumed successfully from `0c29ec6` with all eight existing calibration debug files preserved. Independent calibration found **no qualifying MoveNet score threshold**. The native and frontend0.65 gates, model, crop, gesture geometry and timing remain unchanged. There is no new permission blocker.

The frozen reviewed pilot contains53 person examples for calibration (47 with all four joints visible, six occlusion challenges),35 independent-image person examples for verification (32 visible, three occluded), and20 separately reviewed backgrounds per split. All88 original person rows/labels/splits are identical. Eight unacceptable backgrounds were replaced before inference after two independent model-blind AI pixel reviews. Human joint labels are official COCO annotations; AI background/video reviews are not new human ground truth. Image/annotation/hash disjointness and a bounded pHash/Flickr-ID screen do not certify physical-person disjointness. The former source-person separation record is withdrawn.

## Actual native results

The debug calibration Activity decodes the exact frozen JPEGs without density scaling and runs the unchanged native Lightning FP16 IMAGE three-pass engine, resetting for each image. No scoring, camera, Mac inference, reference inference, upload or saved-progress mutation occurs. Both batches completed (73/73 and55/55) with resources closed. Float outputs are serialized as doubles to retain native float boundary values.

A pose passes localization only if **all four source-pixel joint errors are <=0.10 of human-labelled shoulder span**. This is a strict spatial metric, not gesture-event accuracy or a probability interpretation of raw MoveNet scores.

| Fixed threshold | Visible admitted /47 | Incorrect localization among admitted | Background admitted /20 |
| --- | ---: | ---: | ---: |
|0.20|44|34|2|
|0.35|27|18|0|
|0.50|10|5|0|
|0.65 baseline|1|1|0|
|0.70|0|0|0|

The predeclared18-threshold grid yielded no gate meeting coverage,5% empirical localization error, correct gain and background/occlusion safeguards. Only10/47 calibration examples meet the tight all-four point criterion at any score; a gate admitting>=20 cannot satisfy5% error. The single baseline admission misses only the left shoulder bound (11.11px versus9.51px allowed) while correctly classifying neutral. Independent calibration-only inspection found no global index, mirror or XY mapping anomaly; robust human geometry classes match31/32. This distinction prevents describing point rejection as31 incorrect gestures.

The `None` decision was frozen **before** running the55 heldout samples (selection SHA256 `dd369b8f1a208835f252b669ba8d56f6b00f56a65593eb9d42080e55cf3d372f`). Heldout evaluates baseline only:0/32 visible examples,0/3 occluded and0/20 backgrounds admitted. No threshold was selected from verification data. Rejecting everything has inadequate positive coverage.0/20 background admissions has a one-sided95% upper bound13.91%; it does not certify low production false-event risk. Static pose admission is separate from temporal false gesture events.

## Actual app pipeline and natural footage

New public-domain DVIDS679690 supplies a separately recorded contiguous neutral→anatomical-left raise. Its83 original-speed frames were independently AI annotated before inference; no cut/splice/reflection/hold duplication/retiming was added. The one expected left event has a frozen2050–2733.334ms window. In the app's actual native inference→gesture→WebView→scoring/ACK pipeline:

| Input | Complete frames | Events / rays / ACK | Result |
| --- | ---: | ---: | --- |
| New left-natural |83/83|0/0/0|Positive fails; expected1 within frozen window|
| Right-short continuous prefix |156/156|0/0/0|Wrong-side negative passes|
| Both-up |136/136|0/0/0|Negative passes|

Primary inference means are58.6–67.5ms per frame (sum of three calls); diagnostic native frame means96.9–106.8ms, P95 163.2–178.9ms. These exclude polling/rendering and are emulator results, not camera-to-render or Fire TV performance. ProcessPSS snapshots151034–153564KiB omit renderer/system sustained peaks.

All report `video`, no camera calls, unchanged participation and no page errors. The short right prefix supplements the previously incomplete450-frame negative; it does not erase that performance failure or establish right-positive recognition. No natural alternating-six or live-person success is claimed. Existing frontal6/UI6/ACK6, timer/reload and lifecycle evidence is preserved; unchanged engine/gate sources remain hash-bound to that prior evidence.

## Reproduce and limits

`sidecar/fixtures/confidence-calibration/` retains immutable manifests, human labels, model-blind review records, public-source credits and opt-in reconstruction recipes. Media remain ignored. `scripts/confidence-calibration/` contains the frozen analyzer and its10 synthetic contract tests. Verify hashes, prepare the exact dataset with `scripts/prepare-native-calibration.py`, build offline using the existing Mac toolchain, and use `scripts/verify-native-calibration.mjs` on an explicitly selected emulator. The analyzer `select` command freezes a decision last; `heldout` verifies the script/input/split hashes before opening predictions and cannot refit. See accompanying usage/protocol files. Do not infer a directory of unused images.

Fresh validation:65 JS tests, production build,10 analyzer tests,14 offline preparation/CLI checks and debug/release builds passed. Release has no calibration Activity/assets or native runtime libraries. Source/APK/input/result hashes and scoped counts are in [structured evidence](verification/native-confidence-20261021.json). Full scalar traces stay in the local dated workspace and are not uploaded.

One camera-disabled Android TV API34 ARM64 emulator is the only execution target. Fire OS7/API28/armeabi-v7a is provisional; ELF32 binary presence is static evidence only. There is no Fire TV hardware, so FireOS loading,32-bit execution, UVC capture, Vega and sustained device memory/latency are unresolved. No push, deployment, upload, spending or credential changes occurred.

The sole emulator and isolated ADB5038 were stopped; emulator/WebView-forwarding ports are closed. At the prior no-expansion checkpoint, optional native MediaPipe audit/artifact/adapter drafts stay in the dated workspace only. No MediaPipe APK build, graph initialization, inference or canonical integration occurred. Stock telemetry initialization and a deterministic official-dummy factory replacement were audited; this is preparation, not an accepted recognition backend.

The subsequent conditional MediaPipe continuation is recorded in [the eligibility decision](NATIVE-MEDIAPIPE-ELIGIBILITY.md): stock1.1.1 mandatory remote statistics triggers the explicit pause condition, so no candidate build or three-video run has occurred.
