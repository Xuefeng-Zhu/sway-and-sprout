# Movement-first gameplay — 2026-10-21

The goal is to encourage comfortable movement. Ordinary camera play now uses an
explicit `activity` policy: small raises, waves, stretches and torso lean can
contribute without alternating anatomical sides, crossing shoulder height or
holding a prescribed pose. Manual play remains available.

## Implementation

Python `sidecar/activity.py` and Java `ActivityMachine` apply the same pure rules.
Each arm uses its trusted wrist relative to its shoulder; torso lean uses trusted
shoulder and hip midpoints. Existing model outputs already contain the hip points.
One weak or missing wrist does not block another reliable feature. No model,
runtime, confidence calibration or native MediaPipe build was introduced.

Coordinates are normalized by shoulder width, smoothed over 100 ms and compared
with movement anchors. A 0.025-width deadband rejects small jitter. One feature
must accumulate 0.20 widths of path in a 1.5-second window, across at least three
movement samples spanning 250 ms. Each required joint needs confidence >=0.65;
these scores are admission gates, not correctness probabilities. Static holds
stop contributing. Missing tracking, implausible jumps and gaps above 300 ms
clear the affected temporal evidence. A one-second cooldown limits emitted
`activity` events; the frontend still caps each round at six rays.

The optional seventh control field is `policy=activity|strict`. Legacy six-field
requests retain strict behavior. Policy is bound into request/response context;
changing it requires a new round. Activity ACK processing retains sequencing and
freshness but removes anatomical alternation. The 1,500 ms control lease and event
TTL, pause/reset handling, stale-result rejection and duplicate protection remain.

Ordinary gameplay selects activity. `?policy=strict` retains the strict diagnostic
experience. Native `?input=video-verification` remains strict unless explicitly
combined with `&policy=activity`; old fixture expectations are not evaluated as
activity expectations. Synthetic and replay participation still cannot alter the
saved garden. Historical strict tests, annotations and failed results are intact.

## Replay investigation and repairs

The earlier visible replay accepted only 8/188 frames; it is still a failed
coverage result. Its APK and first eight landmark rows matched the successful
headless run, while accepted-frame elapsed time rose from about 265 ms to
6,868 ms. There were 28 observed packet gaps above the 1.5-second lease. This
supports scheduling/transport starvation and repeated stale-frame rejection;
it does not identify the underlying cause of the broad slowdown.

The existing animation clock credits at most 250 ms per callback. Its behavior is
preserved and tested; `window.togetherMoveTiming()` now returns primitive credited,
wall, stalled and callback counters. Native packets include control epoch, poll
gap, lease-break count, discard reason and skipped stale inference count. These
diagnostics neither inject time nor drive scoring.

Review found that a frame invalidated during decoding still incurred all three
inference passes. The same frame guard now runs immediately after decode and
again after inference. Early rejection recycles the bitmap without inference;
final rejection still handles pauses/expiry during inference. Per-attempt stats
prevent an old frame from contaminating replacement-round counters. This avoids
known wasted work; no emulator throughput improvement is claimed.

## Verification actually completed

- 97 Node tests and the production frontend build passed.
- 168 Python tests passed, using modified worktree code, existing pinned model
  resources, synthetic/blank tensors, mocks and loopback HTTP. External networking
  was denied by the existing OS policy. No camera or natural media was used.
- 11 shared synthetic traces produced identical Java/Python event timestamps and
  matching scores through the real JS reducer. Small left/right, both-arm and
  torso movement scored; static, jitter, camera translation, tracking loss,
  implausible jumps and timestamp-gap cases did not. Duplicate events and the
  six-ray cap were checked.
- 90 actual-main-module VM checks preserved simulated/replay progress and manual
  participation behavior. Storage and clients were in memory.
- Two mocked Chrome checks passed: activity six-ray play and retained strict
  calibration. All motion/preview routes were mocked; the test server was stopped.
- All 19 main/debug Java sources compiled against existing Android 35 and
  hash-verified cached AARs. Host checks passed 381 pose, 350 crop, 32 query/policy
  and 41 fake-clock lease assertions. This did not build or execute an APK.
- Independent review found no blocking issue, including after the early guard fix.

[Structured results and source hashes](verification/movement-first-20261021.json)
record the successful checks, earlier failed setup attempts and their resolution.
The reproducible synthetic parity and compile-only helpers are
`scripts/verify-activity-parity.py` and `scripts/verify-native-source.py`; both
require explicit existing local toolchain paths and never fetch dependencies.

## Remaining limits

These are provisional functional rules, not measured natural-video accuracy.
Synthetic camera translation and jitter do not establish robustness to arbitrary
camera rotation or real-world pose noise. Pexels and other natural footage were
not downloaded or analyzed for this change. Any future validation corpus needs
appropriate permission for its intended processing; old labels are not a new
clearance decision.

The updated code has not been packaged into an APK or executed in an emulator.
The historical visible-run slowdown remains unresolved and has not been hidden by
a longer round or weaker lease. Physical Fire TV hardware is unavailable, so no
hardware performance or human-camera claim is made. No paid service, installation,
upload, push or deployment occurred, and SayGo/shared port 8000 were untouched.
