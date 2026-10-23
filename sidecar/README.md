# Sway & Sprout local motion sidecar

The optional sidecar supplies local gesture input for **Catch the Sunshine**.
One player raises their anatomical left arm, rests both arms, raises their right
arm, and repeats for six alternating rays. Seated and standing play use the same
shoulder-relative rules. Manual play works without Python or a camera.

Start with the [web setup guide](../docs/GETTING-STARTED.md). For camera-free file
checks, use [video and synthetic verification](VIDEO-TESTING.md). The
[documentation index](../docs/README.md) links to dated evidence and its limits.

## Install the default Mac runtime

Run **all commands in this document from the repository root**. The locked runtime
targets CPython 3.14, macOS 14+ and Apple Silicon. It uses
`opencv-python-headless==5.0.0.93` (`cv2.__version__ == '5.0.0'`) and
`numpy==2.5.4`. No Docker, GPU runtime or credentials are needed.

```sh
python3.14 -m venv sidecar/.venv
sidecar/.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r sidecar/requirements-macos-arm64.lock
# Explicitly restore pinned models; this may download missing model files.
sidecar/.venv/bin/python sidecar/fetch_models.py
sidecar/.venv/bin/python -B sidecar/run.py --verify
```

Recreate the virtual environment in each checkout rather than copying or
symlinking another checkout's environment. Other platforms need separately
reviewed wheel hashes; `requirements.txt` is a version list, while the
platform-specific lockfile is the reproducible installation input.

The [runtime lock](runtime.lock.json) records wheel URLs and hashes.
[models.lock.json](models.lock.json) pins model bytes and unchanged official
wrappers to OpenCV Zoo commit `47534e27c9851bb1128ccc0102f1145e27f23f98`.
Their Apache-2.0 notices remain under `vendor/`. Model binaries, virtual
environments, caches and generated reports remain ignored by Git. Setup does
not download public test footage.

Startup verifies model/wrapper hashes and runs both DNNs on generated zero
images before reporting `runtime.verified: true`. The local adapter matches
unique output shapes for OpenCV 5 without changing vendored Zoo code. A verified
runtime establishes model loading and execution; human recognition remains a
separate acceptance check.

## Choose an input mode

Each service invocation selects exactly one input mode. The default web bridge
expects the sidecar at `127.0.0.1:8765`.

| Mode | Command from the repository root | Input and scope |
|---|---|---|
| Runtime check | `sidecar/.venv/bin/python -B sidecar/run.py --verify` | Generated zero images; exits after checking DNN execution |
| Synthetic demo | `npm run motion:synthetic` | Deterministic landmarks through the real gesture state machine; no camera |
| File replay | `sidecar/.venv/bin/python -B sidecar/run.py --video /absolute/path/to/local-file.mp4` | Explicit local file through FFmpeg and real inference; no camera |
| Camera play | `npm run motion:camera` | Opt-in device 0; capture only during an actively polled game round |

Even synthetic service mode initializes the default verified pose runtime, so
it needs the installed dependencies and locked models. It does not infer on
camera or file frames. File input must exist, be at most 512 MiB and have a
finite 1–120 fps time base; URLs and device indexes are not accepted as files.

### Connect the web app

Start a chosen synthetic or file service in one terminal, then start the app in
a second terminal from the same repository root:

```sh
npm run dev
```

Open `http://127.0.0.1:4173`, choose **Catch the Sunshine → Camera sunshine → Start**.
The existing Camera sunshine control connects to the selected sidecar source.
Check the displayed provenance: **SYNTHETIC TEST · NO CAMERA** for synthetic input,
or **VIDEO REPLAY · NO CAMERA** for a file. Both modes must leave saved garden
participation unchanged, including after confirmation and reload.

The fixed Vite proxy is configured for the development server. Serving `dist/`
alone does not provide the Python motion bridge. Although `run.py` has a `--port`
option, changing it also requires a matching bridge configuration; use the
default for these instructions. Stop each terminal process with Ctrl-C.

### Explicit camera use

Start camera mode only when the user is ready for a supervised camera session.
Face the Mac camera with both shoulders and wrists visible, hands clear of the
face, and headroom for raised arms. Input is **not mirrored**. Rest both arms
below the shoulders and wait for **Ready** before following the indicated side.
The rules are prototype entertainment controls, not a clinical movement measure.

`npm run motion:camera` selects camera 0. To choose another device explicitly,
use `sidecar/.venv/bin/python -B sidecar/run.py --camera INDEX` with an index
from 0 to 7. Capture begins only while a client polls an active round. Pause,
leaving the game or a 1,500 ms poll-lease timeout releases capture. Resume
requires arms at rest before another raise. macOS may ask for camera permission
for the terminal running Python; unlock the Mac and use the normal OS prompt.

A separate smoke check opens the camera immediately and prints aggregate frame
counts, timings and detector statuses:

```sh
# Explicit opt-in capture; omit this during offline verification.
sidecar/.venv/bin/python -B sidecar/run.py --camera-smoke 0 --seconds 5
```

`--seconds` accepts 1–30 seconds after opening. An OS permission prompt or device
open can still block, so unattended execution needs a bounded parent process.
Smoke success does not establish alternating human gestures or six game rays.

## Verify without a camera

After restoring the runtime and models:

```sh
sidecar/.venv/bin/python -B -m unittest discover -s sidecar -p 'test_*.py'
mkdir -p verification-results
sidecar/.venv/bin/python -B sidecar/verify_synthetic.py --output verification-results/synthetic.json
```

The Python suite includes loopback HTTP tests; a socket-blocked subset must be
reported separately. Use the [portable verification plan](../docs/MIGRATION-TEST-PLAN.md)
for capture-prohibited checks, progress preservation and opt-in public-fixture
restoration. [File verification](VIDEO-TESTING.md) explains the preserved default
near-face 1/6 failure and the separately isolated, opt-in Full backend.

## Event protocol and gameplay rules

The local HTTP service exposes:

```text
GET /motion/events?clientId=<uuid>&roundId=<uuid>&revision=<integer>&active=0|1&mode=seated|standing&after=<seq>
GET /motion/preview?<same query fields>
```

Events carry a per-process `streamId`, explicit source, verified runtime, control
identity, status, expected anatomical side, hold duration and bounded scalar
metrics. At most 64 semantic events are returned. Each has a sequence, round ID,
gesture, confidence and server-computed age; pending events expire after
1,500 ms. Query size, fields, UUIDs, safe integers, host, origin and local peer
are constrained. Responses are `no-store`.

`metrics.calibration` supplies optional bounded reason/gate labels, dwell/hold
durations, confidence labels and freshness. After 300 ms without a new valid
frame, readiness is masked. Polling cannot arm the classifier or accumulate
neutral time. The state machine uses 300 ms neutral, 350 ms hold and 500 ms
cooldown. Both wrists first rest below their shoulders. Only the expected wrist
raised above its shoulder while the other stays down can begin a hold. The
expected wrist may cross the shoulder transition band after neutral, but no
partial hold survives it. Wrong-side raises, both arms up, low confidence,
disappearance and frame gaps over 300 ms break the hold and require neutral.
The default backend requires exactly one detected person and checks pose,
visibility, presence and frame bounds.

`after` acknowledges accepted game events. Only acknowledged event progress
survives pause, revision and lease resets; a bounded semantic ledger reconciles
late acknowledgements. Round changes reset the expected side to left. A new
stream or source resets and pauses the input round. Takeover retires the old
client, retaining at most 32 retired IDs; restart the service if that bound is
reached. These are semantic events rather than generic Enter/key presses.

Preview reads return one bounded, short-lived JPEG from the same capture and
inference result. They cannot activate capture, acknowledge events or extend
the lease. Only the current active client/round/revision receives an image.
Pause, completion, leaving, errors and lease expiry clear it. Synthetic mode
returns no image. There is no camera-start, upload or arbitrary proxy endpoint.

## Privacy and evidence limits

Camera frames stay in memory; the sidecar does not record, write or upload them.
The live preview transfers the latest small JPEG over Mac loopback to the local
browser without persistent image storage. Semantic packets and camera service
logs contain no images or landmark coordinates. Separate public-file analysis
can write scalar coordinates for selected fixtures; its output does not establish
a live-user test. Keep personal frames and camera logs out of source control.

Default browser development uses the fixed Vite proxy. The Android debug host's
optional proxy uses `10.0.2.2:8765`, an emulator host alias rather than a physical
Fire TV address. Android recorded-video inference has its own implementation
and evidence in the [native video report](../docs/NATIVE-VIDEO-VERIFICATION.md).
Do not infer native behavior from this Mac sidecar.

Natural alternating-six recognition and live-user performance remain unverified.
Lighting, occlusion, seated framing and camera placement still need acceptance
evidence. Constructed poses, synthetic landmarks, model startup and generic
Android emulator checks have distinct scopes. Fire OS/Vega runtime and competition
eligibility remain separate unresolved questions.

Pinned upstream references: [OpenCV wheel](https://pypi.org/project/opencv-python-headless/5.0.0.93/),
[person detector](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/person_detection_mediapipe),
[pose estimator](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/pose_estimation_mediapipe),
[emulator networking](https://developer.android.com/studio/run/emulator-networking-address).
