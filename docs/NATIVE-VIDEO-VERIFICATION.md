# Android native video verification — 2026-10-20

This dated report preserves the baseline fixtures, model comparisons and original
30-second UI results. The later [independent natural evaluation](INDEPENDENT-NATURAL-EVALUATION-20261021.md)
records additional clips and the explicit 120-second diagnostic replay rerun;
its completion results do not replace the failures below. Use
[Getting started](GETTING-STARTED.md) for current web setup and the
[Android guide](../android/README-motion.md) for native source entry points.

Official crop/preprocessing corrections restored one actual native positive: **Lightning FP16 with three same-image passes reaches six frontal events, six UI rays and ACK6**, then passes the real30-second celebration, reload and unchanged participation checks. Clear and near-face remain0/6; overall recognition is not accepted. The default web/OpenCV backend and optional Mac Full IMAGE baseline remain unchanged.

The user has no physical Fire TV. The provisional reference is Fire OS7/API28/`armeabi-v7a`; actual execution is Android TV API34 ARM64 on the existing Mac emulator. ARMv7 ELF32 presence is statically checked, not executed. Fire OS/UVC/Vega and sustained device performance remain unverified.

## Android implementation

The debug-only intent `nativeVideo=true` selects one of seven fixed local videos, an explicit pinned model (`int8`, `float16`, `thunder`) and `nativeRefinement=image|tracked`. No path, URI, camera or network video is accepted. Release has an inert factory, no model/runtime/media, INTERNET or CAMERA permission. Model binaries, licensed videos, generated assets and logs remain ignored.

`MediaMetadataRetriever.getFrameAtIndex` decodes indexed bundled MP4 frames, requiringAPI28 for this mode. LiteRT1.4.2 CPU uses two threads, without Play Services or a Mac inference sidecar. Model/video byte counts and SHA256 are checked, as are exact tensor types/shapes and unquantized I/O metadata. Lightning uses UINT8 RGB192×192; Thunder uses256×256. FLOAT32 outputs are17 `(y,x,score)` joints. No external normalization, extra dequantization or confidence remapping is applied.

The official Android hip-centered torso/body ROI is ported with350 independent host math assertions. Actual Support API comparisons independently check sampled center-crop/resize/RGB tensor bytes on a shared crop bitmap, followed by all51 floats through the same interpreter. All observed byte and output differences were0. This sampled boundary does not independently verify decoding, the shared Canvas crop or another runtime. See [exact source pins, semantics and scope](MOVENET-REFERENCE-PARITY.md).

`tracked` uses one pose call and carries crop state between frames. `image` resets each fileframe and performs three same-image crop refinements; only the final pose advances the classifier once. Sampled parity adds one reference call per checked pass. All four required native joint scores must still meet.65; .2 is only official crop-support eligibility. Neutral300ms, hold350ms, cooldown500ms, gap300ms and .30/.20 shoulder-width margins are unchanged. MoveNet scores are uncalibrated keypoint scores, not MediaPipe visibility or global person probability. SinglePose cannot verify person count.

The serialized native worker owns decoder, interpreter and crop state. Revision/epoch/pause changes discard in-flight work and reset tracking. Same-origin WebView interception transports semantic events and metadata-only preview without opening a socket; source stays `video`. The existing JS reducer/ACK/UI owns scoring and preserves saved participation. File time drives gesture dwell, wall time drives leases/event age and the real30-second round. Frames/tensors remain in memory and are recycled; scalar diagnostics contain no pixel export.

## Measured results

| Model/profile | Clear | Near-face | Frontal | Negative coverage |
| --- | ---: | ---: | ---: | --- |
| Initial INT8/full-frame |0/6|0/6|0/6|Both complete, but all frames confidence rejected|
| INT8 official tracked/image |0/6|0/6|Not run in these two probes|Not established|
| Lightning FP16/image3-pass |0/6|0/6|**6/6, UI6, ACK6**|Both-up136/136 zero; right-only218/450 partial|
| Lightning FP16/tracked1-pass |0/6|0/6|0/6|Both complete, zero; all7 files/1680frames complete|
| Thunder FP16/tracked1-pass |0/6|0/6|0/6|Both-up136/136 zero; right-only193/450 partial|

The three positive clips disclose held frames/cuts/reflection; none certifies natural six-alternating motion. The two continuous inputs remain observed-only, not zero-event negatives. Partial negatives fail full acceptance. A valid runtime or completed file is not successful recognition; `acceptedFrames` means frames committed to the current epoch, while `nativeConfidenceAcceptedFrames` reports the separate pose gate.

Offline scalar replay matches all logged canonical classifier states/events. Lower-gate counterfactuals are not model calibration or UI results. Near-face still produces only2/6 under ideal confidence in image mode,0/6 in tracked mode: geometry breaks the holds. Independent AI joint boxes, frozen before reviewing predictions, allow both passing and failing .30 geometry; they do not establish exact human ground truth or justify changing expectations/margins.

| Profile | Primary inference mean across cases | Native diagnostic frame mean |
| --- | ---: | ---: |
| Lightning FP16 tracked |22.4–30.4ms|38.3–54.5ms|
| Lightning FP16 image |63.5–84.1ms, sum of3|93.6–133.8ms|
| Thunder FP16 tracked |110.0–144.0ms|143.2–182.0ms|

Times are emulator/Mac measurements. Primary inference excludes extra sampled reference calls; native frame time includes them and decode/preprocessing, but excludes event polling/rendering and intentional dwell. They are not camera-to-render or Fire TV results. ProcessPSS snapshots omit separate renderer/service memory and sustained peaks; no complete TV resource budget follows. No candidate is promoted.

## Reproduce and evidence

Use the existing explicit fixture recipes, then restore audited artifacts with `python3 scripts/prepare-native-video.py --artifact-dir /path/to/audited-artifacts` (offline default), or explicit `--download`. `--check` verifies six artifacts, three models, seven videos and21 configs without mutation. Existing14 INT8/FP16 config bytes and all frozen expectations are preserved. `sh scripts/build-android-cached-mac.sh` uses this Mac's installed JDK17/Gradle8.13/AGP8.13.2/SDK35 offline, one worker/768MB heap and the existing debug key. Exported AGP8.7.3/Gradle8.9 pins are unchanged.

With the debug APK installed on an intended camera-disabled emulator:

```sh
node scripts/verify-native-video.mjs --adb /path/to/adb --adb-port 5038 --serial emulator-5556 --model float16 --refinement image --completion true --out verification-results/fp16-image frontal both-up-negative
node scripts/verify-native-lifecycle.mjs --adb /path/to/adb --adb-port 5038 --serial emulator-5556 --model float16 --refinement tracked
```

The runner rejects physical serials and checks `ro.kernel.qemu=1`; it does not boot/install. Failed known positives or incomplete negatives return1 after remaining cases. Completion waits for the actual timer and preserves the original six-ray observation, then checks video label, no camera calls, unchanged storage and reload. No timer/event is injected.

Fresh checks include65 JS tests, production build,350 crop plus381 pose host assertions,9 optional-model preparation boundaries, offline debug/release APK builds, real six-ray/completion/reload preservation and7 actual emulator identity/lifecycle assertions. An initial fixed800ms cleanup check failed; the bounded5-second recheck observed actual cleanup. Both records are retained.

[Structured current evidence](verification/native-reference-20261020.json) binds scalar results, APK/source hashes, frozen inputs and diagnostic analyses. [The initial full-frame report](NATIVE-FULLFRAME-BASELINE.md) and its JSON remain historical rejected baseline evidence.

## Remaining acceptance

No independent natural six-alternation positive or calibrated MoveNet event-score gate exists. The new public-domain DVIDS699177 candidate has three visible people and only one complete neutral→left→neutral cycle; it is an untested partial source, not accepted six-event footage. Next obtain precise independent joint/gesture annotations on separate clear-margin natural positives and negatives before proposing any model-specific gate. Keep the .65 baseline and rejected runs.

Actual TV capture requires a proven third-party frame API; Cube calling support does not prove general Camera2/UVC access. Without hardware, FireOS loading,32-bit execution, capture and sustained20-minute latency/memory/UI acceptance cannot be certified. Vega needs a separate port. There is no permission denial or pending approval. Camera remained off, one emulator only, external networking denied during runtime, and no push, deployment, spending or upload occurred.
