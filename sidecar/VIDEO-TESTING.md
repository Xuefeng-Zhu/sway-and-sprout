# Camera-free video and synthetic verification

Run every command here from the **repository root**. Install the locked default
runtime and models using the [sidecar setup](README.md) first. The workflows
below use generated landmarks or explicit local files and do not open a camera.

Public footage is excluded from Git and is not downloaded by normal startup or
unit tests. Follow the opt-in [fixture restoration recipe](../docs/MIGRATION-TEST-PLAN.md#public-media-stays-local)
and retain the [fixture provenance and notices](fixtures/README.md). Before file
inference, restore the exact canonical MP4 bytes named by the adjacent expectation
JSON. Rebuilt outputs in `.cache/rebuilt/` are not installed into those canonical
paths automatically; compare their recorded hashes before copying them.

## Synthetic regression checks

```sh
mkdir -p verification-results
sidecar/.venv/bin/python -B sidecar/verify_synthetic.py --output verification-results/synthetic.json
```

This runs deterministic landmark/event checks for calibration, alternating holds,
duplicate prevention, poor confidence, pause/reset, frame gaps, replay, stale
epochs and actual JavaScript scoring. It does not perform video pose inference.
The report remains explicitly synthetic.

## Default backend: file inference and game scoring

These commands decode the selected file, run actual detector/pose inference,
exercise the classifier/service and in-memory preview, and score events with the
JavaScript game reducer. The expectation file binds to the video's SHA256 before
inference. `--require-complete-goal` requires the full ordered six-event goal.

```sh
mkdir -p verification-results
sidecar/.venv/bin/python -B sidecar/verify_video.py sidecar/fixtures/clear-public-arm-fixture.mp4 --expected sidecar/fixtures/clear-public-arm-fixture.json --require-complete-goal --output verification-results/clear.json
```

The recorded default clear-fixture result is six events, six rays and six
acknowledgements. The preserved difficult near-face case uses its own independent
six-event expectation:

```sh
# Known expectation failure with the default backend: recorded result is 1/6.
sidecar/.venv/bin/python -B sidecar/verify_video.py sidecar/fixtures/held-public-arm-fixture.mp4 --expected sidecar/fixtures/held-public-arm-fixture.json --require-complete-goal --output verification-results/near-face.json
```

The recorded near-face result exits **1**. Preserve that result; do not change
expectations or thresholds to make it pass. Read the generated JSON for observed
and expected gestures, gate counts, calibration, scoring and ACK reconciliation.
Reports contain preview delivery counts, not preview image bytes. Keep new
reports in ignored `verification-results/`; a local rerun does not replace a
dated committed evidence record.

`--seconds` limits deterministic file-time verification to at most 30 seconds
(default 30). `--annotation` accepts a hash-bound partial annotation instead of
`--expected`; partial coverage cannot establish the full goal. With no full
expectation, consistent decoding/scoring is an observed pipeline result rather
than an accuracy pass. See [natural-video verification](../docs/NATURAL-VIDEO-VERIFICATION.md)
for the stricter bindings and preserved natural-motion failures.

## Visible file replay in the app

Start the service in terminal 1:

```sh
sidecar/.venv/bin/python -B sidecar/run.py --video sidecar/fixtures/clear-public-arm-fixture.mp4
```

Start Vite in terminal 2, also from the repository root:

```sh
npm run dev
```

Open `http://127.0.0.1:4173`, then choose **Catch the Sunshine → Camera sunshine →
Start**. This existing input control connects to the running service. Its `video`
provenance must display **VIDEO REPLAY · NO CAMERA**. The bounded preview shows
file frames and markers. Replay rays never save garden participation, including
through confirmation and reload. Pause/end clears the preview. Stop both terminal
processes with Ctrl-C when finished.

File decoding explicitly uses FFmpeg; URLs, device indexes and files over
512 MiB are rejected. Ordinary web file replay uses the normal 30-second round.
The separate native diagnostic entry `input=video-verification` gives Sunshine
replay a 120-second UI budget; it does not change this verifier's 30-second limit.
See the [native evaluation report](../docs/INDEPENDENT-NATURAL-EVALUATION-20261021.md)
for its separately recorded runs.

Offline verification uses frame-index/file-FPS time. Visible replay uses host
wall time and file cadence, retaining every frame and slowing down when inference
is slower than the source. UI replay therefore checks transport/timing separately.
Held frames, cuts and disclosed reflections do not establish natural transitions,
independently filmed left/right trials, seated framing or live-user accuracy.

## Optional Full CPU IMAGE backend

The separately pinned Google Full backend improved the same constructed near-face
fixture from one to six events/rays/ACKs in the dated
[Full verification report](../docs/MEDIAPIPE-FULL-VERIFICATION.md). It is opt-in,
file-only and remains separate from the default OpenCV environment. Restore its
isolated `.toolchain/mediapipe-venv` and pinned model using that report before
running these commands:

```sh
mkdir -p verification-results
python3 scripts/run-local-pose.py verify sidecar/fixtures/held-public-arm-fixture.mp4 --expected sidecar/fixtures/held-public-arm-fixture.json --require-complete-goal --output verification-results/full-nearface.json
```

For visible replay, use the same Vite terminal and app steps above, with this
service command instead of the default one:

```sh
python3 scripts/run-local-pose.py replay sidecar/fixtures/held-public-arm-fixture.mp4
```

The macOS launcher enforces external-network denial while allowing the loopback
app bridge. It offers no camera mode, dependency installation or automatic model
downloads, and refuses an unsandboxed fallback. Direct backend invocation bypasses
that launcher policy, so use the launcher for these operational commands.
`--seconds`, expectation and report options apply to `verify` only; `replay`
uses the selected file cadence. Stop it with Ctrl-C after use.

Constructed-fixture improvement does not establish natural alternating-six or
live-user success, or justify promoting Full to the native runtime. Later
[natural-benefit findings](../docs/PYTHON-FULL-NATURAL-BENEFIT.md) and the
[independent natural evaluation](../docs/INDEPENDENT-NATURAL-EVALUATION-20261021.md)
preserve the outstanding positive-evidence and timing limits.
