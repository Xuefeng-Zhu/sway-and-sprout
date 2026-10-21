# Independent review of the first native UI attempt

The existing Android LiteRT MoveNet path produced saved scalar observations for **447 of 593 planned frames**. Both-press completed; both-stretch and cross-stretch became inactive before completing their files. **146 missing frames are unexecuted evidence, not model abstentions or negative outcomes.** The first attempt therefore does not support a complete cohort comparison.

This analysis uses frozen AI visual annotations, not human-reviewed ground truth. There are zero definite physical positive opportunities, so event recall remains unestimable regardless of the execution failure. Only both-press has a known whole-case zero expectation. The other clips remain unknown.

| Case | Scalar coverage | Confidence admitted | Low confidence | Covered certified-negative samples | Admitted negative samples | Saved native events | End UI score / rays / ACK |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| both-press | 210/210 | 117 | 93 | 156 | 93 | 0 | 0 / 0 / 0, verified |
| both-stretch | 99/188 | 0 | 99 | 25 | 0 | 0 on prefix | unavailable / unavailable / 0, scoring unverified |
| cross-stretch | 138/195 | 36 | 102 | 26 | 14 | 0 on prefix | unavailable / unavailable / 0, scoring unverified |
| Covered total | 447/593 | 153 | 294 | 207 | 107 | no emitted events in covered observations | no whole-cohort score claim |

Native `acceptedFrames` counts frames accepted by the replay service, **not** confidence admission. The partial last packets report decoded100/accepted99/discarded1 for both-stretch and decoded139/accepted138/discarded1 for cross-stretch, with `fullFileProcessed=false`. Their UI snapshots show the check screen and null score/ray counts. Both have `executionAcceptance=failed` and `nativeScoringMatches=false`; press passes execution and scoring evidence.

MoveNet exposes its model's per-keypoint scores. The adapter uses anatomical indices 5/6/9/10 (shoulders/wrists), maps them to decoded source pixels, and sets global confidence to the minimum of those four scores. The classifier requires each score and global minimum to be finite and at least 0.65, plus valid coordinates and shoulder span. This is separate from MediaPipe's visibility/presence semantics and is not a calibrated correctness probability. No threshold was changed.

All 447 covered frames have finite, non-sentinel geometric observations. Source-coordinate gates were recomputed using the frozen strict 0.30 up / 0.20 down margins and Euclidean shoulder span, independently of confidence, then compared with the frozen source-coordinate allowed sets.

- Press and the stretch prefix have zero gate conflicts. Cross has **nine left-gate conflicts**, at frames 96–99, 104, 106–107 and 109–110 (original source frames 246–249, 254, 256–257 and 259–260): MoveNet predicts left-down where the frozen AI region permits only left-up or transition. **All nine are rejected by the existing confidence gate.** This is a diagnostic discrepancy against AI bounds, not human-validated point-error ground truth.
- There are **zero admitted gate conflicts** and **zero single-arm-positive geometric conflicts on the 207 covered certified-negative samples**, even with confidence ignored. Covered negative exposure is 7.071867 sample-bin seconds; closed sampled spans total 6.678400 seconds. Missing negative samples are excluded. This is descriptive exposure, not a general false-positive-rate estimate.
- Singleton physical gate pairs agree on the covered frames: press98/98, stretch11/11, cross17/17. Broad uncertainty elsewhere and correlated AI labels prevent a population accuracy claim.
- No admitted single-arm-positive geometry occurs in any covered native prefix, so these observations cannot establish positive recognition benefit. No events exist for precision or onset-timing agreement.

| Case | Mean three-pass inference ms | P95 inference ms | Mean frame work ms | P95 frame work ms | App PSS KiB snapshot | Runner wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| both-press | 69.692 | 127.830 | 123.480 | 206.916 | 143463 | 27.294 |
| both-stretch prefix | 77.687 | 147.562 | 311.160 | 1384.473 | 150060 | 31.894 |
| cross-stretch prefix | 68.519 | 131.446 | 216.144 | 394.847 | 131603 | 30.967 |

These are CPU measurements from one **API34 ARM64 Android emulator**, LiteRT1.4.2, Lightning FP16v4, two threads and official three-pass stateless crop. They are not directly comparable to Mac Full timing and do not establish Fire OS/ARMv7, real camera, sustained memory or real Fire TV performance. Frame work and runner wall time have different scopes; selected reference checks add overhead. The recorded 30/18/21 reference checks show zero input-byte or reference-output differences. Scalar file-time stamps agree with the frozen PTS within numerical rounding and the declared stream ticks.

All three saved performance summaries report `resourcesClosed=false` and `cleanupSucceeded=true`; those summaries alone do not establish final resource closure. Final stop/closure evidence is owned by the parent controller and must be cited separately. Saved progress hashes match before and after each case; recorded physical camera calls are zero.

This first attempt is preserved as failed/partial execution evidence. A separate bridge-only run may diagnose model outputs without the UI round timer, but cannot retroactively turn these UI failures into a complete application acceptance. No porting or backend choice is justified by this preliminary set's zero definite positives.

Bindings and detailed frame conflicts are in [native-initial-analysis.json](native-initial-analysis.json); [analyze_native_saved.py](analyze_native_saved.py) reproduces the analysis with Python's standard library only. All 71 frozen files and 16 source pins were reverified unchanged. Raw saved case reports and logs were hash-checked before and after analysis, so concurrent replacement would fail instead of publishing mixed evidence.
