# Portable local verification

Run commands from the canonical repository root. The inference/classifier code,
model lock and core verifiers already resolve files relative to their source.
Migration changes test/tool paths and stale simulated-progress assertions.

## Recreate dependencies

Do not copy or symlink the old `sidecar/.venv`: its pip shebang points at the old
checkout and `pyvenv.cfg` records the old creation path. A symlink would keep the
old checkout as an undeclared dependency. Recreate it:

```sh
npm ci
python3.14 -m venv sidecar/.venv
sidecar/.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r sidecar/requirements-macos-arm64.lock
sidecar/.venv/bin/python sidecar/fetch_models.py
```

The Python wheel lock targets CPython 3.14, macOS 14+ and Apple Silicon. Other
platforms require separately reviewed wheel hashes; do not silently substitute
OpenCV 4. `runtime.lock.json` retains exact official wheel URLs and hashes.
For offline setup, first populate a local wheel directory from those pinned
requirements, then install with `--no-index --find-links` and `--require-hashes`.
Copying the already verified model files is also sufficient for offline use;
`models.lock.json` and startup verify their sizes and hashes. Keep the vendored
wrappers and their licenses in source control. Node dependencies must come from
`package-lock.json`; do not copy `node_modules` or the old `.toolchain` directory.

## Public media stays local

The `.gitignore` excludes model binaries, PNG/MP4 fixture media, source cache and
new verification outputs. JSON provenance, recipes, manual annotations and
sanitized historical scalar evidence remain reviewable source files.

The public source is Artem Podrez's Pexels video 6003772. The pinned original is
31,111,153 bytes, SHA256
`d891db0b4b326b5adaa07dbc6af080024ae4ed2e3e3e9c671bf8f75e39708c51`.
Its attribution and [license](https://www.pexels.com/license/) remain applicable.
No user camera imagery is needed.

```sh
# Offline copy from a user-specified existing public source:
python3 scripts/prepare-public-fixture-source.py --from-file "$PUBLIC_SOURCE"
# Or explicitly download only the fixed public URL recorded in the script:
python3 scripts/prepare-public-fixture-source.py --download
# Otherwise the helper only verifies its existing ignored cache.
python3 scripts/prepare-public-fixture-source.py

# Requires FFmpeg with libx264; uses no Python imaging dependency or pose model:
python3 scripts/rebuild-public-held-fixtures.py
```

Reconstruction writes three fixed held/cut recipes into
`sidecar/fixtures/.cache/rebuilt/`, never over the frozen manifests. Its report
compares generated hashes against the originals and records the FFmpeg version.
FFmpeg 8.1.1 reproduced all three recorded MP4 hashes exactly during migration
staging. A different encoder may produce different bytes: preserve that result
and do not rewrite the frozen original hash or describe it as an identical file.
The six-event expectation stays independent of the observed model result.

Original canonical near-face/clear media may be copied into `sidecar/fixtures/`
after their hashes match their adjacent JSON. The frontal four PNGs and three
video derivatives may be copied into `sidecar/fixtures/frontal/`; their hashes are
in the frozen v2 annotations and `bounded-frontal/encoded-media-manifest.json`.
Those local media files are deliberately ignored by Git. PNG pair verification
requires exact frozen PNG bytes; merely changing an image hash to accept another
encoding is not part of this procedure. The public-source cache is optional when
the already verified local fixtures are available.

`make-bounded-frontal-fixtures.py` retains the original additional construction
recipe. It uses the local four PNGs and defaults to the ignored source cache;
`TM_PUBLIC_SOURCE` can select a different local copy of that same pinned source.
It also creates continuous original/mirror derivatives without changing speed.
These authored held frames/reflections are not independently filmed left/right
exercise trials or proof of live-human recognition.

## Required post-copy checks

```sh
mkdir -p verification-results
npm test
npm run build
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/run.py --verify
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python -m unittest discover -s sidecar -p 'test_*.py'
node scripts/verify-simulated-progress-preservation.mjs . verification-results/progress.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python scripts/verify-decoder-contract.py --output verification-results/decoder.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_synthetic.py --output verification-results/synthetic.json
```

The full Python suite contains explicit loopback HTTP tests. For a strictly
socket-blocked run, omit those HTTP tests and report them separately; never call
that subset a full-suite result. Physical camera APIs must remain prohibited in
offline inference/tests. The decoder wrapper blocks both capture and sockets.
The 90-case VM preservation harness uses scripted nonempty progress, in-memory
storage/DOM and inert clients; it never reads a user's browser storage.

After verifying local fixture hashes, run actual file inference/game scoring:

```sh
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/clear-public-arm-fixture.mp4 --expected sidecar/fixtures/clear-public-arm-fixture.json --output verification-results/clear.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/held-public-arm-fixture.mp4 --expected sidecar/fixtures/held-public-arm-fixture.json --output verification-results/near-face.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python scripts/evaluate-frontal-pose-pairs.py --manifest sidecar/fixtures/frontal/frontal-public-selection-20261020-v2.json --manifest-sha256 2b495c38b86214060ee48f29a3d86af608b77de71c16f1b909aed0611f777c8d --output verification-results/frontal-pairs.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/frontal/bounded-frontal/frontal-held-source035.mp4 --expected sidecar/fixtures/frontal/bounded-frontal/frontal-held-source035.json --output verification-results/frontal-held.json
```

Keep the near-face **1/6 failure** visible; its nonzero exit is the preserved
expectation failure. Clear and frontal held cases previously returned six events,
six rays and six ACKs. A continuous clip without a certified expected sequence
can report consistent decoding/scoring but cannot establish an accuracy pass.

Both Playwright configs now use local `test-results/browser/` outputs and accept
`TOGETHERMOVE_BROWSER_PATH`. Mac Chrome is used if installed; otherwise Playwright
uses its managed browser. Historical external baseline tests require the explicit
`TOGETHERMOVE_BASELINE_DIR` opt-in. The mock motion project can be run with
`npm run test:e2e:mac -- --project motion`; it starts Vite. The separate live
synthetic project is skipped unless `TOGETHERMOVE_LIVE_SYNTHETIC=1` is explicitly
set, and additionally requires an intentionally started synthetic sidecar. Before
Start, the test verifies that the inactive setup packet reports a verified
synthetic source. Never enable it against a physical-camera service. The
[migration record](MIGRATION-VERIFICATION.md) lists the checks actually run from
the new checkout. Synthetic completion must leave saved progress unchanged
before and after reload; camera/manual behavior has separate mocked controls.

For native migration, limit verification to manifest/resource inspection and
host-only `MotionQuery` Java tests. Do not use the legacy emulator launcher: it
targets a fixed emulator and the old unsuffixed application ID. Cached Android
build commands in historical evidence depend on external caches and are not
portable setup instructions. No APK build, emulator, Docker or device action is
required for this migration.

## Evidence selection

`docs/verification/` contains only public-file or synthetic results. Migration
copies replace machine-specific path strings with repository-relative paths and
record the original report SHA256 in `_migration`; numerical outcomes are
unchanged. Do not copy camera observers, human test/calibration logs, browser
storage, private frames, bulk contact sheets, old patch/back-up trees, SDK/Gradle
caches, debug keys, APKs, or generated build assets into source control.

Historical result JSON is supporting evidence, not a substitute for the new-path
checks above. Keep migration results in the ignored `verification-results/`.
