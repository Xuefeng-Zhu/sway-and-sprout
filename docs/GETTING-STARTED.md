# Getting started

Start with manual play, then add only the motion or verification tools you need.
All commands below run from the repository root, normally
`~/mygit/sway-and-sprout`. For the full guide/report map, use the
[documentation index](README.md).

## 1. Run manual play

You need Node.js 20.19+ or 22.12+, npm, and a modern browser. No Python, camera,
credentials, Docker, or emulator is required.

```sh
cd ~/mygit/sway-and-sprout
npm ci
npm run dev
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173). Choose a moment and a seated
or standing position, keep **Manual play** selected for sunshine, and start.
Each ordinary round lasts 30 seconds. At the end, **We joined in** saves your
self-reported participation. Skipping a moment does not complete it.

Arrow keys move focus, Enter selects, and mouse/touch select the same buttons.
Escape, Backspace, or native Back pauses a playing round; Space toggles pause.
Switching position during play pauses the round. Returning to the garden keeps
saved participation; **Grow together again** starts a new garden.

Progress uses browser local storage under the compatibility key
`togethermove.v1`. Another browser/profile or origin has separate storage. If
storage is unavailable, the app reports that progress could not be saved.

Stop Vite with **Ctrl-C**. To inspect a production bundle locally:

```sh
npm run build
npm run preview
```

## 2. Run the app checks

```sh
npm test
npm run build
mkdir -p verification-results
node scripts/verify-simulated-progress-preservation.mjs . verification-results/progress.json
```

`npm test` runs Node tests, not a browser or a pose model. The preservation
harness uses isolated scripted progress and storage; it does not read a user's
saved garden. New reports belong in ignored `verification-results/`.

For browser checks, use an installed trusted browser or an already installed
Playwright browser. The Mac config selects local Google Chrome when available;
`TOGETHERMOVE_BROWSER_PATH` can explicitly select another executable.

```sh
# Mocked motion routes; no Python service or camera is needed.
npm run test:e2e:mac -- --project motion

# Manual app flow plus mocked motion checks; synthetic relay stays opt-in.
npm run test:e2e
```

Both configs start Vite if needed and reuse an existing server on port 4173.
Use a server from this checkout. Browser reports go to `test-results/browser/`.
See [Quality and verification](QUALITY.md) for what each test layer establishes
and the separate browser-install prerequisite.

## 3. Add the optional Mac motion runtime

The pinned Python environment targets **CPython 3.14, macOS 14+, Apple Silicon**.
The web app is independent of this platform-specific runtime. Other Python
versions/platforms need separately reviewed wheel hashes; keep the locked
OpenCV 5 setup intact.

These commands explicitly install dependencies and download the pinned default
model files. They do not download public videos or open a camera.

```sh
python3.14 -m venv sidecar/.venv
sidecar/.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r sidecar/requirements-macos-arm64.lock
sidecar/.venv/bin/python sidecar/fetch_models.py
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/run.py --verify
```

Create a fresh virtual environment per checkout instead of copying or symlinking
one. Startup verifies locked model/wrapper bytes and DNN execution on generated
zero images. `runtime.verified: true` establishes that runtime check, not human
gesture accuracy. Keep models and the virtual environment ignored.

For the offline restore recipe and guarded Python checks, follow
[Portable local verification](MIGRATION-TEST-PLAN.md). The optional Google Full
backend uses a separate environment and a network-restricted, file-only launcher;
follow its [verification report](MEDIAPIPE-FULL-VERIFICATION.md#restore-and-exercise-locally).

## 4. Try labelled synthetic sunshine

After restoring the default motion runtime, start the synthetic service:

```sh
npm run motion:synthetic
```

In a second terminal, run `npm run dev`. Open the app, select **Catch the
sunshine → Camera sunshine → Start**, and check that the input badge reads
**SYNTHETIC TEST · NO CAMERA**. The input selector connects to the service; the
service's provenance identifies the source. Synthetic landmarks pass through
the gesture classifier and HTTP bridge without opening a camera. They can
produce rays, but completion must leave the saved garden unchanged.

The separately opted-in browser check uses that real synthetic HTTP service:

```sh
TOGETHERMOVE_LIVE_SYNTHETIC=1 npm run test:e2e:mac -- --project live-synthetic
```

The test checks an inactive, verified synthetic packet before Start. Run it only
against the intentionally started synthetic sidecar. Its use of real HTTP does
not make it a human-camera test. Stop the sidecar and Vite with **Ctrl-C** when
finished.

## 5. Choose another input deliberately

| Input | Next guide | What to expect |
| --- | --- | --- |
| Local video file | [Video testing](../sidecar/VIDEO-TESTING.md) | Explicit file path, **VIDEO REPLAY · NO CAMERA**, unchanged saved garden; public fixtures require opt-in preparation. |
| Physical Mac camera | [Sidecar guide](../sidecar/README.md) | Explicit camera command and OS permission, one person, in-memory preview; live recognition is an outstanding acceptance check. |
| Native Android recorded video | [Native source guide](../android/README-motion.md) · [Latest evaluation](INDEPENDENT-NATURAL-EVALUATION-20261021.md) | Separate debug assets/toolchain and emulator evidence; no physical Fire TV/Vega claim. |

Ordinary manual, camera, synthetic, and file-replay rounds use 30 seconds. The
explicit `input=video-verification` Sunshine motion-input branch uses a
120-second diagnostic round for native replay. That exception does not extend
ordinary file replay or change recognition thresholds. Do not use it to turn
old 30-second failures into passes.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `npm ci` fails | Check Node/npm versions and use the committed `package-lock.json`. Keep any local error output out of Git. |
| Port 4173 is occupied | Stop the known development/preview server with Ctrl-C, or confirm the existing one belongs to this checkout. Vite's dev port is strict. |
| Motion service is unavailable | Manual play still works. Start the intended source separately on loopback port 8765; the app's dev proxy uses that fixed port. |
| Runtime/model verification fails | Use the matching locked Python environment and restore pinned bytes with `fetch_models.py`. Preserve hash failures; do not edit a lock to accept a mismatch. |
| A video fixture is missing | Follow the explicit [public-media recipe](MIGRATION-TEST-PLAN.md#public-media-stays-local). A fresh clone intentionally contains no fixture MP4/PNG files. |
| Near-face default verification exits 1 | This is the retained **1/6** expectation failure, not an environment problem. Read the [Full comparison](MEDIAPIPE-FULL-VERIFICATION.md). |
| Playwright cannot find a browser | Set `TOGETHERMOVE_BROWSER_PATH` to a trusted local executable, use Mac Chrome, or explicitly install the matching Playwright browser as described in [Quality](QUALITY.md). |
| Hands are visible but Ready is absent | Markers alone do not arm recognition. Both wrists/shoulders must pass confidence and neutral-dwell rules; see the [motion rules](../sidecar/README.md). |

No `.env` file is required. Optional test variables are shell settings in
[`.env.example`](../.env.example). Keep credentials, private frames, browser
storage, model binaries, media, and operational logs out of source control.
