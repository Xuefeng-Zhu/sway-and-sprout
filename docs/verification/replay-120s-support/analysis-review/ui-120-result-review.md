# Independent review of the 120-second native UI rerun

Both previously interrupted Pexels clips now complete the real application flow: **383/383 frames, zero native events, zero displayed rays and ACK 0**. Each retains its EOF scoring snapshot, waits for the actual 120-second diagnostic timer, reaches **Replay finished**, clicks **View replay result**, displays **Replay result**, reloads home without changing saved progress, and closes native resources. All independent case and controller checks pass.

| Clip | Complete frames | Confidence admitted / rejected | EOF wall seconds | Real timer completion wall seconds | UI rays / native events / ACK |
| --- | ---: | ---: | ---: | ---: | --- |
| Both stretch | 188/188 | 5 / 183 | 50.982 | 121.751 | 0 / 0 / 0 |
| Cross stretch | 195/195 | 36 / 159 | 41.124 | 120.798 | 0 / 0 / 0 |
| Total | 383/383 | 41 / 342 | Separate cases | Separate cases | 0 / 0 / 0 |

Each actual initial UI observation reports `120s`, `data-round-seconds=120` and the explicit diagnostic marker. Both measured completion walls exceed 120 seconds; the harness's declared one-second timing tolerance was not needed to establish that fact. EOF and final scalar logs have identical hashes, so waiting for completion and closing the Activity did not introduce more video frames or alter the captured observations. All frame indices are unique, ordered and complete, and unrounded file-time PTS matches frozen timestamps within their declared stream ticks.

The zero UI count and ray count independently match the native event sequence and acknowledgment metrics. Both completion packets become inactive. Stopped summaries confirm `resourcesClosed=true`, `cleanupSucceeded=true`, `verified=false` and ACK 0. Camera-call counters are zero at EOF, result, reload and cleanup; both emulator cameras were disabled. The saved controller confirms the OS network-deny preflight, successful verification exit, and shutdown of the task-owned emulator and isolated ADB server. The reviewer performed saved-data analysis only, with no model execution, SDK initialization, camera or network actions.

The recognition profile is unchanged: Lightning FP16, LiteRT1.4.2, CPU, two threads, three-pass stateless crop, fixed 0.65 admission. MoveNet global confidence equals the minimum of its four required keypoint scores on every frame. Service `acceptedFrames=383` denotes processed-frame coverage; confidence admission is 41. Model scores are not calibrated correctness probabilities and are not interchangeable with MediaPipe visibility/presence.

Native geometry has the same nine cross-stretch discrepancies against frozen AI allowed gate sets, all confidence-rejected, and zero admitted discrepancies. All 159 certified-negative samples are covered; 16 pass confidence admission, with zero predicted single-arm-positive conflicts even when confidence is ignored. These are preliminary diagnostics against frozen AI visual annotations, **not human-reviewed ground truth**. Both clips retain **unknown whole-case gesture expectations** and `observed-only` recognition status. Their zero events must not be labelled negative acceptance passes.

| Clip | Mean three-pass inference ms | P95 inference ms | Mean frame work ms | P95 frame work ms | App PSS KiB snapshot |
| --- | ---: | ---: | ---: | ---: | ---: |
| Both stretch | 79.225 | 148.562 | 265.368 | 550.866 | 81287 |
| Cross stretch | 68.026 | 131.800 | 205.847 | 332.857 | 108441 |

Each clip records 30 reference checks with zero input-byte or output differences. EOF wall time includes application replay, preview, decoding, processing and transport; full case walls including setup/result/reload/closure are 128.132 and 124.614 seconds. Inference, frame work and complete UI wall time have distinct scopes. These API34 ARM64 emulator measurements do not establish live frame-rate behavior, Fire OS/ARMv7 support, UVC camera access or sustained real Fire TV performance.

The rerun changes only the authorized diagnostic duration: the exact video-verification Sunshine camera-input route uses 120 seconds; ordinary rounds retain their 30-second duration. At review completion, all **15 unchanged semantic pins**, the **authorized current main.js hash**, **71 historical frozen files**, and **10 original UI evidence files** match their saved baselines. The old main.js hash remains historical evidence; this report does not claim all 16 current source pins are unchanged. The original 30-second failures are preserved, and the earlier bridge-only run retains its narrower scope.

There are still **zero definite physical positive opportunities**. Recall and positive model benefit remain unestimable; zero events/rays/ACKs demonstrate zero-score consistency and replay completion, not successful positive recognition or positive scoring/ACK behavior. The experiment resolves the premature diagnostic UI interruption, while the original recognition-evidence and physical-hardware limitations remain.

Detailed independent checks, actual timing, raw input SHA bindings and preservation evidence are in [ui-120-result-review.json](ui-120-result-review.json), reproduced by [review_saved_ui.py](review_saved_ui.py). The frozen rerun plan SHA is `002d61ca7dcfbc2254cf0def39a2e08ca81a8669a6a097bce0cd23b162f84755`; the pre-run baseline SHA is `3cdb7ea6a561c927e0a711332b2679a141cc37bb6f9bf8f90fec2ce88c78ac87`.
