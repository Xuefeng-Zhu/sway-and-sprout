# MoveNet reference parity — 2026-10-20

The native integration now follows the official Android crop/image path and can compare its input against the actual Support API. The bounded comparison is complete. The observations below do not establish overall model acceptance, natural-motion accuracy or Fire TV support.

## Pinned references and models

- [Android MoveNet.kt](https://github.com/tensorflow/examples/blob/bda6a8741864b7bc934345c47c25f8e17fd67bdc/lite/examples/pose_estimation/android/app/src/main/java/org/tensorflow/lite/examples/poseestimation/ml/MoveNet.kt): examples commit `bda6a8741864b7bc934345c47c25f8e17fd67bdc`,13,653bytes, SHA256 `bf2c97ccbe9d2abe154167c13b39749d38027fdfaf0a23e34b3480d602fc4ac8`. BodyPart.kt at the same commit confirms shoulders5/6, wrists9/10 and hips11/12. Its download.gradle selects **Lightning float16-v4**, a different artifact from the initial INT8 candidate.
- [Support image operations](https://github.com/tensorflow/tflite-support/tree/133228616ca14e1b64c03f6a0ea8610f41a60783/tensorflow_lite_support/java/src/java/org/tensorflow/lite/support/image): release0.4.4, commit `133228616ca14e1b64c03f6a0ea8610f41a60783`. Official `tensorflow-lite-support-api-0.4.4.aar`:85,482bytes, SHA256 `072481f7f3822074996a06afb1d784efd8287319b38e3e48572bb299079298e4`. The inspected0.3.0 sample operations have equivalent behavior after import/Javadoc changes. Only the selected Java image path is used; no duplicate legacy TensorFlow Lite API or ODML adapter is needed.
- [Official pose-classification notebook](https://github.com/tensorflow/tensorflow/blob/bd60a6fb8e40f5cdc59a03e109864e20455c4666/tensorflow/lite/g3doc/tutorials/pose_classification.ipynb): commit `bd60a6fb8e40f5cdc59a03e109864e20455c4666`,57,345bytes, SHA256 `06e4df615d114148a51a041bcd2026362d1afaca93cbad21de5333f98cc41bdf`. Its explicit three-pass sequence is used as a refinement strategy; its Raspberry Pi/OpenCV image sampler is not claimed as Android pixel parity.

| Lightning v4 artifact | Bytes | SHA256 |
| --- | ---: | --- |
| INT8 | 2,894,840 | `cd7cc22fa946e5d146a7b98d496853e1923e22828d3972d579973f27f91bb105` |
| Float16 | 4,758,512 | `0fac2226112d0371903ca86e3853cec24ef603a0b2f96f589b180f0ebdd135ab` |

The [asset lock](../android/native-video-assets.lock.json) pins official URLs, licenses, model bytes and frozen videos. Runtime remains LiteRT1.4.2 CPU/two threads; binaries/media remain local and ignored.

## Tensor and score contract

Both exact artifacts take raw **UINT8 RGB `[1,192,192,3]`**,0..255, and return **FLOAT32 `[1,1,17,3]`** as `(y,x,score)`. I/O quantization arrays are empty; the runtime scale0/zero-point0 is not an instruction to normalize or requantize outside the graph. INT32 tutorial input belongs to the SavedModel signature. Float16 describes internal weights, not a float image API. TensorImage ignores alpha and packs R,G,B bytes; Java signed byte storage preserves those eight-bit values.

The INT8 graph itself casts/scales pixels and internally quantizes output. Its final FLOAT32 values have already been dequantized from a shared INT8 scale approximately0.004096854/zero-point−128. Repeated score levels are expected. No additional output dequantization, sigmoid or score remapping is applied.

The sample uses raw joint scores and mean-of17 Person.score; the game retains its required-four minimum and **.65 event gate**. These are not established as equivalent to MediaPipe confidence or a calibrated probability. Official **.2 crop support** decides torso visibility/body extents, never gestures. Any model-specific event-gate proposal needs separate score/geometry/negative evidence.

## What parity establishes

The source first renders a floating crop rectangle into an integer-sized ARGB bitmap, then center-crops to the smaller dimension, uses `Bitmap.createScaledBitmap(...,true)` and packs RGB. This replaces the earlier direct192pixel integer letterbox. All17 restored points update the hip-centered ROI with official1.9/1.2 torso/body expansion and source fallback behavior. Crop state is worker-owned and reset at control epochs.

Two boundaries are checked separately:

1. [MoveNetReferenceImage](../android/app/src/debug/java/com/togethermove/tv/MoveNetReferenceImage.java) invokes the actual pinned Support API. On a **shared decoded/cropped bitmap and shared chosen ROI**, it independently performs center-crop, bilinear resize and RGB conversion. The candidate compares every input byte, then runs that reference buffer through the **same pinned interpreter** and compares all51 output floats. Checks sample the first3 frames, every30th frame and the final frame; image mode checks all3 refinement passes at those sampled frames. Report full byte-difference count/max delta and output max delta, not CRC equality alone. This does not independently verify MediaMetadataRetriever decoding, the shared floating-origin Canvas crop, ROI selection or a different inference runtime.
2. [MoveNetCrop](../android/app/src/main/java/com/togethermove/tv/MoveNetCrop.java) is a separate scalar port. [350 host assertions](../android/tests/com/togethermove/tv/MoveNetCropTest.java), derived from15 independently translated float32 reference cases, check regions, integer bitmap dimensions and inverse coordinates. These are model-free math tests, not Android image or landmark-accuracy evidence. Source quirks are retained: odd portrait initialization uses integer height/2, and float truncation can produce a456×455 bitmap whose source inverse still uses456 for X. Nonfinite/degenerate crop inputs additionally fail safely.

Completed saved INT8/FP16 sampled summaries report zero byte/max-byte differences and zero same-interpreter output delta. That establishes this declared sampled boundary only. They do not establish every-frame parity, independent crop correctness, reliable recognition or hardware readiness. Run records must bind model, APK and source hashes.

## Profiles and measured observations

`tracked` performs one recognition invocation per decoded frame and carries its ROI into the next frame, matching the Android video strategy. `image` resets to the full-image crop for each decoded frame, then performs3 invocations of that same bitmap, updating ROI between passes. Only the final pose advances gesture timing once at that frame's original timestamp. The three-pass policy is supported by the official pose-classification notebook; it is not a threshold fitted to these clips.

| Completed scoped observation | Clear rays | Near-face rays | Frontal rays |
| --- | ---: | ---: | ---: |
| INT8 tracked | 0 | 0 | Not established here |
| INT8 image/3-pass | 0 | 0 | Not established here |
| Float16 tracked | 0 | 0 | 0 |
| Float16 image/3-pass | 0 | 0 | **6; UI6 and ACK6** |

A same-APK confirmation (`native-reference-integration/float16-image-confirm`) also completed the frontal real30-second celebration, reload and unchanged participation; its full136-frame both-up control produced0 events. The tracked FP16 run completed all7 videos/1,680frames with0 events. These remain scoped observations: clear and near-face are unresolved, the positive is constructed held/cut/reflected, and zero negatives can reflect failed calibration. No backend promotion or gating change is justified.

Performance must count **all** recognition invocations: one per tracked frame versus three per image frame. Sampled parity adds one extra reference invocation per checked pass, plus Support preprocessing/comparison work. `modelInferencesPerFrame` describes recognition work only; `referenceParityChecks` accounts for the additional calls. Recognition preprocessing/inference timings sum all3 passes; `referenceMeanMs` reports extra parity work; whole native frame time includes sampled parity overhead. None is camera-to-render latency or Fire TV throughput. Include decoder, UI/renderer memory, lifecycle and sustained device costs separately.

## Reproduce the comparison

Follow the [native setup](NATIVE-VIDEO-VERIFICATION.md) to restore/build/install on the intended camera-disabled emulator. The runner requires an emulator serial and `ro.kernel.qemu=1`; it performs no boot/install or physical-device action.

```sh
node scripts/verify-native-video.mjs --adb /path/to/adb --adb-port 5038 --serial emulator-5556 --model int8 --refinement tracked --out verification-results/movenet-int8-tracked clear nearface
node scripts/verify-native-video.mjs --adb /path/to/adb --adb-port 5038 --serial emulator-5556 --model float16 --refinement image --completion true --out verification-results/movenet-float16-image clear nearface frontal right-negative both-up-negative
```

`--refinement image` selects3 passes; `tracked` selects1. `--completion true` additionally waits for the real UI timer/result and reload, checking saved participation, when six real model rays occur. No events/timer are injected. Failed known positives return exit1 after later cases run; uncertified clips remain observed-only.

No physical camera, natural/human acceptance, Fire OS/32-bit execution, Vega/UVC support or sustained TV performance is established. No push, deployment, spending or external upload is part of this milestone. Frozen expectations and existing event thresholds remain unchanged.

## Bounded Thunder comparison

The optional official Thunder float16-v4 pin is12,584,128bytes, SHA256 `41641538679ec79b07d4101e591dda47d098c09af29607674b2a40b8a3798dd3`. Its strict UINT8 RGB input is256×256; output remains FLOAT32 `[1,1,17,3]`. It uses the same297 builtin ops, without Custom/Flex. `--model thunder` is explicit; INT8 remains the native default and existing192-input paths remain distinct. No default Mac backend changed.

Tracked Thunder completed clear/near-face/frontal152frames each and produced0/6 each. Both-up completed136frames with0 events. The right-only negative processed only193/450frames before the actual30-second UI ended, so it fails complete-negative acceptance despite zero observed events. All requested runtime/model/input-size checks passed. Primary inference means were110.0–144.0ms and native frame means143.2–182.0ms on this ARM64 emulator. This candidate provides no demonstrated replacement benefit; no three-pass Thunder or device throughput claim is made.

The [structured record](verification/native-reference-20261020.json) preserves failures, coverage, parity counters, timings, APK/source bindings and prior lifecycle timing failure. The initial fixed800ms cleanup observation failed; a bounded5-second poll subsequently observed actual decoder/interpreter cleanup and all6 lifecycle assertions passed. The finalAPK then passed7 assertions including the added actual model-pin check.
