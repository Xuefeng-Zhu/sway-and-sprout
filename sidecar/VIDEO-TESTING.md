# Offline video and synthetic verification

Run these commands from the Sway & Sprout project root. None opens the physical
camera. File decoding uses an explicit FFmpeg backend and an existing local path;
device numbers and URLs are rejected.

```sh
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_synthetic.py --output /tmp/togethermove-synthetic.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/clear-public-arm-fixture.mp4 --expected sidecar/fixtures/clear-public-arm-fixture.json --output /tmp/togethermove-clear-video.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/held-public-arm-fixture.mp4 --expected sidecar/fixtures/held-public-arm-fixture.json --output /tmp/togethermove-near-face-video.json
```

The clear fixture currently passes six expected gestures and six game rays. The
near-face fixture deliberately retains its independent expectation of six; its
observed one-ray result makes the verifier exit1. Do not edit expectations or
thresholds to hide that failure. Both reports contain observed/expected gestures,
gate counts, calibration, scalar preview delivery counts and actual JavaScript
game-reducer output. Preview image bytes are not saved in reports.

`verify_synthetic.py` separately labels37 deterministic landmark/event checks.
They cover calibration, alternating holds, duplicate prevention, poor confidence,
pause/reset, frame gaps, replay, stale epochs and scoring. Those checks do not run
video pose inference and are not human verification.

For a visible app replay, start the sidecar with the file source and start Vite
in a second terminal:

```sh
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/run.py --video sidecar/fixtures/clear-public-arm-fixture.mp4
npm run dev
```

Choose Catch the Sunshine → Camera sunshine → Start. This existing input-mode
control connects to the local service; the service's explicit `video` provenance
labels the app **VIDEO REPLAY · NO CAMERA**. The same bounded preview route shows
file frames and markers. Replay rays never save garden participation, including
through confirmation. Pause/end clears the preview; stop both terminal processes
when finished. No `--camera` or `--camera-smoke` command is needed for this workflow.

Offline verifier time is deterministic frame-index/file-FPS time. Visible replay
uses host wall time and file cadence, so it separately checks transport timing.
Held/cut imagery does not test natural transitions, seated framing, occlusion,
different people, or real-user camera accuracy. See `fixtures/README.md` for
provenance and the preserved difficult case.
