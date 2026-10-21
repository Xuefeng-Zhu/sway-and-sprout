# Natural-left timing audit — 2026-10-21

**The fixed timed test remains FAILED.** Its 416.667 ms early event is consistent with the implemented classifier and file clock. The audit establishes a difference between the conservative certified-overhead-window contract and the wrist-height rule; it does not establish either a physical false positive or a valid physical 350 ms hold. No candidate is promoted. Native port/build work remains paused.

## Video source

The clip is [Kettlebell Overhead Lunge, DVIDS679690](https://www.dvidshub.net/video/679690/kettlebell-overhead-lunge), credited to Capt. Matthew Holfinger / U.S. Marine Corps Training and Education Command, VIRIN190510-M-JT909-020. The archived official page marks it PUBLIC DOMAIN. The foreground person wears a green T-shirt and shorts in a gym; the raised screen-right arm is anatomically left. The appearance of U.S. Department of War visual information does not imply or constitute DoW endorsement.

The original 640×480 rendition is 30/1 fps. The evaluated trim contains source decoded display-order frames **285–367 inclusive**, zero based: **9.500000–12.266667 s end-exclusive**, 83 frames / 2.766667 s. Last sample is at 12.233333 s. It has no spatial crop, mirror, duplication, retiming or splice. Local path: `sidecar/fixtures/.cache/native-confidence-study/left-natural.mp4`; SHA256 `e4cc461c1c8c162c0f2bd0d256dcd99cd229e997b2ac4175715e34e0240ca8c8`.

## What was checked

Fresh metadata checks verify all 946 source and 83 clip display timestamps, at 512 ticks/frame in a 1/15360 time base. Source frame 285 maps exactly to clip 0 with a 9500 ms offset. All 83 inference/observation/delivery timestamps match clip PTS. Source B-frame packet reordering does not reorder decoded display PTS. Independent scalar recalculation reproduces all 83 saved gates and classifier states, with zero mismatches and the exact event. No inference, SDK initialization or recompilation was needed.

| Milestone | Clip / source frame | Clip time |
| --- | --- | ---: |
| Neutral begins; arms after 300 ms |23 / 308; 32 / 317|766.667; 1066.667 ms|
| Raised gate and hold begin |38 / 323|1266.667 ms|
| Event / JS score 1 / ACK 1 |49 / 334|1633.333 ms|
| Certified raised window begins |51 / 336|1700.000 ms|

The hold lasts 366.667 ms, or 11 frame intervals, meeting the unchanged 350 ms rule. No clock, truncation, ACK or control-reset defect explains the lead. The authored lower event bound is 2050 ms: certified start 1700 + 350. Its first eligible sample is frame 62 at 2066.667 ms. The actual event precedes the authored bound by 416.667 ms.

## Geometry and uncertainty

The original annotation explicitly describes source 317–335 as a conservative transition exclusion, not a precise threshold-crossing estimate. The frozen event contract requires the dwell fully inside the certified window. The implemented rule instead requires a wrist more than 0.30 Euclidean shoulder spans above its own shoulder and the other wrist more than 0.20 spans below, with unchanged 0.65 admissions. It requires neither a straight elbow nor a wrist above the head.

A separate AI reviewer inspected every transition frame and froze broad joint-center boxes before interval calculation, without opening model points. Selection was posthoc, and timing context was disclosed before saving; this is model-coordinate-blind, not fully event-blind or human ground truth. Source 317 robustly fails the raised gate; 318–331, including hold-start 323, remain uncertain; 332–335, including event 334, robustly pass. The opposite wrist stays clearly down. All 76 saved model points fall within the broad audit bounds, which does not prove accuracy.

The trigger posture is clear, but only 66.667 ms of prior robust geometry is established from source 332. The audit cannot independently certify a physical 350 ms hold or determine the exact crossing time. The model's onset is compatible with these uncertainty bounds. No boxes, labels, windows or failures were replaced or retuned.

This qualifies the timing-based rationale in the [earlier benefit report](PYTHON-FULL-NATURAL-BENEFIT.md), without converting its failure to a pass. Before another timed comparison, freeze geometry, uncertainty and event-window policy prospectively on new independent natural footage. Existing tested footage is diagnostic, not a new held-out acceptance set. No browser, live user or Fire TV result is claimed.

The [scalar evidence](verification/natural-left-timing-audit-20261021.json) pins original inputs, results and local audit files. Full reproducible checkers, PTS, all 19 visual comparisons and public diagnostic frames remain in `/Users/frank/Documents/Codex/2026-10-19/task/confidence-calibration/early-trigger-audit/`. Original result/annotation/source hashes are unchanged. Camera stayed off; no new tools, upload, push, deployment, spending or credentials. No action is denied, pending or uncertain.
