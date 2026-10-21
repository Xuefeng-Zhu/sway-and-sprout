# Sway & Sprout

Every move helps your garden grow.

A living-room movement garden: three short moments, seated or standing, with
self-reported manual participation and optional local pose recognition for
**Catch the Sunshine**. Comfortable waves, reaches, stretches and sways can
contribute; ordinary play does not prescribe a side order or pose hold. No account
is required. Camera frames stay in memory on the Mac; the app does not save or
upload them. Optional web garden backup is disabled unless explicitly configured.

This is the canonical development repository, normally checked out at `~/mygit/sway-and-sprout`. The earlier TogetherMove export remains an unchanged backup outside this repository. The private repository is [Xuefeng-Zhu/sway-and-sprout](https://github.com/Xuefeng-Zhu/sway-and-sprout).

The movement-first candidate is `work/activity-progression`; use that branch
instead of the older default `main` for this experience. Current milestones and
limits are in the [Mac development handoff](docs/DEVELOPMENT-HANDOFF.md).
A permitted human-motion excerpt now produces temporary garden credit through
OpenCV and actual in-memory game code; [exact evidence and limits](docs/MOTION-TO-GARDEN-20261021.md).
Natural-motion reliability and live recognition remain unverified. Older
strict-pose, model-comparison and recorded-video results are diagnostic history;
they do not define ordinary gameplay requirements.

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

[Historical migration verification](docs/MIGRATION-TEST-PLAN.md) includes earlier
media recipes. Those recipes are not current license clearance: do not newly
download or analyze Pexels, uncleared DVIDS or unlicensed YouTube inputs. Normal
startup and unit tests do not download footage. Camera capture is a separate
opt-in command; do not start it merely to run verification. Current functional
evidence must name its exact permitted input and distinguish real inference,
generated landmarks and manual input.

## Optional garden backup

The web backup client and AWS-oriented API support explicit Save, Restore and
Delete of confirmed garden summaries. No frames, pose coordinates or active
counts leave the device. Restore merges saved blooms without creating a current
visit or harvest; local play works offline. There is no configured endpoint in
the normal build and no automatic upload.

The proposed deployment is API Gateway HTTP API → Lambda → DynamoDB. It has
**not been deployed**. The existing Android outbound-request restriction and
release permissions remain; native cloud backup is disabled. See
[behavior, cost proposal and required deployment approval](docs/AWS-GARDEN-BACKUP.md)
and [local API tests/template](cloud/README.md). Running source locally does not
fulfil the competition's running-AWS requirement.

## Evidence and limits

The browser and windowed Android TV emulator completed the manual garden
journey, including growth, confirmation, harvest, replay and saved-garden reload.
The native run passed 32 layout checks. These are automated self-report inputs,
not observed human movement. [Native result and preserved failures](docs/NATIVE-JOURNEY-20261021.md).

The latest generated-video diagnostic APK was prepared but has not run. Historical
windowed replay accepted only 8/188 frames; the cause remains unresolved. No
physical Fire TV or reliable live-human recognition is established. Old strict
diagnostics retain their original outcomes and expectations. Synthetic/video
credit cannot become saved human participation.

## Compatibility and native source

The product is **Sway & Sprout**. Internal `togethermove.v1` storage, `com.togethermove.tv` / `.motion` Android IDs, JavaScript bridges, WebView origin, and protocol identifiers deliberately retain their original names. Branding alone must not discard existing progress or break native integration.

`android/` contains the Fire OS host source and renamed launcher assets. The committed Gradle wrapper is 8.9 with AGP 8.7.3 and SDK 35 requirements. Historical APK/build evidence is not proof of a clean native build here. Migration validation does not start an emulator, Docker, or a physical camera, and does not deploy anything. See [native source notes](android/README-motion.md); physical Fire TV/Vega runtime verification remains pending.

## Repository contents

- `src/`, `public/`: app code and project-authored/generated interface assets.
- `sidecar/`: local inference, classifiers, locked dependencies, fixtures' provenance, and tests.
- `scripts/`, `tests/`: portable setup/verification and browser checks.
- `docs/`: current setup plus clearly scoped historical and public/synthetic evidence.

Owner-authored code and documentation use the [MIT license](LICENSE), copyright
2026 Xuefeng Zhu. Third-party code, weights and media retain their own terms; see
[license scope and notices](THIRD-PARTY-NOTICES.md). The repository remains private. Model and fixture media remain excluded from Git; historical provenance
does not authorize new use of restricted footage. There are no required `.env`
secrets; `.env.example` contains comments only. Do not put cloud capability keys,
personal browser state, APKs or operational logs into source control.
