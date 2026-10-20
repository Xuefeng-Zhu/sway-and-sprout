# Sway & Sprout — Mac development handoff

Every move helps your garden grow.

Canonical checkout: `~/mygit/sway-and-sprout`. Private remote:
[Xuefeng-Zhu/sway-and-sprout](https://github.com/Xuefeng-Zhu/sway-and-sprout).
Local development branch: `work/natural-motion-diagnostics`. Its starting point
is `ed4e1f5f12003319fc2cb4a93c4c203fee104adb` on `main`/`origin/main`.
Local milestones: `89a0f9c` explains calibration/readiness; `d48a3ac` binds video
acceptance and reconstruction. Inspect all local checkpoints with
`git log --oneline origin/main..HEAD`. Pushing, publication and deployment have not
been requested. The dated TogetherMove source remains an untouched backup.

## Current milestone

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
4. **Diagnosis:** a portable analyzer reproduces the current natural-video
   result and records local scalar traces. No decoder/crop defect was
   demonstrated, and no thresholds were lowered to fit a fixture.

Fresh checks and limits are recorded in
[the development verification record](verification/mac-development-20261020.json).
The earlier [migration record](MIGRATION-VERIFICATION.md) remains historical.

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

1. Obtain a licensed or user-provided local normal-motion clip with confidently
   annotated visible neutral intervals and anatomical left/right raises. Freeze
   exact bytes and annotations before inference. The current dancing clip cannot
   certify a complete alternating six-raise trial; its partial windows stay partial.
2. Run the strict full pipeline and require six expected events, six rays, ACK6,
   no saved participation, and no unexpected events. Retain failures and uncertainty.
   A reflected side is not an independently filmed opposite-side trial.
3. Recheck near-face failure, neutral/loss/recovery, pause/restart/context filters,
   stale feedback and the nonempty-progress harness after any recognition change.
4. Request a real camera test only when the user explicitly says they are ready.
   Keep it single-person and supervised, prompt raises only after Ready, keep all
   frames in memory, and stop capture when finished or participation is unavailable.

The missing complete natural-motion acceptance evidence is the remaining input
limitation. No permission request is pending. Two-player camera co-op remains
future work; it was a capability question, not an implementation request. Native
APK/Fire TV/Vega verification is also separate and was not run in this milestone.
