# Independent natural-video diagnostic comparison — 2026-10-21

Preliminary AI visual annotations were frozen before either model ran. This round does not establish positive-recognition improvement or justify a MediaPipe native port: the selected material contains **zero definite positive opportunities** under the existing game rules. No human supplied or confirmed these labels. Human validation remains necessary before acceptance. A post-run provenance review also found conflicting copyright notices on the DVIDS case: it is not cleared for redistribution; the two Pexels cases retain their recorded license evidence.

## Frozen evaluation and sources

The [evaluation contract](/Users/frank/mygit/sway-and-sprout/docs/NATURAL-EVALUATION-CONTRACT.md) records the existing geometry, 300 ms neutral, continuous 350 ms hold, opposite-arm condition, 500 ms cooldown, >300 ms gap reset and confidence/loss handling. Physical wrist/shoulder uncertainty is separate from model confidence; an uncertain onset remains an interval. Thresholds, previous annotations/failures and production defaults were preserved.

The cohort was frozen at 04:46:56 UTC, before Full inference. Plan SHA256 is `fb84346ad034457d469ff7963f54ec3e518be2675f39ac7aedfbf37cf389f73b`. All 71 protected files and 16 recognizer/state-machine source pins are checked separately. Three contiguous trims contain 593 frames; decoded YUV pixels and CFR display PTS match the originals. No mirror, splice, retiming or model-output-based selection was used.

| Case | Original source / credit | Source range | Frames / FPS | Frozen AI reference |
| --- | --- | --- | --- | --- |
| both-press | [DVIDS 768147: Kneeling Overhead Press](https://www.dvidshub.net/video/768147/kneeling-overhead-press-fitness-workout), Robert Price / AFN Sasebo; instructor Kelly Stratoti; **conflicting public-domain/copyright restriction notices; redistribution not cleared** | Frames [180,390), approximately 6.006–13.013 s | 210 / 30000÷1001 | Zero-event sequence under every path allowed by the frozen uncertainty bounds |
| both-stretch | [Pexels 7628775: Woman Stretching Her Arms](https://www.pexels.com/video/woman-stretching-her-arms-7628775/), ArtHouse Studio; [Pexels License](https://www.pexels.com/license/) | Frames [0,188), 0–7.52 s | 188 / 25 | Unknown sequence; possible single-arm interval is not a definite opportunity |
| cross-stretch | [Pexels 8401267: A Woman Stretching her Arms in the Street](https://www.pexels.com/video/a-woman-stretching-her-arms-in-the-street-8401267/), RDNE Stock project; Pexels License | Frames [150,345), 5–11.5 s | 195 / 30 | Unknown sequence; occlusion and opposite-wrist boundary preserve uncertainty |

**Provenance correction:** the [official DVIDS page](https://www.dvidshub.net/video/768147/kneeling-overhead-press-fitness-workout) labels the asset public domain while also warning of copyrighted portions whose distribution is restricted. The initial frozen record's stronger statement that no apparent asset-specific restriction existed was not justified. A separate correction supersedes that interpretation without changing the source, AI annotations, cohort selection or failed/passed execution records. No media was committed or redistributed. DVIDS's 210 frames remain historical local diagnostic evidence, not a cleared redistributable validation asset. The two explicitly Pexels-licensed sources supply 383 frames; both exact sequences are unknown, so they do not supply a definite positive or whole-sequence zero reference.

These are new source/production groups, excluding the old kettlebell clip and its derivatives. Performer identity separation and model-training independence are not established. Nine downloaded source videos plus bounded metadata/access screens were considered; the source-selection note records individual exclusions. This is not an exhaustive search or a claim that suitable public positive footage does not exist.

The both-press proposal's original unknown sequence is unchanged. A separate **pre-inference** universal state-machine proof supplies its zero reference: mandatory disarm at frames 85–91, earliest neutral at 92 and arming at 101, first hold at 102, only 66.7 ms available through 104 before disarm at 105. A geometry-only possible 400.4 ms interval therefore cannot yield an event. This proof remains conditional on AI visual bounds, not human ground truth. The other two cases retain unknown sequence truth.

## Full result through the existing service and JavaScript reducer

| Case | Complete frames | Confidence admissions | Model events / JS rays / protocol ACK | Interpretation |
| --- | --- | --- | --- | --- |
| both-press | 210/210 | 210 | 0 / 0 / 0 | Frozen AI-bound negative matched |
| both-stretch | 188/188 | 113 | 0 / 0 / 0 | Observed only |
| cross-stretch | 195/195 | 183 | 0 / 0 / 0 | Observed only |

Full admitted 506/593 observations and abstained on 87 low-confidence observations. Its confidence is `min(visibility,presence)` per joint plus a task-admission lower-bound marker; it is neither calibrated correctness probability nor MoveNet's raw keypoint score. Confidence-free geometry was available in 592 frames; one invalid/sentinel joint was excluded.

Independent saved-row analysis found no gate incompatibilities with the frozen allowed sets. All 195 frames with singleton gate pairs agreed. These broad AI bounds support non-contradiction, not a point-localization accuracy or human-acceptance claim. On 315 independently marked pose-negative sampled bins, 297 were confidence-admitted and none predicted single-arm-positive geometry. The bin exposure is 11.191867 s (count/FPS); closed first-to-last spans are reported separately. Correlated frame bins do not estimate a general false-positive rate or certify subframe continuous movement.

There were zero emitted events, hence zero definite false events and zero unresolved emitted events in this run. **Recall, precision and positive timing agreement are unestimable**: there are no definite positive opportunities and no emitted events. Abstentions were not removed to create a positive success denominator. No natural alternating six-event sequence was certified.

The complete path was decode → existing Full adapter → classifier/MotionService → current headless JavaScript reducer and ACK reconciliation. It did not render a browser UI or measure live transport/capture latency. All graphs closed and the in-memory preview cache cleared; no inference output frames were saved.

## Actual Android application result

Existing MoveNet Lightning FP16 v4 (`0fac2226112d0371903ca86e3853cec24ef603a0b2f96f589b180f0ebdd135ab`) ran in LiteRT 1.4.2, CPU/two threads, existing three-pass stateless image refinement and unchanged raw-score admission 0.65. The release/default model was not replaced. Each decoded frame produces one classified observation after three model calls.

| Case | Scalar frame coverage | Native events / ACK | Real garden score | Existing game result |
| --- | --- | --- | --- | --- |
| both-press | 210/210 | 0 / 0 | 0, six uncollected ray slots and explicit replay badge verified | Complete negative matched |
| both-stretch | 99/188 | 0 / 0 on partial run | Unavailable: game had entered check screen | Failed/incomplete |
| cross-stretch | 138/195 | 0 / 0 on partial run | Unavailable: game had entered check screen | Failed/incomplete |

The application's real 30-second round ended input before the latter two files finished. They were not shortened, re-annotated, given more game time or counted as zero-event passes. Exactly 447/593 native scalar frames were captured; 146 were missing, and the two interrupted epochs each discarded one decoded in-flight frame. Saved progress did not change; browser camera calls were zero. The harness now requires a present, explicitly scored garden and complete unique frame coverage, so a missing UI cannot masquerade as zero points. Original failed results remain in `movenet-results`.

On this partial native coverage, confidence admitted 153/447 observations, rejected 294 and retained valid mapped geometry in 447. Nine gate conflicts with frozen AI allowed sets occurred in cross-stretch; all nine were below the unchanged confidence gate. No admitted gate incompatibility or single-arm-positive geometry occurred in the 207 covered negative bins. Different score definitions prevent treating Full's larger admission count as a calibrated reliability improvement.

The initial native summaries were captured before managed decoder/interpreter closure (`resourcesClosed=false`); they do not prove final SDK cleanup. Task-owned emulator and isolated ADB server shutdown were separately confirmed. Supplemental bridge-only completion/cleanup is reported separately below.

## Supplemental native bridge comparison

The supplemental comparison completed all **593/593** frames through the existing NativeVideoReplay → `/motion/events` route and canonical packet validator while the app remained on its home screen. All three cases had zero native events and zero receipt ACKs; this is **not game UI or JavaScript reducer scoring**. The earlier real-game failures remain unchanged.

| Case | Complete bridge frames | Confidence admissions / abstentions | Events / receipt ACK | Explicit inactive / native resources closed |
| --- | --- | --- | --- | --- |
| both-press | 210/210 | 117 / 93 | 0 / 0 | Yes / yes |
| both-stretch | 188/188 | 5 / 183 | 0 / 0 | Yes / yes |
| cross-stretch | 195/195 | 36 / 159 | 0 / 0 | Yes / yes |

This full coverage admitted 158/593 observations and abstained on 435. All mapped coordinates were geometrically available; native confidence rejection was reported separately. Nine cross-stretch gate incompatibilities remained, all below admission. All 315 frozen pose-negative bins were covered, 109 confidence-admitted, with zero predicted single-arm-positive conflicts. Full had zero such gate incompatibilities on the same frozen labels, but the cohort still contains no definite positive opportunity, so no recall advantage is established.

The bridge sent an explicit inactive revision after EOF, then finished the Activity through its real Back handler. Every stopped summary reported `resourcesClosed=true`, `cleanupSucceeded=true`, `verified=false`; received events and protocol ACKs agreed. The home screen remained active until finish, browser camera-call counters were zero and saved progress was unchanged. All scalar rows, delivery checks and final resource flags were independently checked. This is complete native model/bridge evidence and a managed-cleanup check, not a repaired UI acceptance result.

| Bridge-only API34 ARM64 emulator | Decode / preprocess mean ms | Three-call inference mean / p95 ms | Total frame mean / p95 ms | Active wall s | PSS snapshot KiB |
| --- | --- | --- | --- | --- | --- |
| both-press | 15.46 / 15.96 | 35.72 / 73.13 | 73.15 / 127.77 | 15.614 | 125075 |
| both-stretch | 15.37 / 43.81 | 29.96 / 48.64 | 96.95 / 196.06 | 18.511 | 139193 |
| cross-stretch | 19.20 / 40.08 | 27.52 / 41.08 | 93.54 / 199.86 | 18.447 | 141916 |

The supplementary run kept the UI at home and used a different polling/rendering workload. Its lower costs do not show a model/code optimization and do not erase the initial game failure. Without controlled profiling, the difference cannot be attributed to one rendering, decode, thermal or scheduling cause. All 30 sampled reference model calls per case had zero input/output parity difference in both initial and supplementary runs.

## Measured costs and privacy

| Mac Full CPU IMAGE, two-pose configuration | Adapter median / p95 ms | Processing s | Initialization ms | Wall including initialization s |
| --- | --- | --- | --- | --- |
| both-press | 23.733 / 25.709 | 5.545 | 1832.207 | 7.637 |
| both-stretch | 24.878 / 26.961 | 5.214 | 71.560 | 5.439 |
| cross-stretch | 25.187 / 26.373 | 5.546 | 72.059 | 5.771 |

Full used existing MediaPipe 1.1.1 / OpenCV 5.0.0 / NumPy 2.5.4 and model SHA256 `4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad`. Adapter timing includes resize/RGB/task/mapping; total processing also includes decode, preview/service and headless scoring. These are Mac diagnostic measurements.

| Initial Android TV API34 ARM64 emulator | Decode mean ms | Preprocess mean ms | Three-call inference mean ms | Total frame mean / p95 ms | App PSS snapshot KiB |
| --- | --- | --- | --- | --- | --- |
| both-press, complete | 14.34 | 29.47 | 69.69 | 123.48 / 206.92 | 143463 |
| both-stretch, partial | 42.60 | 138.05 | 77.69 | 311.16 / 1384.47 | 150060 |
| cross-stretch, partial | 32.98 | 98.77 | 68.52 | 216.14 / 394.85 | 131603 |

Total frame cost includes sampled official-reference parity work and extra overhead; inference alone is not end-to-end latency. All sampled input/output parity differences were zero in these runs. PSS is a single app-process snapshot, not a sustained peak or full-TV memory budget. The emulator used two virtual cores and 1536 MiB guest RAM on the 8 GB Mac. Mac and emulator timings are different measurements/environments and cannot establish a backend speedup or physical TV performance.

Full ran under OS deny-all networking, including a fresh SDK-free no-payload probe rejected with EPERM before SDK initialization. Android/emulator/ADB ran under the existing OS profile denying external networking while allowing localhost/Unix test transport; its fresh probe also failed with EPERM. Possible SDK/network attempts are not described as telemetry-disabled. The first native launcher stopped at a restricted child `ps` before Android tools ran; a fresh read-only parent inventory replaced that process check without relaxing the network profile. No unsandboxed inference fallback was used.

The physical camera remained off; front/back emulator cameras were explicitly `none`. No media/model/software dependency download, SDK agreement, credential creation/change, upload, push, deployment or spending was part of inference/build execution. Existing cached tooling/artifacts and the existing Android identity were reused. Public media had been downloaded and visually screened locally before the cohort freeze, under recorded public usage evidence.

## Decision and remaining evidence

Continue validation, **do not start native Full porting or source builds** on this evidence. The current cohort supports a narrow negative check and confidence/geometry diagnostics, not the missing recognition benefit. The old early-trigger and other positive failures remain unchanged. This run also demonstrates application replay failing to finish two higher-resolution clips within its existing real round on this emulator; that performance limitation must remain visible.

The precise missing recognition input is clearly licensed independent naturally filmed footage with confidently visible anatomical shoulders and both wrists, a definite >=300 ms neutral segment, expected left/right raises with the opposite wrist down, and >=350 ms continuous qualifying holds. Both-arm/wrong-side controls and uncertainty intervals must be retained, labels frozen before predictions, and human validation obtained before acceptance. No candidate should be tuned on these evaluation labels.

After both runs, fresh process inspection confirmed zero emulator processes and zero task-owned ADB servers. No physical Fire TV is available. APK build and Android TV ARM64 emulator evidence do not establish Fire OS API28/32-bit loading, UVC camera access, Vega compatibility or sustained real-device latency/memory. No Fire TV readiness is claimed. There is no pending permission denial; the remaining limits are positive/usage evidence and target-hardware availability. No rights-holder contact or new legal terms were undertaken.

## Reproduction and saved work

The exact-byte audit package lives in `sidecar/fixtures/independent-natural/cohort-20261021/`; archived absolute provenance paths are intentionally unchanged. It is not a self-contained downloadable media corpus. Local raw scalar/results remain under `/Users/frank/Documents/Codex/2026-10-19/task/confidence-calibration/independent-natural-evaluation/`; clips, models, emulator data and raw logs are excluded from Git.

Completed checks: 78/78 Node regression tests, 62/62 existing Python motion/offline/video tests, six Full-harness mock evidence checks, eight append/freeze metadata checks, front-end production build, offline cached debug APK assembly and prepared-asset hash checks. Synthetic/mock checks verify harness behavior; they are not natural-motion recognition evidence. All pre-existing runtime/threshold/annotation pins remain unchanged.

Local commits before this final report: `0092f88` contract/protocol, `d70bd70` native evidence guard/trace changes, `7b4dcbb` exact frozen AI annotation/provenance copies. No push was performed.
