# Sway & Sprout

A cooperative living-room movement garden: three playful moments, seated or standing, with manual participation and optional local pose recognition for **Catch the Sunshine**. No accounts or cloud runtime. Camera frames stay in memory on the Mac; the app does not save or upload them.

This is the canonical development repository, normally checked out at `~/mygit/sway-and-sprout`. The earlier TogetherMove export remains an unchanged backup outside this repository. The private repository is [Xuefeng-Zhu/sway-and-sprout](https://github.com/Xuefeng-Zhu/sway-and-sprout).

## Start on this Mac

Node 20.19+ or 22.12+, npm, and a modern browser are required. Install from the lockfile:

```sh
npm ci
npm run dev
# http://127.0.0.1:4173
npm test
npm run build
```

Manual play requires no camera, Python, or credentials. Arrow keys move focus, Enter selects, Escape/Back pauses, and Space toggles pause. Touch and mouse work too. Saved garden progress remains on the same browser/device.

## Local motion tools

The tested inference runtime is CPython 3.14 on macOS 14+ Apple Silicon, with hash-locked OpenCV 5.0.0.93 and NumPy 2.5.4 wheels. Recreate the environment in each checkout:

```sh
python3.14 -m venv sidecar/.venv
sidecar/.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r sidecar/requirements-macos-arm64.lock
sidecar/.venv/bin/python sidecar/fetch_models.py
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/run.py --verify
```

Model downloads are pinned by size/hash in `models.lock.json`. The model files, virtual environment, caches, generated builds, and licensed public test media stay local and are ignored by Git. Vendored upstream wrappers and their Apache licenses remain committed.

[Portable verification and public-fixture preparation](docs/MIGRATION-TEST-PLAN.md) includes opt-in download/rebuild instructions, synthetic checks, pose-pair checks, and actual video inference. Normal startup and unit tests do not download stock footage. [Video replay instructions](sidecar/VIDEO-TESTING.md) explain the explicitly labeled camera-free replay mode. Camera capture is a separate opt-in command; do not start it merely to run verification.

## Evidence and limits

See [the migration verification record](docs/MIGRATION-VERIFICATION.md) for checks run from this checkout. The project retains the calibration/arming fix, stale capture-epoch rejection, bounded same-frame preview, explicit input provenance, and guards preventing synthetic/video rays from saving human participation.

High-margin held public poses have produced six alternating gestures and six rays. The preserved near-face fixture produces only one of six expected gestures. Left reflections are disclosed; they are not independently filmed left-arm trials. Normal continuous alternating performance and live user recognition remain unverified. Synthetic tests, public-video inference, and human results are kept distinct.

## Compatibility and native source

The product is **Sway & Sprout**. Internal `togethermove.v1` storage, `com.togethermove.tv` / `.motion` Android IDs, JavaScript bridges, WebView origin, and protocol identifiers deliberately retain their original names. Branding alone must not discard existing progress or break native integration.

`android/` contains the Fire OS host source and renamed launcher assets. The committed Gradle wrapper is 8.9 with AGP 8.7.3 and SDK 35 requirements. Historical APK/build evidence is not proof of a clean native build here. Migration validation does not start an emulator, Docker, or a physical camera, and does not deploy anything. See [native source notes](android/README-motion.md); physical Fire TV/Vega runtime verification remains pending.

## Repository contents

- `src/`, `public/`: app code and project-authored/generated interface assets.
- `sidecar/`: local inference, classifiers, locked dependencies, fixtures' provenance, and tests.
- `scripts/`, `tests/`: portable setup/verification and browser checks.
- `docs/`: current setup plus clearly scoped historical and public/synthetic evidence.

No project-wide open-source license has been selected. Preserve third-party license notices. Public fixture media are excluded from Git; retain their [Pexels provenance and license](sidecar/fixtures/README.md) when preparing them locally. There are no required `.env` secrets; `.env.example` contains comments only.
