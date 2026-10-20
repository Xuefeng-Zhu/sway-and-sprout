# Natural-motion baseline diagnosis — 2026-10-20

The two normal-speed public clips still produce **zero gestures, zero rays and
ACK zero** through actual decoding, detector, pose model, classifier/service and
JavaScript game reducer. This is a diagnostic baseline, not a natural-motion
accuracy pass. No live-user recognition is verified.

## Reproduce without a camera

Prepare the ignored licensed media using the repository's existing pinned-source
instructions in [the portable test plan](MIGRATION-TEST-PLAN.md). The two continuous
clips are frozen by `sidecar/fixtures/frontal/bounded-frontal/encoded-media-manifest.json`.
Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python scripts/analyze-natural-motion.py --output verification-results/natural-motion
```

`--project /path/to/checkout` can select an explicit root. Output is local scalar
JSON only: per-frame landmark confidence/coordinates, predicted wrist gates,
detector ROI, classifier state and events. No images or preview JPEGs are written.
The analyzer permits only the two exact hash-verified local files with the FFmpeg
backend and prohibits Python socket/camera APIs. Each clip uses its unchanged
30-fps file clock, 319 frames, and the current actual game reducer. It does not
retime frames, prepend holds, flip classifier sides or retune thresholds.

The command exits successfully when the diagnostic run completes; that exit is
**not an accuracy verdict**. Full traces belong in ignored `verification-results/`.
The [small frozen baseline](verification/natural-motion-baseline-20261020.json)
records code/media hashes and observed counts without private machine paths.

## What the measurements demonstrate

| Observation | Original | Reflected derivative |
|---|---|---|
| Person detections / successful current-frame pose inference | 319/319 exactly one person | 319/319 exactly one person |
| Both-wrists-down predicted frames | 158 | 147 |
| Predicted raised-arm frames | 61 right, zero left | 65 left, zero right |
| Low-confidence frames | 73 | 81 |
| Frames in armed state | 124 | 84 |
| Gestures / rays / acknowledged sequence | 0 / 0 / 0 | 0 / 0 / 0 |

The original predicts both wrists down at frames 0–9. Their timestamps span
300 ms, so it arms at frame 9. At frame 10 the right arm begins a predicted
transition, while the game expects anatomical left. That wrong-side transition
disarms it; frame 13 begins a right-up run. Later there is no predicted left-up
gate in this clip. These are **model predictions**, not independent truth labels
for every frame.

The reflection's first frame has right-wrist confidence **0.637489**, below the
unchanged 0.65 minimum. Its next both-down run is only frames 1–9, spanning
**266.667 ms**. The left transition starts at frame 10 and left-up at frame 13,
so the initial raise never had the required 300 ms of confident neutral. This
explains that missed initialization without blaming frame gaps: the largest
deterministic inter-frame gap is approximately 33.334 ms, far below 300 ms.
Later wrist confidence failures and wrong-side transitions reset readiness.

All low-confidence bottlenecks in these runs were wrist estimates. The original
has 54 right-wrist and 19 left-wrist bottlenecks; the reflection has 49 left-wrist
and 32 right-wrist bottlenecks. Successful person detection and the status label
`tracking` therefore do not mean both wrists are usable for calibration.

The source and its reflection are not independently filmed left/right trials.
The footage does not provide a certified full six-alternation sequence. Zero
events cannot establish a decoder failure, an accuracy pass, or a general false
negative rate without independent motion annotations.

## ROI, orientation and temporal scope

No crop/rotation inverse defect was demonstrated. A supplementary independent
synthetic geometry review compared the pinned wrapper against OpenCV's affine
inverse over 75 cases / 300 landmarks, including fractional hips, 25 rotations
and 50 padded crops. Maximum recovery error was 0.00004578 px. This is geometry
evidence only; it does not certify learned landmark accuracy. The committed
`test_pose_contract.py` already retains meaningful padding/rotation, anatomical
index, confidence, shared-resize and all-120-output-permutation checks.

The original video's ROI angles range from −9.16° to 14.35°; the reflected video's
range from −16.85° to 5.91°. No 180° ROI flip appeared. Adjacent ROI angle changes
reach 9.49° / 11.23°, and hip-center shifts reach 15.83 / 20.77 px. Those are
measured jitter, not proof of an implementation error. All 319 frames still have
one detector result and a pose result.

There is **no temporal ROI tracker** in this implementation: full-frame detection
and pose inference run independently on every frame. `tracking` names a successful
current-frame pose result. `people[0].copy()` correctly protects detector output
from the vendored preprocessing's in-place coordinate translation. The anatomical
indices, image-coordinate output and minimum visibility/presence confidence
extraction agree with the pinned model contract; no decoder sign/swap fix is
justified by these measurements.

## Next acceptance boundary

Keep the 0.65 confidence, 300 ms neutral, 350 ms hold, 500 ms cooldown and 300 ms
maximum frame-gap requirements unchanged unless independent evidence supports a
deliberate behavior change. Readiness must explain which wrist is missing or not
down, how much confident neutral has accumulated, and whether a wrong side or
confidence loss reset a hold. A raised hand must never substitute for initial
neutral calibration. Do not prompt a real person to raise before readiness.

Before a live test, verify an independently annotated natural-motion interval
through the actual video/service/game pipeline and retain unsupported coverage
as a limitation. The current held public fixtures and synthetic tensors are useful
controls, but cannot replace that evidence. Never label reflected or scripted
sessions as saved human participation.
