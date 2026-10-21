# Prospective independent natural-video evaluation contract

**PROTOCOL FROZEN before annotations or model inference; the evaluation set is not yet frozen. Preliminary AI visual comparison is authorized.** This specifies the existing behavior at commit `574ac455f4a5e09b399b2a337c5ddf873db0c98b`. It changes no runtime, default, threshold, annotation or prior result. Execution waits for immutable AI annotation/final-set freeze and privacy checks. Results remain preliminary diagnostics; human validation is still required before acceptance. AI labels must never be described as human, user-supplied or user-approved annotations.

## 1. Freeze before prediction

Use new, licensed public footage with naturally filmed movement. Before any candidate inference, freeze source/derivative hashes, license/provenance, decoded-frame map, complete chosen cohort, case roles, annotation bytes, reviewer authorship/approval and exact runtime/model/source pins. Contiguous trims are allowed only with a fixed frame map and unchanged decoded pixels/cadence; no mirroring, splicing, repeated frames or retiming creates an independent positive. Derivatives of one source share one statistical source group. Do not infer actor identity separation.

Record each label author's type (`human` or `AI`), independence from candidate predictions, and confirmation status. The user explicitly permits AI visual review for this preliminary diagnostic study without waiting for human labels. Record `authorType=AI`, `humanConfirmed=false` and AI visual provenance; no user-supplied/approved label claim follows. Freeze these annotations before inference. Human validation remains necessary before acceptance, rather than a prerequisite for this authorized preliminary execution. Preserve excluded candidates and reasons fixed before prediction; a failed model run cannot remove a case or change its labels.

## 2. Physical observations are independent of model scores

Annotate decoded **display-order** frames in unmirrored, top-left image coordinates. Left/right mean the participant's anatomical sides. Identify the same visible target within the shot; if side, target, joint or person count is uncertain, record that uncertainty. Primary single-person cases require one clearly visible participant; a model returning one pose is not proof only one physical person is present.

Mark projected shoulder/wrist centres with independently chosen uncertainty regions, visibility and reason. Let `D = hypot(LS.x−RS.x, LS.y−RS.y)` and `q_side = (shoulder.y−wrist.y)/D`. Physical geometry follows the code exactly:

| Gate | Strict condition |
| --- | --- |
| Up | `q > 0.30` |
| Down | `q < −0.20` |
| Transition | `−0.20 ≤ q ≤ 0.30` |

Certify a gate only when every plausible joint configuration in the recorded uncertainty regions satisfies it. Otherwise retain the allowed gate set/unknown; occlusion is not a fabricated point or automatically a transition. Degenerate shoulder span, uncertain anatomical side and missing visibility are separately reported. No model confidence is used to choose physical points, gates, onset or positive denominators. Without independent point annotations, gate agreement is not a point-localization accuracy claim.

Keep decoded dimensions, model working dimensions and the transform between them explicit. Existing sidecar preprocessing caps width at 640 with aspect-preserving integer height. Compare physical/model joints in one declared coordinate space. Do not normalize working-image pixels using decoded-source dimensions.

## 3. Exact classifier behavior to evaluate

The classifier accepts an observation only when its global confidence and all four joint confidences are finite and in `[0.65,1]`, all coordinates are finite and `D > 0.00001`. Adapters have additional validity rules. A non-`tracking` inference status is passed to `lost`; absent observation gives `no-person`; confidence/invalid-geometry rejection clears temporal state. These model outcomes are abstentions, not physical labels. Preserve status/reason, including one-pose rejection, invalid coordinates and weak joints.

The current OpenCV global score is the minimum of detector/pose scores; its joints use minimum visibility/presence. Optional Python Full uses `.65` as a task-admission lower bound, not an exposed detector score; joints use minimum visibility/presence. Equal numerical gates do not establish equal confidence calibration. Preserve separate raw values only if genuinely exposed/recorded; never reconstruct visibility and presence from their minimum.

The actual comparison pair also includes **Android `NativeMoveNet` through existing LiteRT**, not a Mac MoveNet backend. Its `[1,1,17,3]` output contains normalized y/x and a raw per-keypoint score. Anatomical shoulders use indices **5/6**, wrists **9/10**; the current crop transform restores coordinates to the decoded image. Each point requires finite restored x/y and score, score in `[0,1]`, restored x/y inside inclusive `[0,width]`/`[0,height]`, and raw y/x in inclusive `[0,1]`. Invalid mappings become `(0,0,0)` and must remain identifiable as rejected mappings, not valid confidence-free geometry. Observation confidence is the **minimum of the four raw joint scores**. Its `.65` baseline is uncalibrated raw-score admission; it is neither Full visibility/presence nor a demonstrated probability of correctness. `PoseGestureMachine.java` implements the same geometry/timing rules below.

Freeze the Android model ID/hash, input size and tracked versus stateless three-pass refinement explicitly; three passes of one image produce one classified observation. Freeze Python Full model/runtime, CPU IMAGE and its two-pose detection configuration separately. Keep execution, telemetry eligibility and resources separate: existing Android MoveNet runs in the app, existing Python Full runs on the Mac. Cross-host timings establish no backend speedup or Fire TV support.

| State rule | Existing semantics |
| --- | --- |
| New round | Expected side left; clear arming/neutral/hold and reset last-emission cooldown origin. |
| Neutral | Both wrists down continuously for `now−neutral_since ≥ 300 ms` arms. Neutral clears partial hold. |
| Expected raise | Expected wrist up **and** opposite wrist down. Continuous qualifying observations are required. |
| Expected wrist transitioning, opposite down | Preserve existing arming; clear hold and neutral timers. This never arms by itself or preserves partial hold. |
| Wrong side, both up or other ambiguity | Disarm and clear hold/neutral. Fresh qualifying neutral is required afterward. |
| Cooldown | While `now−last_emitted < 500 ms`, clear hold; do not backdate it. Existing arming may survive. |
| Hold | First qualifying sample starts hold; emit when `int(now−hold_since) ≥ 350`. Emission switches expected side, records cooldown and clears temporal state. |
| Gap/loss | Observation gap **>300 ms**, loss or pause resets temporal state. Exactly 300 ms does not trigger the gap reset. Backward time raises an error. |

Temporal reset alone preserves the expected side and last-emission time; `new_round` resets them. Transport resets additionally restore the acknowledged expected side. A failed left event does not delete later independently scheduled right opportunities from product-recall denominators; report sequence-dependency misses separately.

## 4. Sampling, uncertain onset and valid event time

For the existing deterministic verifier, freeze CFR footage whose decoded PTS cadence matches `i/fps` within one declared stream tick, without display-order gaps or duplicate PTS. Verify source-to-clip offset and frame count before inference. Exclude VFR/gapped inputs from this cohort before prediction; do not change the clock to accommodate them. Use the exact float FPS supplied to the verifier, preserve unrounded `i×1000/fps` and apply the code's integer truncation. A hold needs elapsed timestamp span, not `number_of_frames/fps`; the first emitting sample is the first with `int(t_i−t_start) ≥ 350`.

For each independently identified opportunity, record the last definitely non-up sample, first definitely up sample and allowed gates in between. This is an uncertain onset interval, not an invented exact physical crossing. Also certify opposite-down, preceding neutral, continuous raised support and its ending/reset boundary. Where ambiguity could change arming, expected side, cooldown or event count, retain that state uncertainty; do not force an exact expected trace.

Freeze two sampled eligibility bounds using these physical observations and the **same** temporal/expected-side rules: earliest possible eligible event `E_possible`, and first guaranteed eligible event `E_guaranteed`. The physical reference does not apply any model's confidence gate; model abstentions are evaluated against these fixed physical opportunities. For a simple already-armed continuous raise starting at sample `j`, eligibility is the first sample with `int(t_i−t_j) ≥ 350`; apply cooldown/arming constraints when relevant. Bounds must be derived before model predictions. If a guaranteed physical opportunity cannot be established, mark it indeterminate rather than manufacture a positive or negative.

- Before `E_possible`: definitely early only if **no** permitted physical/state interpretation allows the event.
- From `E_possible` up to `E_guaranteed`: onset-dependent/timing-indeterminate; not a definite pass or proven physical false trigger.
- At/after `E_guaranteed`, while the expected physical pose remains valid: definite valid timing. A later confidence-driven hold start may legitimately emit later. Report latency bounds; do not invent a maximum-delay failure after the first eligibility deadline.
- After the certified physical support/reset boundary: outside that opportunity. A late-for-opportunity event is not automatically a physical false trigger if subsequent physical observations are unknown.

Any product latency budget must be separately justified and frozen before prediction; none is introduced here. Report event-minus-onset and event-minus-first-eligibility as intervals, including sampling uncertainty, instead of one exact latency to an uncertain onset. Complex cases may remain indeterminate. Existing `evaluate_event_windows` uses ordinal, inclusive, exact-count windows and cannot express these three-way uncertainty outcomes; preserve its raw result separately. A future uncertainty-aware analysis must be reviewed before use, never relabel an old failed record.

## 5. Keep classifier, transport and UI endpoints separate

**Deterministic file verifier:** time is `frameIndex×1000/fps`, fixed through inference/observe/preview/delivery; it polls per frame, acknowledges delivery and invokes the real JS reducer. It does not exercise real browser packet validation, transit delays, rendering or the UI timer. Its normal bounds are 30 file seconds, at most 3600 decoded frames and a 512 MiB local file. Require the full frozen frame count, not merely a successful exit.

**Existing Android recorded-file route:** `NativeVideoReplay` also sends `index×1000/fps` to `PoseGestureMachine`; monotonic Android wall time separately drives leases and event freshness. Its worker owns decode/crop/LiteRT state and discards stale epochs. Semantic requests are intercepted in the WebView; this route has no Python sidecar dependency. The shared browser reducer/client still needs actual-route verification. Do not transfer the Python service's implementation details or a Mac-only result into a claim that the native route was tested.

**Actual sidecar/browser replay:** `video_worker` uses the service's monotonic clock, with observation time after inference. It skips no frames and slow inference stretches playback. Supplied `metrics.fps` is source FPS, not measured throughput. Preserve frame index/PTS and service observation time separately; never compare this wall-clock event directly with file-time windows without a declared mapping. Report inference, frame processing, transport and rendering measurements separately; no capture-to-render claim without adequate clock alignment.

Python service tokens bind client/round/revision/capture epoch. Lease is valid through 1500 ms; oldest pending event expires when age **>1500 ms**. Revision/lease/pause changes clear queued/partial work after ACK handling and restore acknowledged expected side. New rounds clear the event ledger/start left but service sequence numbers remain monotonic. Duplicate deliveries are not new events. ACK is a transport ledger endpoint, not evidence of a scored ray.

The browser polls single-flight (normally 200 ms after request completion, timeout 1200 ms), validates bounded 32 KiB packets, context/runtime and event order, and adds the full local request duration to server event age. The reducer adds local wait since receipt and rejects age **>1500 ms** before sequence consumption. Fresh wrong-side or confidence-below-.65 events consume sequence but add no ray. Unverified runtime events are diagnostic only. Preview cannot score.

The UI ends active scoring at six accepted rays or at its 30-second **RAF timer**; each timer increment is capped at 250 ms. Pauses stop that timer, preserve scored progress and require fresh neutral; source/stream changes reset/pause the round. Six rays stop active input immediately, but celebration waits for timer completion. Disconnect alone does not pause the timer. Record emitted events, delivered unique events, consumed sequences, accepted rays, ACK, rendered UI and saved-progress state independently. Public-video results do not verify a live person, and synthetic/video completion must not change saved participation.

## 6. Metrics and conservative denominators

Freeze all case/opportunity IDs and negative intervals before predictions; do not discard weak-confidence, no-person, downstream sequence misses, incomplete runs or slow cases afterward. Count physical-negative duration only where annotations and state permit a definite negative. Unknown physical time is not negative exposure.

| Metric | Definition/denominator |
| --- | --- |
| Definite timed event recall | One correct, ordered, unique event with definite valid timing per frozen definite physical opportunity / **all** such opportunities. Abstention and incomplete execution are not demonstrated successes. |
| Possible recall bound | Add only disjoint opportunities with a compatible timing-indeterminate event or unavailable execution evidence; report the bound and reason counts, never as measured success. Zero denominator is unestimable. |
| Sequence/count result | Exact frozen ordinal sequence and count, including extras; do not skip an early/extra event to obtain a passing later match. Single-right-at-left-first is a negative, not a right positive. |
| False triggers | Count all unique emitted events incompatible with every permitted physical/state interpretation. The rate per certified negative minute uses only such events inside those frozen negative intervals as its numerator. Report wrong-side/both-up/background strata and source groups. |
| Unresolved emissions | Events in uncertain onset/state/visibility regions, or otherwise unadjudicable. Report separately; neither erase them nor call them proven false triggers. |
| Timing | Definite/indeterminate/early/outside-support counts and latency bounds. No invented exact onset or post-hoc delay tolerance. |
| Abstention/coverage | On physically adjudicable frames/opportunities: no observation, non-tracking status, invalid coordinates, model admission rejection and weak-joint rejection, with overlaps declared. Also report physical annotation coverage separately. |
| Geometry | Confidence-free agreement only on valid predicted joints against independently adjudicable physical gates; report admission-conditioned agreement separately. No point accuracy without independently frozen point uncertainty. |
| Pipeline/product | Full-file coverage, emitted→delivered→ray→ACK losses, termination/censoring, UI/render and saved-progress protections, with each denominator shown. |

Use source-group counts, per-case results and raw numerators/denominators. Frames and derivative clips are correlated; do not call them independent trials or infer a general false-positive rate from zero pilot events. Preserve failure/censoring counts in primary product reporting; any completed-subset diagnostic must state its narrower denominator. A natural six-goal claim requires an independently frozen natural six-alternation expectation, timed events, six accepted rays/ACK consistency and actual UI evidence. A pilot cannot establish Fire TV, camera, demographic or deployment readiness.

## 7. Review and execution boundary

The companion `sidecar/fixtures/independent-natural/PROTOCOL.freeze.json` pins code semantics and provides the annotation/case fields. It contains no selected footage, labels, success claims or tuned thresholds. Before final set freeze, fill AI visual provenance, cohort/opportunity counts, annotation review, actual pins, clocks and uncertainty bounds; independently review consistency. Then freeze immutable bytes before the first model run. Any ambiguity-analysis implementation or latency budget is reviewed/frozen prospectively. Keep old baselines, annotations and failed results untouched. Report this cohort as preliminary AI-annotated diagnostics with human confirmation absent; do not promote it to human-validated acceptance.
