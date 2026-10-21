# Existing Python Full natural-motion benefit — 2026-10-21

**Do not proceed with a native Full port on this round’s evidence.** Full improves confidence-admitted left-pose coverage, but the actual event violates the frozen timing window; natural reliability is not accepted. Preserve the optional Mac diagnostic backend. This does not reject its already demonstrated near-face constructed-fixture benefit.

The strategy explicitly paused Android source builds/Bazel/tool installation. Only the existing pinned Python backend ran: MediaPipe1.1.1 / OpenCV5.0.0 / NumPy2.5.4, Full task SHA256 `4eaa5eb7…cec4ad`, CPU IMAGE, up to two poses, unchanged0.65 admissions, neutral300ms, hold350ms, cooldown500ms, gap300ms and .30/.20 shoulder-width margins. No confidence calibration or annotations were changed. MoveNet keypoint scores and Full min(visibility,presence) are different semantics; their numeric values are not correctness probabilities or directly calibrated equivalents.

## Reuse and actual results

Existing exact-file Full results were checked first. Both-up already had a complete136-frame result and was reused. No exact left83/right156 result existed, so only those two were inferred. All input, expectation/model/source hashes were verified; original files were unchanged afterward.

| Fixed clip | Frames | Events / current JS score / ACK | Timed acceptance | Median adapter inference | Processing time |
| --- | ---: | ---: | --- | ---: | ---: |
| New natural left |83/83|1/1/1|**Fail: early event**|23.241ms|2.292s|
| Right-short wrong-side negative |156/156|0/0/0|Pass|23.353ms|3.831s|
| Both-up negative, reused |136/136|0/0/0|Historical pass|23.178ms|3.283s|

Left emits at1633.333ms (frame49/source334),416.667ms before the fixed2050–2733.334ms window. It lies in the blind annotation’s uncertain transition32–50. Thus one timing violation and zero events inside the allowed window are established; a physically false gesture in that uncertain transition is not established. The window was not widened or relabeled to pass. Both negative controls have zero events; this selected two-clip observation is not a production false-positive-rate estimate.

The new executions use actual file decoding, the unchanged canonical Full adapter/classifier/service, in-memory previews, and the current real JavaScript reducer/ACK logic. They are not mocked semantic events. No browser rendering, actual30-second UI round, Android inference or FireTV execution was performed. Historical both-up evidence does not revalidate the current frontend.

## Keypoint evidence and what improved

Independent scalar review of the same certified windows found:

| Gesture window | Full geometry / admitted | Native MoveNet geometry / admitted |
| --- | ---: | ---: |
| Left neutral0–31 |32/32 /9/32|32/32 /4/32|
| Left raised51–82 |32/32 /32/32|32/32 /1/32|
| Right raised136–151 |9/16 /6/16|16/16 /1/16|

Full’s accepted left span is1033.333ms, but its certified-neutral accepted span is266.667ms, short of300ms. It arms atframe32 using predicted-neutral frames23–34, starts the raised hold at38, and emits at49 after366.667ms. Full’s accepted right span is only66.733ms (geometry-only233.567ms), below350ms. Raw left geometry already matches for both models; the demonstrated left advantage concerns admitted continuity, not proven lower point-location error. No independent joint-coordinate ground truth exists for these natural windows. Decoders/platforms also differ, so exact pixel/runtime parity is not asserted.

New traces preserve all four joint coordinates and min(visibility,presence) values. Separate raw visibility and presence were not intercepted; the earlier plan’s wording overstates that field coverage. Historical both-up has categorical gates and window counts, but no complete coordinate trace; it was not rerun just to reconstruct missing diagnostics.

A recording metadata error is retained transparently: right-short’s decoded input is1024×576, while the existing adapter resizes to640×360 before producing coordinates. Original reports are untouched. Separate `*.coordinate-audited.json` views identify inference-pixel units and explicitly derive source coordinates with1.6× scaling. Left remains640×480. Original observations, gates, events and timing are unchanged; no reinference or annotation edit occurred.

## Privacy, timing and decision

The installed Python native library has telemetry capability. It is not described as telemetry-disabled. The previously approved outer macOS deny-all network profile was active before SDK import, throughout inference and for child processes, with no unsandboxed fallback. A fresh SDK-free no-send UDP-connect check was denied with EPERM; the model process repeats that guard before imports. No camera, pixel export, upload, new dependency, credentials or permission change occurred. Both graphs closed; the process and scorer exited. No emulator or Android SDK was started.

Left graph initialization was1789.945ms; right initialization67.758ms. Case wall times including initialization were4.129s and3.905s. Adapter inference includes resize/RGB conversion, SDK detect and point mapping; it does not isolate neural kernels. Processing includes decode/in-memory preview/service/scoring; initialization is separate. These are Mac Python observations, not FireTV timings or a speedup comparison against Android-emulator MoveNet.

Recommendation: **stop further native Full port investment for now**, retain its optional diagnostic use, and require new independent timed natural-positive evidence before revisiting the costly portable implementation. This round demonstrates a useful left gate-coverage difference and a preserved timing failure, not a solved recognition pipeline. No threshold, frozen annotation, saved participation or default backend changed. No push, deployment, spending or upload occurred.

Supporting local evidence: `analysis.json`, the untouched raw reports, coordinate-audited views, `independent-review.md`, `plan.freeze.json`, preflight and privacy audit. The executed harness and source pins remain local and reproducible; all outputs contain scalar metadata only.
