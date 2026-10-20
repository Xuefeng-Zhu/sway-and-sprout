# Portable Fire OS baseline audit — 2026-10-20

The user has **no physical Fire TV hardware**. Fire OS 7 / API28 / `armeabi-v7a` is an explicit provisional engineering reference. It is not the user's device or a verified deployment target. The installed Android TV API34 ARM64 emulator can verify Android integration; it cannot certify Fire OS, 32-bit performance, webcam access or Vega support. No model/screenshot request remains pending.

This document records the packaging snapshot at `ca84fb1` and the completed static artifact audit. Native implementation, APK builds and emulator runs must carry separate evidence; this audit claims none of those outcomes. The [structured record](verification/candidate-portability-20261020.json) binds the local source reports and exact pins.

## Packaging gap at the audited baseline

The existing APK is a Java WebView host for bundled Vite assets, Android package `com.togethermove.tv`, debug suffix `.motion`, compile/target SDK35 and minimum SDK25. Its D-pad and pause/resume transport are implemented. There is no Camera2/UVC capture, camera permission, native ML dependency, model or Vega project at the audited baseline.

`MotionProxy.java` relays debug JSON to `http://10.0.2.2:8765/motion/events`; this is an Android Emulator host alias. Release disables that proxy and has no INTERNET permission. The Mac Python OpenCV/MediaPipe process is a development harness, not on-TV inference. A portable path must perform decode/capture, preprocessing, model invocation and gesture timing in the Android process and reach the existing JS scoring/UI without a Mac inference fallback. LiteRT packets need an honest engine identity, rather than a fabricated OpenCV version.

The Mac already has JDK17, cached Gradle/AGP, Android SDK and an installed Android TV API34 ARM64 AVD. Use cached tools and at most one emulator, with its virtual cameras disabled; no new SDK/license acceptance or Docker is needed for the bounded Android check. These installed-tool observations are distinct from a completed build or emulator run.

## Audited runtime and model

Bundle both official `com.google.ai.edge.litert:litert:1.4.2` and `litert-api:1.4.2` artifacts. The core POM pins the API artifact; the API POM declares no further dependency. Both manifests require API21. No Play Services dependency is declared by this closure.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| [LiteRT core 1.4.2](https://dl.google.com/dl/android/maven2/com/google/ai/edge/litert/litert/1.4.2/litert-1.4.2.aar) | 8,305,790 | `9b02cdf9db0a698b341b59e75c54ab8221d6304577cc43830d01024caf1fca74` |
| [LiteRT API 1.4.2](https://dl.google.com/dl/android/maven2/com/google/ai/edge/litert/litert-api/1.4.2/litert-api-1.4.2.aar) | 23,589 | `66c2ba8086bd5cbf89bec2bd81c3de6c1a852312829cd55bc30c9dd26ffa357c` |
| [MoveNet SinglePose Lightning INT8 v4](https://tfhub.dev/google/lite-model/movenet/singlepose/lightning/tflite/int8/4?lite-format=tflite) | 2,894,840 | `cd7cc22fa946e5d146a7b98d496853e1923e22828d3972d579973f27f91bb105` |

The actual core AAR contains `jni/armeabi-v7a/libtensorflowlite_jni.so`: **ELF32 ARM**, 2,641,764 bytes, SHA256 `1ef7f586c996fb95c944c3e25555d121f01874153b330d5b26503f369fd54d0a`. ARM64 and x86 variants are also present. The inspected JNI DT_NEEDED entries are `libm.so`, `libdl.so`, `liblog.so` and `libc.so`; no separate C++ runtime is declared. This proves an ARMv7 payload exists, not that it loads on Fire OS7.

Both AARs include Apache2 license files. The [Google MoveNet model card](https://storage.googleapis.com/movenet/MoveNet.SinglePose%20Model%20Card.pdf) declares Apache2. Anonymous official downloads succeeded without accepting new explicit terms. Keep licenses/notices and explicit restoration instructions; model binaries and licensed clips remain ignored and local.

Static FlatBuffer inspection of the exact model establishes:

- Input **UINT8 `[1,192,192,3]`**, RGB bytes 0–255; output **FLOAT32 `[1,1,17,3]`** as normalized `(y,x,score)`.
- Empty input/output quantization arrays; 215 internal INT8 tensors do not make the input signed INT8.
- 157 operators and 19 builtin opcode entries; no Custom/Flex operator.
- Anatomical shoulder indices 5/6 and wrist indices 9/10. Mirrored preview must not swap recognition sides.

The baseline preprocessing is aspect-preserving RGB resize with zero padding, retaining actual integer dimensions/offsets and inverse mapping into original-frame coordinates. Exact TensorFlow resize/pad arithmetic parity is a separate check; do not claim it from visual similarity. No mean subtraction or division by255 applies. MoveNet scores are not MediaPipe visibility/presence, so unchanged .65 gates may reject useful points; report raw geometry and confidence separately.

## Resource and acceptance limits

Known file/buffer sizes are small enough to justify a bounded candidate, not a RAM guarantee: model 2.76 MiB, ARMv7 JNI 2.52 MiB, input buffer110,592 bytes and output204 bytes. One 640×480 ARGB bitmap is1,228,800 bytes. Decoder surfaces, tensor arena, native/Java heaps, WebView and rendering remain unmeasured. Keep bounded buffers, stop inference on pause, release native resources and report decoded/processed/dropped counts. Do not infer device PSS from APK size.

A useful Android test must load the pinned runtime/model and process actual frozen-video frames through native preprocessing, gesture timing, event transport and UI scoring, with the Mac sidecar stopped. Report misses and negative-control failures honestly; generated semantic packets and pure Java tests establish different boundaries. A 350 ms gesture hold is intentional dwell, separate from inference and frame-to-render latency.

Amazon's [player](https://developer.amazon.com/docs/device-specs/device-specifications-fire-tv-streaming-media-player.html) and [Cube](https://developer.amazon.com/docs/device-specs/device-specifications-fire-tv-cube.html) tables distinguish CPU architecture from supported **application ABI**. ARM64 CPU branding does not establish ARM64 app support. API28/ARMv7 remains a provisional reference until a real target is available. Current minSDK25 also excludes older API22/Fire OS5 hosts.

Vega is a separate unresolved port. [Amazon's native-library guidance](https://www.developer.amazon.com/docs/vega-api/0.24/porting-libraries) does not make Android APK/AAR reusable as-is. Supported native ABI/runtime, C++/TurboModule integration, UI packaging and a real frame-capture API need separate work. This route makes no Vega claim.

Physical acceptance remains unavailable because there is no Fire TV hardware: loading/execution on Fire OS, actual webcam permission/frame delivery, and sustained latency/memory/UI behavior. Cube video-calling support does not prove generic third-party Camera2/UVC access or Stick compatibility. Future acceptance must run capture, inference and UI on the TV with the Mac sidecar **off**, including natural left/right and negative controls plus at least20 minutes of resource and lifecycle measurements. No physical-camera capture is authorized or performed by this audit.
