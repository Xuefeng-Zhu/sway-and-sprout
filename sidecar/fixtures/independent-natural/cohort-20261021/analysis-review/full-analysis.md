# Independent Full result review

All 593 frozen frames completed through the existing MediaPipe Full IMAGE adapter, classifier, event service and JavaScript scoring path: **0 events, 0 rays, ACK 0**. This is preliminary diagnostic evidence from **AI visual annotations, not human-reviewed ground truth**. The frozen set has **zero definite physical positive opportunities**; event recall is therefore **unestimable**. Zero events does not establish positive recognition.

The three results have no execution validation failures, complete decoding, closed models and cleared preview caches. The reviewer ran only standard-library analysis of saved scalar results and labels; no inference, camera, network activity, threshold changes or annotation edits. The plan SHA is `fb84346ad034457d469ff7963f54ec3e518be2675f39ac7aedfbf37cf389f73b`; all 71 frozen files and 16 source pins were verified unchanged before and after this analysis.

| Frozen case | Frames | Classifier confidence admitted | Low confidence | Valid coordinate geometry | Frozen pose-negative samples | Admitted negative samples | Events / rays / ACK |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| both-press | 210 | 210 | 0 | 210 | 156 | 156 | 0 / 0 / 0 |
| both-stretch | 188 | 113 | 75 | 187 | 103 | 87 | 0 / 0 / 0 |
| cross-stretch | 195 | 183 | 12 | 195 | 56 | 54 | 0 / 0 / 0 |
| Total | 593 | 506 | 87 | 592 | 315 | 297 | 0 / 0 / 0 |

The adapter reports `tracking` for every frame; that status does not mean the classifier admitted every observation. Full joint scores are `min(visibility, presence)` and the adapter's global 0.65 is an admission lower bound. These are not calibrated correctness probabilities or scores interchangeable with MoveNet. Rejection involved wrists: both-stretch right 73 / left 14 frames, overlapping on 12; cross-stretch right 5 / left 9, overlapping on 2. Both-stretch frame 170 contains a zero-sentinel joint, so confidence-independent geometry is conservatively unavailable there. No shoulders fell below 0.65.

Geometry was recomputed from finite, in-image, non-sentinel coordinates without using confidence. Strict up/down thresholds and Euclidean shoulder span follow the frozen contract. Source and Full working coordinates give the same gate pairs on all 592 available frames, including the portrait clip's separate X/Y inverse scales.

- There are **0 gate incompatibilities** with the frozen allowed working-coordinate gate sets. These uncertainty sets can be broad; compatibility is not proof of point accuracy.
- Where both physical gate labels are singletons, all available pairs match: press 98/98, stretch 80/80, cross 17/17. Of these 195 frames, 190 pass confidence admission. Correlated AI-labelled frames do not establish population accuracy.
- There are **0 predicted single-arm-positive geometric conflicts on 315 certified pose-negative samples**, both before and after confidence admission. Their sample-bin exposure is 11.191867 seconds; the sum of closed first-to-last sampled spans is 10.725067 seconds. Neither quantity proves continuous subframe behavior or supplies a general false-positive-rate estimate.
- Cross-stretch has eight admitted single-arm geometric frames, all in physically uncertain regions: expected-left at frame 97 and frames 104–108; opposite-right at frames 0 and 2. The longest expected-left sampled span is 133.333 ms, below the required continuous 350 ms hold. At those left-positive frames the actual classifier is unarmed and reports `needs-neutral`; maximum recorded hold is 0 ms in every case. There is no emitted event to assess against an onset interval.

Only both-press has a proved whole-case zero expectation and a `negative-control-matched` result. Both-stretch and cross-stretch correctly remain `observed-only` with unknown event expectation. Their zero outputs must not be relabelled successful negative controls or interpreted as measured misses. Event precision is unestimable because there are no emitted events; event timing agreement is not applicable.

| Case | Median adapter inference ms | Processing seconds | Model initialization ms | Case wall seconds including initialization |
| --- | ---: | ---: | ---: | ---: |
| both-press | 23.733 | 5.545 | 1832.207 | 7.637 |
| both-stretch | 24.878 | 5.214 | 71.560 | 5.439 |
| cross-stretch | 25.187 | 5.546 | 72.059 | 5.771 |

These are Mac Python measurements. Adapter inference includes preprocessing, RGB conversion and SDK-to-observation mapping; processing includes decoding, preview work, service and headless JavaScript scoring but excludes model construction. Cold first-case initialization is reported separately. Actual service observation and delivery clocks agree with frozen frame PTS to numerical rounding (maximum error below 1e-9 ms), within each declared stream tick, and decoded FPS matches frozen FPS. These results do not certify browser rendering, live-user behavior, native latency, Fire OS/ARMv7 operation, camera access or sustained Fire TV hardware performance.

The set supports checking negative exposure and abstention behavior, not choosing a new backend for positive reliability or proceeding to native porting on accuracy grounds. A separately frozen set with definite, independently reviewed, neutral-to-single-arm 350 ms positive opportunities is still needed before an acceptance claim. Detailed counts and bindings are in [full-analysis.json](full-analysis.json), the reproducible standard-library analysis is [analyze_full.py](analyze_full.py), and a second independently recomputed count check is [numeric-independent.json](numeric-independent.json).
