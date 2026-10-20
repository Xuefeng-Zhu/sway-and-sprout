# Sway & Sprout local motion sidecar

This is new prototype work on the original exported TogetherMove. Only **Catch the
Sunshine** has camera gameplay: one player raises their anatomical left arm, rests
both arms, raises their right arm, and repeats. Seated and standing use the same
shoulder-relative rules. Face the Mac camera with both shoulders and wrists visible;
leave headroom for raised hands. Input is **not mirrored**. This is a coarse arm
gesture game, not a clinical movement measure. Competition reuse/eligibility is
unconfirmed.

## Reproduce this Mac runtime

Run from this directory. The verified installation uses CPython3.14, Apple Silicon,
`opencv-python-headless==5.0.0.93` (actual `cv2.__version__ == '5.0.0'`) and
`numpy==2.5.4`. No Docker, system installation or GPU runtime is needed.

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-macos-arm64.lock
.venv/bin/python fetch_models.py
.venv/bin/python run.py --verify
.venv/bin/python -B -m unittest discover -p 'test_*.py'
```

`requirements-macos-arm64.lock` pins **wheel SHA256**, for CPython3.14/macOS14+ arm64.
`runtime.lock.json` records their official PyPI URLs. The models and unchanged
official inference wrappers are locked to OpenCV Zoo commit
`47534e27c9851bb1128ccc0102f1145e27f23f98`, with all file SHA256 values in
`models.lock.json`. Their Apache2.0 licenses are preserved under `vendor/`.
`fetch_models.py` downloads only those immutable URLs and checks bytes and hashes.

The OpenCV5 graph engine changed the person detector output ordering. The adapter
in `inference.py` matches exact, unique output shapes for **both** networks; it does
not alter the vendored Zoo code or substitute OpenCV4. Startup loads the verified
models and performs actual DNN forward passes on generated zero images before it
reports `runtime.verified:true`. This verifies loading, execution and output shapes;
it does **not** verify recognition accuracy on a human.

## Run and stop

No camera:

```sh
.venv/bin/python run.py --synthetic
```

This sends deterministic synthetic landmarks through the real gesture state machine.
All responses are labelled `source:'synthetic'`; the game must visibly show synthetic
test mode. It is useful for transport, pause and game feedback checks, and is not
camera verification.

Camera mode is for a later supervised test after the user explicitly says they
are ready. Offline development keeps it off. To explicitly allow this local
camera for that active game:

```sh
.venv/bin/python run.py --camera 0
```

From the repository root in a separate terminal, start the web app with `npm run dev`, choose **Catch the Sunshine**,
select camera input, and start the round. The service opens the camera only while a
client is actively polling an active round. Pause, leaving the game or a1500ms poll
lease timeout releases the camera. Resume requires arms at rest before another
raise. The camera may need macOS permission for the terminal running Python.
Unlock the Mac and accept that permission normally; this code bypasses no controls.
Ctrl+C stops the service and releases capture.

A separate explicit smoke command captures for1–30 seconds after camera opening:

```sh
.venv/bin/python run.py --camera-smoke 0 --seconds 5
```

It prints aggregate frame count, timings and detector statuses only. Opening a
camera can be blocked by OS permission/lock state; when running unattended, supervise
this command with a bounded parent process (e.g. a15s subprocess timeout). A
successful smoke does not prove alternating human gestures; a human must perform
those and confirm the corresponding six game rays.

## Event protocol and gameplay rules

Both HTTP endpoints are on loopback `127.0.0.1:8765`. Semantic events use
`GET /motion/events?clientId=<uuid>&roundId=<uuid>&revision=<integer>&active=0|1&mode=seated|standing&after=<seq>`.
The user-requested `/motion/preview` endpoint uses the same six query fields and
returns a bounded, short-lived JPEG plus wrist visibility/confidence feedback.
It uses the same camera capture and inference result, never a second camera.
Preview reads cannot activate capture, acknowledge events or extend its lease.
Only the current active client/round/revision can receive an image. Pausing,
leaving, completion, capture errors or lease expiry clears the cached image.
Synthetic mode returns no camera image. There is no camera-start, upload or
arbitrary proxy endpoint. Browser
requests go through the app's same-origin Vite proxy. The Android native wrapper
proxies only this fixed route to `10.0.2.2:8765`, the emulator's Mac host alias.
This address is not a physical FireTV route.

Packets carry a per-process `streamId`, explicit source, verified runtime, control
identity, status, expected anatomical side, hold duration, numeric/boolean metrics
and at most64 semantic events. Optional `metrics.calibration` contains only bounded
reason/gate labels, dwell/hold durations, confidence labels and frame freshness.
After300ms without a new valid frame, readiness is masked. Polling never arms the
classifier or accumulates neutral time. Each event has a global sequence, round ID, gesture,
confidence and server-computed age. Pending events expire after1500ms. Query size,
field count, UUIDs, safe integers, host, origin and local peer are constrained;
responses are `no-store`. A single local client has a1500ms lease. A takeover
retires the old client (at most32 retained IDs); restart the sidecar if that bound
is reached. A new stream/source requires a new paused game round.

The temporal state machine defaults to350ms hold,300ms neutral and500ms cooldown.
Both wrists must first rest below their shoulders. The expected wrist may then cross the shoulder-height transition band while the other wrist stays down; this never arms a gesture without prior neutral and never preserves partial hold time. Only the expected wrist raised
above its shoulder, with the other wrist down, can begin a hold. Both arms up,
wrong-side raises, low confidence, disappearance and frame gaps over300ms break
the hold and require neutral. OpenCV detects exactly one person and checks pose,
visibility, presence and frame bounds. All thresholds are prototype defaults,
not values validated with a user population.

The `after` field acknowledges accepted game events. Only acknowledged progress
survives pause/revision/lease resets. A bounded semantic ledger reconciles late
acknowledgements, avoiding left/right drift when a response crosses a pause.
Round changes reset to left. No action is converted to generic Enter or a keypress.

## Privacy and present limits

Camera frames are never recorded, written to disk or uploaded. The requested
live framing preview transfers only the latest small JPEG over Mac loopback to
the local browser, with no recording or persistent browser storage. Images are
cleared on pause, end and manual mode. The semantic event endpoint and live
camera service logs contain no images or landmark coordinates. The separate
public-file analyzer can write scalar coordinates for its pinned licensed fixtures;
it cannot open a camera and does not log user movement. No personal images are used for
external inference. Manual input and pause remain available in the game. The
existing APK has not been updated with the Mac-browser preview.

Deterministic landmark tests and zero-image DNN execution are separate from actual
human camera verification. Performance on real people, occlusion, lighting, camera
placement and seated framing remains to be measured. Generic Android TV emulator
testing is not actual FireOS testing or contest eligibility evidence.

Official upstream references:

- https://pypi.org/project/opencv-python-headless/5.0.0.93/
- https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/person_detection_mediapipe
- https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/pose_estimation_mediapipe
- https://developer.android.com/studio/run/emulator-networking-address

Current commands, evidence and acceptance limits: [Mac development handoff](../docs/DEVELOPMENT-HANDOFF.md).
