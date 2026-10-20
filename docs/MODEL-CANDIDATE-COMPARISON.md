# Bounded model comparison — 2026-10-20

Retain the verified MediaPipe Full IMAGE backend as the optional **Mac diagnostic baseline**. Neither Heavy nor the evaluated RTMPose pair warrants replacement: Heavy does not recover a sustained accepted overhead hold and costs about three times as much; RTMPose loses the six-event near-face control. The default OpenCV backend is unchanged. These Mac results do not select a production television runtime.

The [structured record](verification/candidate-portability-20261020.json) contains all 21 completed case results, frozen media/annotation bindings, exact artifact pins, timing scopes and SHA256 bindings to the local scalar evidence. No annotation, gesture threshold or timing was changed to fit a candidate.

## Actual pipeline and controls

The comparisons use exact local public-video files and the canonical verifier: decode → native model → unchanged gesture classifier/service → in-memory preview → actual JavaScript scorer and ACK. They are accelerated deterministic file-clock tests, without HTTP replay or human camera participation. No decoded frame was saved or uploaded; video/synthetic completion does not save participation.

| Input | Full events / rays / ACK | Heavy | RTMPose-m |
| --- | ---: | ---: | ---: |
| Clear constructed held sequence | 6 / 6 / 6 | 6 / 6 / 6 | 6 / 6 / 6 |
| Frontal constructed held sequence | 6 / 6 / 6 | 6 / 6 / 6 | 6 / 6 / 6 |
| Near-face constructed held sequence | 6 / 6 / 6 | 6 / 6 / 6 | **0 / 0 / 0** |
| Natural right-only negative | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Natural both-up negative | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Continuous original, observed only | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Continuous reflected, observed only | 1 / 1 / 1 | 0 / 0 / 0 | 0 / 0 / 0 |

The three six-event fixtures use disclosed cuts, holds and/or reflection; they do not certify a filmed natural alternating sequence. The two continuous inputs have no independently certified expected sequence, so their counts cannot establish accuracy. The right-only clip starts in a left-first game: zero is a correct wrong-side negative, not proof of positive right-arm recognition.

Gesture rules remain confidence ≥.65, both wrists down for 300 ms to arm, the expected wrist above its own shoulder by .30 shoulder-width while the opposite wrist is down, hold 350 ms, cooldown 500 ms and maximum frame gap 300 ms. Wrist-down margin is .20 shoulder-width. A transition resets partial hold; loss and ambiguous/both-up/wrong-side poses disarm. The same numeric confidence gate has different meanings across models.

## Overhead geometry versus confidence

The independently frozen DVIDS overhead window is frames 136–151, spanning 500.5 ms. It is a coarse right-up/left-down annotation, not exact per-joint ground truth.

| Window measure | Full | Heavy | RTMPose-m |
| --- | ---: | ---: | ---: |
| Raw coarse geometry matches | 9/16 | 9/16 | 16/16 |
| Accepted after confidence/person/bounds gates | 6/16 | 9/16 | 11/16 |
| Longest accepted first-to-last span | 66.733 ms | 233.567 ms | 166.833 ms |
| Meets required continuous 350 ms hold | No | No | No |

Full and Heavy both return down geometry for frames 136–140 and 142. Frame 143 yields two poses and is rejected. Heavy admits three additional geometrically raised frames that Full rejects for low right-wrist visibility, but its eight-frame accepted run still spans only 233.567 ms. RTMPose has correct coarse geometry throughout, with five right-wrist score rejections breaking continuity.

At frame 148, minimum right-wrist distance to a **pre-existing manual uncertainty rectangle** is 131.601 px for default Zoo, 31.773 px for Full, 2.771 px for Heavy and 4.599 px for RTMPose. These are distances to a broad rectangle on one frame, not exact landmark error/PCK. Better coordinates on this frame do not establish successful sustained scoring.

RTMPose near-face failure has a different cause: all 152 frames pass single-person detection, confidence and bounds; no raised frame clears the unchanged .30 shoulder-width margin. The 30 left and 30 right raised frames are classified as transitions. No exact near-face landmark ground truth establishes the size of a keypoint error, so threshold weakening would not be evidence-backed calibration.

RTMPose's both-up negative is weak evidence: detection rejects 118/136 frames, including every neutral frame; pose runs on only 18 frames. Zero events cannot establish robust both-up rejection after successful calibration.

## Candidate implementation and timing limits

Full and Heavy use the same canonical MediaPipe adapter with fresh CPU IMAGE graphs, `num_poses=2`, .65 task admission/joint gates and identical preprocessing. Full/Heavy metadata describe a task-admission lower bound rather than a measured global pose probability. IMAGE redetects each frame; these results do not transfer automatically to VIDEO/LIVE_STREAM tracking or future multiperson operation.

RTMPose uses the official older RTMDet-nano + AIC/COCO RTMPose-m CPU ONNX bundle, ONNX Runtime 1.31.0 CPU with two intra-op threads. It is not a claim about the latest Body7 models or a general SOTA ranking. The detector is BGR 320×320; pose uses the official Python continuous-affine/RGB 192×256 path and SimCC argmax decoding. The inspected export metadata supplies RGB normalization missing from the short example. This is not bit-parity with MMDeploy's differently rounded SDK crop/resize/pad geometry.

RTMPose native joint confidence is the uncalibrated minimum of the two SimCC axis maxima, not visibility/presence or a probability. The predeclared finite nonnegative wire cap `min(score,1)` preserves the .65 predicate; no sigmoid, softmax, threshold fit or learned calibration was applied. Native scores remain available in scalar diagnostics. No demonstrated integration bug was found against that declared contract.

| Measured Mac operation | Result |
| --- | --- |
| Whole MediaPipe task `detect()` median across cases | Full 23.074–23.208 ms; Heavy 69.043–69.437 ms |
| RTMPose typical native calls | Detector ≈9.3 ms + pose ≈29.9 ms |
| RTMPose adapter, frames where pose runs | ≈41.5 ms |
| RTMPose both-up adapter median, mostly detector-only rejection | 10.463 ms; not representative of pose throughput |
| 15.015 s DVIDS full decode/model/service/preview/JS pipeline | Full 10.837 s; Heavy 31.882 s; RTMPose 19.533 s |
| RTMPose seven-case process maximum RSS / peak footprint | 372,686,848 / 327,435,320 bytes on macOS |

Pipeline durations exclude model constructor/import time, recorded separately in JSON. They use file timestamps and preserve every frame. Heavy and RTMPose exceed this clip's original duration on this Mac. None of these numbers is camera-to-render latency, Android/Fire TV performance or a sustained-memory result.

Local reproducibility sources remain in `heavy-comparison-20261020/{compare_models.py,results-run1,selected-windows-postanalysis.json}` and `rtmpose-evaluation/{compare_pipeline.py,results-run1,saved-results-audit}` under the dated task workspace. The structured record pins those scalar sources. Binaries, media and operational logs remain ignored and local.
