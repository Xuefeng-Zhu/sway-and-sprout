# Sway & Sprout — Mac development handoff

Every move helps your garden grow.

Canonical checkout: `~/mygit/sway-and-sprout`. Private remote:
[Xuefeng-Zhu/sway-and-sprout](https://github.com/Xuefeng-Zhu/sway-and-sprout).
Local development branch: `work/natural-motion-diagnostics`. Its starting point
is `ed4e1f5f12003319fc2cb4a93c4c203fee104adb` on `main`/`origin/main`.
Local milestones: `89a0f9c` explains calibration/readiness; `d48a3ac` binds video
acceptance and reconstruction; `25b9de9` records the initial diagnosis. The next
local milestone `b1b049e` adds authored event timing and generic bound-file
traces. Inspect all local checkpoints with
`git log --oneline origin/main..HEAD`. Pushing, publication and deployment have not
been requested. The dated TogetherMove source remains an untouched backup.

## Current native Android milestone — 2026-10-20

[Native verification](NATIVE-VIDEO-VERIFICATION.md) now provides a pinned LiteRT1.4.2 / MoveNet Lightning UINT8 debug path that decodes public videos and performs inference, gesture timing and event delivery inside the Android app process, with the Mac sidecar off. Debug and release APKs build offline; the debug APK contains real ARMv7 ELF32 libraries, while the exercised guest is Android TV API34 ARM64. The release remains free of ML/media and network/camera permission. Existing identifiers, default OpenCV and optional Mac Full behavior are preserved.

The user has no physical Fire TV. Fire OS7/API28/armeabi-v7a is a provisional reference, not a verified device. Seven actual emulator replays completed1,680 frames, with source labels and unchanged participation. All3 positive controls failed0/6; all1,680 frames failed the unchanged four-joint confidence gate. Input/output fingerprints vary, so this is not fixed/black input or stale output; exact official preprocessing/crop parity remains unverified. Negative0 counts are weak because none calibrated under confidence. Do not promote this candidate or call it Fire TV ready.

Fresh checks:65 JavaScript tests/build,381 host Java assertions,8 asset preparation checks,2 fake-ADB guard checks and5 real emulator lifecycle checks. Pause/resume and native cleanup work. The portable runner correctly returns exit1 for a positive recognition failure. Emulator, isolated ADB and all inference services are stopped; no physical camera, push, production deployment or upload occurred. There is no permission blocker. Vega/capture and sustained hardware acceptance are unresolved; do not ask again for a model screenshot when no hardware exists.

[The controlled model comparison](MODEL-CANDIDATE-COMPARISON.md), committed at2b34976, rejects Heavy and RTMPose as replacements: Heavy's accepted overhead run stays233.567ms<350ms at~3× Full inference cost; RTMPose overhead geometry improves but loses Full's near-face6/6 control to0. Retain Full as the optional Mac diagnostic baseline. Next useful recognition work is exact official preprocessing/crop/loss-recovery diagnosis and independently annotated natural positives, preserving all frozen controls and thresholds. The native scalar record distinguishes actual model failure, generated event/scoring tests and hardware limitations.

## Current optional-model milestone

Local commit `8afc8db` integrates the official Google Full IMAGE backend for explicit local videos.
It improves the same near-face constructed fixture from **1 to6 actual model
recognition events, game rays and ACKs**, while clear/frontal remain6 and the
right-only/both-up natural negatives remain0. The default OpenCV Zoo model,
classifier thresholds and camera command remain unchanged. Use the separately
pinned environment and OS network-denying launcher in
[the Full verification report](MEDIAPIPE-FULL-VERIFICATION.md); the optional model
is rejected for camera/synthetic modes. No capture was performed.

The official-reference audit and exact-tensor OpenCV/ONNX Runtime comparison
locate the overhead problem in raw outputs for the present model/crop. Full
only matches6/16 certified overhead frames (longest66.733ms); Heavy costs~69ms
and matches9/16; Apple Vision has a433.767ms correct overhead run but fails both
near-face raised controls. Neither alternative is integrated. Full VIDEO mode
regresses the cut controls, so only stateless IMAGE is available.

The canonical14-case CLI comparison and actual Chrome app replay passed their
scoped expectations (default near-face remains an explicit exit1). Chrome
displayed six rays with ACK6 and unchanged isolated saved progress. Fresh checks:
156 Python,55 JavaScript,90 progress,37 synthetic and six decoder checks, plus
production build, all passed. Final counts and evidence hashes are in
[the scalar record](verification/full-image-20261020.json). Full inference costs
~23.2ms/frame versus~22.3ms default on this Mac. Initial optional-environment
startup can be slow; the measured cold command was44.8s including3.8s processing.
All models/media/venvs/raw traces remain ignored. No natural alternating-six,
independently filmed left-positive or live-user result is claimed. A suitable
rights-cleared natural left/right clip remains the next acceptance input. There
is no permission blocker and no push, deployment or upload occurred.

## Prior calibration and natural-control milestone

The calibration and verification gaps below have demonstrated fixes. A general
single-person natural-motion reliability fix has **not** been demonstrated.
Physical camera capture stayed off. No live user recognition is claimed.

1. **Calibration feedback:** the service explains visibility, neutral dwell,
   wrong side, both hands raised, hold and rest states. The browser validates
   these optional bounded fields and distinguishes visible markers from Ready.
   Preview text no longer independently tells someone to raise an arm.
2. **Freshness:** an earned Ready could remain visible while HTTP polling
   continued without new frames. Diagnostics now become stale after 300 ms;
   polling masks readiness without changing classifier history. A fresh actual
   observation still performs the existing gap reset. Malformed optional
   diagnostics cannot authorize a raise or disconnect valid semantic input.
3. **Verification contract:** expected sequences are bound to the selected
   media's SHA256 before inference. `--require-complete-goal` requires an
   independently expected alternating six-event sequence, six scored rays and
   matching ACKs. Consistent zero-event transport remains observation-only.
4. **Initial diagnosis:** the dancing-video analyzer and independent inverse-ROI
   checks found no decoder defect in those inputs. No thresholds were lowered.
5. **New natural control:** public-domain DVIDS551039 was independently annotated
   before inference. The 450-frame right-only clip correctly scores zero under
   the left-first policy, but its certified overhead window matches 0/16 poses.
   A cropped wrist/hand context is now demonstrated on this separate input.
   Fixed 1.25 expansion recovers only 2/16 frames and regresses near-face
   recognition from 1 event to 0, so it was rejected. Recognition code is unchanged.
6. **Timed acceptance:** optional event windows are SHA-bound and validated
   before inference; early/late events fail even when order, scoring and ACK match.
   The generic analyzer records bounded numeric traces for any bound local file.

Fresh checks and limits are recorded in
[the development verification record](verification/mac-development-20261020.json).
The earlier [migration record](MIGRATION-VERIFICATION.md) remains historical.
The [prior natural-control report](NATURAL-CONTROL-VERIFICATION.md) and
[scalar record](verification/natural-control-20261020.json) contain the latest
licensed footage, frozen truth, rejected experiment and verification results.
Fresh checks: 137 Python tests, 55 JavaScript tests, 90 saved-progress checks,
37 synthetic-landmark checks, six decoder checks and production build passed.
The earlier 13 browser checks were not rerun because frontend/service/recognition
code did not change. Full numeric evidence is ignored under
`verification-results/natural-controls-20261020/`.

## Start and test

Run from the canonical root. `npm run dev` starts the web app at
`http://127.0.0.1:4173`; manual play needs no sidecar or camera. Recreate missing
dependencies using [the locked setup](MIGRATION-TEST-PLAN.md), rather than copying
an old virtual environment. No credentials, Docker or emulator are needed.

```sh
npm test
npm run build
mkdir -p verification-results
node scripts/verify-simulated-progress-preservation.mjs . verification-results/progress.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python scripts/verify-decoder-contract.py --output verification-results/decoder.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_synthetic.py --output verification-results/synthetic.json
npm run test:e2e:mac -- --project motion
```

The Python suite includes loopback HTTP tests. This invocation prohibits capture
while retaining the entire suite; it requires the pinned local OpenCV install:

```sh
sidecar/.venv/bin/python -B - <<'PY'
import cv2, sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path('sidecar').resolve()))
with mock.patch.object(cv2, 'VideoCapture', side_effect=AssertionError('Capture prohibited in unit tests')):
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('sidecar', 'test_*.py'))
raise SystemExit(not result.wasSuccessful())
PY
```

For the separately labelled synthetic HTTP demo, run `npm run motion:synthetic`
in one terminal and the app in another. The sidecar does not open a camera.
Choose Catch the Sunshine → Camera sunshine to connect to that synthetic source;
the badge must read `SYNTHETIC TEST · NO CAMERA`. The optional real-relay browser
test is `TOGETHERMOVE_LIVE_SYNTHETIC=1 npm run test:e2e:mac -- --project live-synthetic`.
It verifies an inactive, verified synthetic packet before Start. Stop the
sidecar with Ctrl-C after the demo. Simulated sessions never save participation.

## Video acceptance and diagnosis

[The strict video commands](NATURAL-VIDEO-VERIFICATION.md) include public-source
preparation and exact fixture bindings. All licensed media and model binaries
stay ignored. Frozen annotations are expectations or partial coverage, never
generated from the inference result being evaluated.

| Input | Actual gestures / rays / ACK | Interpretation |
|---|---|---|
| Clear held public poses | 6 / 6 / 6 | Selected constructed fixture goal verified |
| Frontal held public poses | 6 / 6 / 6 | Selected constructed fixture goal verified |
| Near-face held public poses | 1 / 1 / 1 | Preserved six-event expectation failure |
| Normal-speed original / reflection | 0 / 0 / 0 each | Complete natural goal unverified; strict acceptance exits 1 |
| New normal-speed filmed right-only control | 0 / 0 / 0 | Correct wrong-side negative; certified overhead tracking fails 0/16 |

Repeat the frame-level diagnosis without capture:

```sh
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python scripts/analyze-natural-motion.py --output verification-results/natural-motion
```

The [concrete diagnosis](NATURAL-MOTION-DIAGNOSIS.md) distinguishes model predictions
from manual annotations. The original's first raised arm is anatomical right
while the game expects left. The reflection loses frame 0 to wrist confidence
0.637489; the remaining initial neutral span is 266.667 ms, short of 300 ms.
All 319 frames have one person and a successful pose result. Wrist reliability,
not frame gaps, limits calibration. The ROI inverse passed independent synthetic
geometry checks; there is no temporal ROI tracker. Full-frame detection and pose
inference run independently per frame. The word `tracking` is a status label.

## Architecture and invariants

- `src/main.js` owns screens, the 30-second round and local garden persistence.
  `src/model.js` normalizes `{completed, sessions}` under `togethermove.v1`.
- `src/motion.js` validates bounded packets, current context/source/stream,
  event age, alternation and sequence. `src/calibration.js` validates optional
  diagnostics; it never creates events. `src/motion-view.js` renders guidance.
- `sidecar/run.py` selects explicit synthetic/video/camera modes. `inference.py`
  verifies pinned models/wrappers, resizes consistently and returns anatomical
  shoulders/wrists. `motion.py` implements the single-person temporal state machine.
- `sidecar/service.py` owns loopback leases, capture epochs, ACK reconciliation
  and one bounded in-memory preview. Preview reads cannot start capture or renew
  the active event-poll lease. Pause, source/context change and loss discard partial holds.
  Diagnostic age measures time since the last processed observation; preview
  expiry separately checks the capture timestamp. Neither certifies landmark accuracy.
- `sidecar/verify_video.py` exercises decode → detector → pose → classifier/service
  → events → actual JS reducer. File time is deterministic; preview frames are
  exercised only in memory. `analyze-natural-motion.py` is public-file diagnosis,
  not a camera logger.

Keep the current prototype defaults: confidence 0.65, neutral 300 ms, hold 350 ms,
cooldown 500 ms, maximum frame gap 300 ms. Changing them needs independent evidence.
Preserve storage/native IDs, pause/revision/ACK behavior and explicit provenance.
Video/synthetic completion and fallback must preserve existing saved progress,
including nonempty gardens and session counts. Tests use isolated scripted
storage; they do not read or clear the user's browser progress.

## Next acceptance checks

1. The new licensed control supplies independent neutral/right-up truth, but no
   filmed positive left/right alternation. Obtain that remaining natural positive
   with confidently visible neutral/hold intervals; freeze bytes and annotations
   before inference. The dancing clip and right-only control cannot certify six
   alternating raises. Keep their partial/negative scopes explicit.
2. Run the strict full pipeline and require six expected events, six rays, ACK6,
   no saved participation, and no unexpected events. Retain failures and uncertainty.
   A reflected side is not an independently filmed opposite-side trial.
3. Recheck near-face failure, neutral/loss/recovery, pause/restart/context filters,
   stale feedback and the nonempty-progress harness after any recognition change.
4. Keep the physical camera off for this continuation. A future supervised
   single-person test requires new explicit user readiness. Prompt raises only
   after Ready, keep all frames in memory, and stop capture when finished or
   participation is unavailable.

Both the missing complete natural-motion positive and demonstrated overhead
tracking failure remain unresolved. The global crop candidate was rejected; do
not adopt it or infer success from a consistent zero-event game negative.
No permission request is pending. Two-player camera co-op remains
future work; it was a capability question, not an implementation request. Native
APK/Fire TV/Vega verification is also separate and was not run in this milestone.
