# Migration verification — 2026-10-20

Sway & Sprout is now developed from `~/mygit/sway-and-sprout`, with the private
repository [Xuefeng-Zhu/sway-and-sprout](https://github.com/Xuefeng-Zhu/sway-and-sprout).
The earlier dated TogetherMove export remains an unchanged backup. Its source
had no Git metadata or recoverable local history, so this repository begins with
a clean initial checkpoint. The 94-file source backup was rechecked against the
pre-copy manifest: every original size and SHA256 hash remains unchanged.

Visible web/native branding was updated. Storage key `togethermove.v1`, Android
application IDs, native bridges, WebView origin and protocol identities were
retained to preserve compatibility. Setup and verification paths now resolve
from the checkout. Dependencies were recreated here from the npm lockfile and
hash-locked macOS Python wheels; the old virtual environment and toolchains were
not copied or symlinked.

## Checks run from the new checkout

| Check | Result | Evidence scope |
|---|---|---|
| `npm test` | 49/49 pass | JavaScript unit tests |
| Full Python unittest discovery | 97/97 pass, zero skips | Includes four loopback HTTP tests; physical capture API prohibited |
| `npm run build` | Pass | Vite 6.4.1 production web build |
| `sidecar/run.py --verify` | Pass | Pinned models, zero-image DNN forwards, exact output shapes |
| `sidecar/verify_synthetic.py` | 37/37 pass | Synthetic landmarks through actual classifier/service and JS reducer |
| Progress-preservation harness | 90/90 pass | 48 video/synthetic scenarios, 12 model-reference checks, 30 camera/manual controls; in-memory storage |
| Decoder contract | 6/6 pass | Synthetic tensors/blank arrays, including all 120 output permutations; no camera/socket attempts |
| Headless Chrome motion project | 11/11 pass, zero flaky | Mocked event and preview routes, six rays, persistence/fallback, responsive bounds |
| Live synthetic browser project | 1 intentional skip | Requires `TOGETHERMOVE_LIVE_SYNTHETIC=1`; verifies inactive synthetic source before Start |
| Host-only Java `MotionQueryTest` | 23 assertions pass | No Android runtime, camera or network |
| `npm run android:sync` | Pass | Five generated files match current build; stale generated bundle removed |
| Public held-fixture reconstruction | 3/3 exact recorded hashes | Existing pinned public source, FFmpeg 8.1.1; no network download |
| Frozen frontal PNG pairs | 4/4 coarse pose gates; 6/6 repeated-frame gestures | Actual OpenCV inference; authored holds and reflected left images |

The [commit-safe scalar evidence](verification/migration-20261020.json) records
the fresh counts, fixture hashes, code hashes and provenance. Full local results,
browser diagnostics and generated files remain in ignored directories.
[The portable test plan](MIGRATION-TEST-PLAN.md) contains reproducible commands.

## Actual public-video inference and scoring

These runs decoded each 152-frame file through the pinned detector and pose
model, actual classifier/service, and actual JavaScript game reducer. They did
not use scripted gesture events. Scoring and acknowledgments matched observed
events in all three runs.

| Held public fixture | Gestures / six expected | Rays | ACK | Sequence result |
|---|---:|---:|---:|---|
| Clear | 6/6 | 6 | 6 | Pass |
| Bounded frontal | 6/6 | 6 | 6 | Pass |
| Near-face | 1/6 | 1 | 1 | Preserved failure; verifier exits 1 |

No thresholds were retuned to make these fixtures pass. The near-face failure is
kept visible. Frontal left samples are reflections of a filmed right raise;
they are not independently filmed left-arm trials. Earlier normal-speed
continuous clips produced zero events and remain supporting failure evidence.
Coarse pose gates do not establish exact landmark accuracy, natural alternating
performance, or live human recognition. No successful live user camera test is
claimed.

The camera-labelled persistence browser case uses mocked JSON for both routes;
it is a control for manual self-report behavior, not a person test. Synthetic
and video completion leave saved participation unchanged. The VM tests use
scripted existing progress and never read a user's browser storage.

## Repository and privacy boundaries

Physical capture remained off throughout migration. Public-file inference
reported zero physical camera opens, zero saved output frames and zero uploaded
frames; bounded preview caches were cleared. The mocked browser server and
headless browser were stopped after verification. No emulator, Docker, AWS or
other deployment was used.

Git excludes credentials and local configuration, virtual environments,
`node_modules`, toolchain/Gradle caches, ONNX models, licensed public PNG/MP4
fixtures and source cache, operational logs, old artifacts/APKs, browser results,
and generated web/native assets. Only project-authored interface artwork and the
licensed Gradle wrapper binary remain among the committed binaries. Vendored
Apache notices and public-media provenance/opt-in reconstruction recipes remain
in source. No project-wide open-source license was invented.

Native manifests, branding and host query parsing were checked. No clean APK
build, Fire TV device test or Vega runtime test was performed; historical native
build evidence is explicitly historical. The committed wrapper/SDK prerequisites
still require a separate native build verification.
