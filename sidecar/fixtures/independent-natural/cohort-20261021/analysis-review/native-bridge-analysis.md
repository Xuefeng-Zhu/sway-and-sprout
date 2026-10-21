# Independent review of the supplemental native bridge run

The separate bridge-only run completed **all 593 frozen frames**, with **0 native events and receipt ACK 0**. All three case reports pass their bridge execution checks, explicitly deactivate the source and record stopped summaries with `resourcesClosed=true` and successful cleanup. Frozen inputs, annotations, thresholds and model profile were unchanged. This supplements model diagnostics; **it does not repair the first attempt's incomplete game UI runs** or exercise game reducer scoring, rays or rendering.

| Case | Frames | Native confidence admitted | Native low confidence | Full confidence admitted on same frames | Native AI gate conflicts / admitted conflicts | Certified-negative samples / admitted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| both-press | 210 | 117 | 93 | 210 | 0 / 0 | 156 / 93 |
| both-stretch | 188 | 5 | 183 | 113 | 0 / 0 | 103 / 2 |
| cross-stretch | 195 | 36 | 159 | 183 | 9 / 0 | 56 / 14 |
| Total | 593 | 158 | 435 | 506 | 9 / 0 | 315 / 109 |

Native `acceptedFrames=593` is complete replay-service coverage, not confidence admission. MoveNet global confidence equals the minimum of its four required keypoint scores on every frame; the 0.65 classifier gate remains unchanged. Full uses `min(visibility,presence)` with its separately defined task admission. The two models' score semantics are distinct; the larger Full admission count is not itself proof of greater correctness or calibrated confidence.

The AI visual annotations were frozen before inference and have not been human-reviewed. There are **zero definite physical positive opportunities**. Consequently event recall is **unestimable**; zero emitted events also leaves precision unestimable and event timing agreement inapplicable. Only both-press has a proved whole-case zero expectation. Both-stretch and cross-stretch remain observed-only with unknown event sequences.

Geometric comparison uses mapped source-pixel coordinates and the frozen strict up/down margins with Euclidean shoulder span, ignoring confidence before separately checking admission. All 593 native frames have finite, in-image, non-sentinel geometry.

- Native has nine left-gate discrepancies against frozen AI allowed sets, all in cross-stretch at frames 96–99, 104, 106–107 and 109–110: left-down is predicted while only up/transition is permitted. **All nine are rejected by confidence.** Full has no allowed-set conflicts. These are preliminary discrepancies against AI uncertainty bounds, not human-confirmed keypoint errors.
- Native has no admitted single-arm-positive geometry in this set. Full has eight such frames in uncertain regions, with no sufficient neutral/hold state and no event. Neither observation establishes positive recognition performance.
- Both native and Full have **zero single-arm-positive geometric conflicts on all 315 frozen certified-negative samples**, including when confidence is ignored. This exposure is 11.191867 sample-bin seconds, or 10.725067 seconds when summing closed sampled spans. These are different descriptive measures; neither is continuous subframe proof or a general false-positive-rate estimate.
- Where both physical gate labels are singletons, native agrees on 195/195 frames, of which 71 are admitted. Broad uncertainty on other frames and frame correlation prevent a population-accuracy interpretation.
- On the paired 593-frame policy comparison, both models admit 157 frames, only Full admits 349, only native admits 1, and both abstain on 86. Their predicted gate pairs differ on 106 of 592 frames with geometry available from both. Gate differences within allowed uncertainty are not necessarily errors.

| Case | Mean three-pass inference ms | P95 inference ms | Mean frame work ms | P95 frame work ms | Active bridge wall seconds | App PSS KiB snapshot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| both-press | 35.717 | 73.127 | 73.146 | 127.767 | 15.614 | 125075 |
| both-stretch | 29.960 | 48.636 | 96.946 | 196.062 | 18.511 | 139193 |
| cross-stretch | 27.522 | 41.077 | 93.542 | 199.861 | 18.447 | 141916 |

These are LiteRT1.4.2 CPU measurements from one API34 ARM64 Android emulator, Lightning FP16v4, two threads and three-pass stateless crop. Inference is the selected three-pass profile; frame work includes decode/preprocessing and diagnostic overhead, with reference checks recorded separately. All 30 reference checks per clip have zero input-byte and output differences. Case walls including connection/setup/closure are separately 28.019, 23.379 and 21.725 seconds. No new kernel-only, native-versus-Mac speed, sustained peak-memory or Fire TV performance claim is supported.

Scalar file-time traces match frozen PTS to numerical rounding (maximum below 1e-9 ms), within declared stream ticks. Every case reports full file completion, valid delivery comparison, matching receipt ACK, explicit deactivation and resource closure. Home screen and saved progress remain unchanged; recorded camera calls are zero. **Receipt ACK is not UI score:** with no events, this run also does not demonstrate positive event delivery/acknowledgment behavior. The physical camera remained outside this recorded-video experiment; real UVC access and Fire OS/ARMv7 execution are unverified.

This set provides additional abstention and negative-exposure diagnostics, including a confidence-rejected native discrepancy, but cannot establish Full's positive benefit or justify native porting on recognition evidence. The next necessary evidence is a separately frozen set containing definite neutral-to-single-arm opportunities with the required continuous hold, including onset uncertainty and independent human review before acceptance claims. Existing production defaults and failure results should remain intact.

Detailed hash-bound results are in [native-bridge-analysis.json](native-bridge-analysis.json), reproduced by [analyze_bridge_saved.py](analyze_bridge_saved.py). The first UI execution is preserved separately in [native-initial-analysis.md](native-initial-analysis.md); Full's separate scope and Mac timing are in [full-analysis.md](full-analysis.md). This reviewer used standard-library saved-data analysis only, performed no inference or network activity, and reverified all 71 frozen files plus 16 source pins before and after reading.
