# Quality and verification

Use this guide to choose a check and understand what its result proves. All
commands below run from the repository root. Setup is in
[Getting started](GETTING-STARTED.md); the [portable test plan](MIGRATION-TEST-PLAN.md)
contains the locked Python setup and public-fixture restoration recipe.

## Choose the verification layer

| Layer | Entry point | What it establishes |
|---|---|---|
| JavaScript unit and harness checks | `npm test` | Model/storage normalization, packet/runtime validation, calibration/preview, scoring and native evidence guards. Native CLI tests use mock child processes. |
| Web production build | `npm run build` | Vite can bundle the app; this does not run a browser or Android. |
| Manual app browser regression | `npm run test:e2e -- tests/browser/app.spec.js` | Real browser navigation, full timed manual garden, pause, reload persistence, remote keys, mobile bounds and reduced motion. |
| Mock motion browser regression | `npm run test:e2e:mac -- --project motion` | Rendered motion/preview behavior with intercepted HTTP responses; no inference or person is involved. |
| Python unit suite | Locked `sidecar/.venv`, command below | Classifier, inference adapters, service and verifier behavior; includes loopback HTTP tests. |
| Pinned runtime smoke | `npm run motion:verify` | Model hashes, loading and zero-image DNN forwards/output shapes; no recognition accuracy. |
| Synthetic pipeline | `sidecar/verify_synthetic.py` | Deterministic landmarks through the classifier/service and JavaScript reducer; no camera or video pose inference. |
| Real HTTP synthetic browser regression | Explicit opt-in below | Browser → Vite → Python service → UI scoring and unchanged saved participation, using synthetic landmarks. |
| Public-file inference | [Video verification](../sidecar/VIDEO-TESTING.md) | Decoding, model inference and scoring for the exact local file and frozen expectation. Constructed holds/reflections have limited scope. |
| Native recorded-video diagnostics | [Native video report](NATIVE-VIDEO-VERIFICATION.md) | Separately recorded Android emulator execution; no physical Fire TV, camera or live-user accuracy claim. |

Run the required web checks after app changes:

```sh
npm test
npm run build
```

Test counts belong to a particular revision and run. Read the command's fresh
summary rather than treating the historical seven-test MVP result below as the
current suite size. `npm run android:sync` copies the built web assets into the
Android source tree; it does not compile, install or launch an APK.

## Browser checks

The default Playwright config includes manual app and mock motion tests. The Mac
config has separate `motion` and opt-in `live-synthetic` projects; it does not
include `app.spec.js`. Both start Vite automatically. The full manual garden
test waits for three real 30-second rounds, so allow roughly two minutes.

```sh
# Manual app flow and mock motion routes; live-synthetic is skipped by default:
npm run test:e2e

# Focused mock motion checks on Mac:
npm run test:e2e:mac -- --project motion
```

Playwright needs a browser installed. The Mac config uses local Google Chrome
when available; both configs accept
`TOGETHERMOVE_BROWSER_PATH=/absolute/path/to/a/trusted/browser`. Otherwise they
use Playwright's managed Chromium. Browser provisioning is separate from
`npm ci`. Reports and failure artifacts go to ignored `test-results/browser/`;
the manual app tests also write ignored screenshots under `artifacts/`.

If you choose Playwright-managed Chromium, provision it explicitly with
`npx playwright install chromium`. This is a separate browser download; using an
existing trusted executable avoids that setup step.

To exercise the real local relay, intentionally start a synthetic service in
one terminal, then run the opt-in browser project in another:

```sh
# Terminal 1; stop with Ctrl-C after the test:
npm run motion:synthetic
```

```sh
# Terminal 2:
TOGETHERMOVE_LIVE_SYNTHETIC=1 npm run test:e2e:mac -- --project live-synthetic
```

The test checks an inactive packet for verified `source: synthetic` before
Start. Use only a deliberately started synthetic service. The word `live` in
this test name means a real HTTP relay, not live camera capture.

## Sidecar and progress checks

After restoring the locked Python environment, run the
[capture-prohibited full-suite command](MIGRATION-TEST-PLAN.md#required-post-copy-checks).

The full suite includes loopback HTTP tests. If the execution environment blocks
sockets, report omitted tests and the subset result separately. Keep physical
capture prohibited during offline verification; neither a camera smoke nor
`--camera` is required for these checks.

For explicit synthetic, decoder and saved-progress regressions:

```sh
mkdir -p verification-results
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_synthetic.py --output verification-results/synthetic.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python scripts/verify-decoder-contract.py --output verification-results/decoder.json
node scripts/verify-simulated-progress-preservation.mjs . verification-results/progress.json
```

The preservation harness uses an in-memory DOM/storage model and scripted
nonempty progress. It does not read a user's browser storage. Retain its
video/synthetic preservation cases and separate camera/manual controls.
Simulated rounds must preserve saved participation through automatic completion,
confirmation and reload.

Public-file checks need separately restored, hash-verified local media and models.
Their commands and the expected nonzero near-face failure are in the
[portable plan](MIGRATION-TEST-PLAN.md). Do not widen expectations or change frozen
hashes to turn a failed fixture into a pass.

## Read the evidence with its limits

| Record | Established scope | Remaining limit |
|---|---|---|
| [Migration verification, 2026-10-20](MIGRATION-VERIFICATION.md) | New-checkout unit/browser/runtime/synthetic checks and exact held-file inference | Historical counts; held poses and reflected left samples do not prove natural alternating motion |
| [Optional Full backend](MEDIAPIPE-FULL-VERIFICATION.md) | The constructed near-face fixture improved from 1 to 6 events/rays/ACKs | File-only diagnostic backend; no general or live-user recognition acceptance |
| [Native video verification, 2026-10-20](NATIVE-VIDEO-VERIFICATION.md) | Android API 34 ARM64 emulator inference and one constructed frontal six-ray result | Clear/near-face failures remain; no Fire OS, ARMv7 runtime, UVC or Vega verification |
| [Independent natural comparison, 2026-10-21](INDEPENDENT-NATURAL-EVALUATION-20261021.md) | Complete 120-second UI reruns for two Pexels files, including completion/reload/cleanup | Zero definite positive opportunities; observed zero events do not estimate recall or establish positive recognition |

The latest rerun retains the original incomplete 30-second runs. Its 120-second
duration applies only to explicit Sunshine `input=video-verification` diagnostics;
ordinary authored rounds remain 30 seconds. Neither an ACK nor a completed file
alone proves recognition. Human review of independent natural-positive labels,
live-user performance and physical Fire TV/Vega acceptance remain outstanding.

The independent report also preserves a DVIDS provenance correction: its local
diagnostic footage has uncleared redistribution eligibility. Do not describe the
entire cohort as cleared public-domain acceptance media.

## Historical web MVP — October 15, 2026

The following records describe the original cloud environment and early native
continuation. Their screenshots, SDK caches and operational logs are not fresh
checkout prerequisites. Later migration and native diagnostic reports above
provide separate evidence; the unsuccessful API 30 boot attempt below does not
invalidate the later API 34 emulator runs.

### Checks recorded at the time

- Production Vite bundle and Android asset sync succeeded.
- Seven Node model tests covered authored challenge structure, saved-state filtering and idempotence, phase bounds and directional focus.
- Playwright used actual Chromium on the cloud VM for full manual gameplay and screenshots, without injecting a success state or fake timer.
- The cloud GUI browser independently opened the app and Enter moved from home into setup with the correct primary focus.
- The native build continuation verified Android compilation; actual Fire TV runtime remained unverified.

### Visual review

Compared `artifacts/design-concept.png` with actual `artifacts/home-1920.png` using image inspection. Also inspected mobile and paused gameplay screenshots.

Five principal comparisons: (1) left-aligned large cream heading, (2) lime pill CTA and cream focus ring, (3) right-side original three-flower botanical scene, (4) three numbered lower challenge cards, (5) dark forest palette and lower remote hints. The above-the-fold headline, supporting line and CTA copy match. Functional status and safety copy were added deliberately.

Material fixes: explicit two-line card titles prevent symbol overlap; mobile navigation wraps rather than clipping; pause hint uses supported ASCII glyphs; synchronous initial focus eliminates a rapid-key race. Native 1920×1080 and 390×844 browser viewports are covered. Image assets are decorative, while all app content and controls remain native HTML.

Intentional differences from concept: independent generated background has different flower geometry; system typography is less rounded; simple Unicode challenge symbols replace detailed card illustrations; reduced card ornamentation keeps ten-foot text clear. This is a reviewed interpretation, **not a pixel-perfect claim**. Real TV viewing distance, safe-area behavior, VoiceView, old WebView versions, performance and remote hardware behavior still need device QA.

### Environment friction

The initial shell sandbox prevented Chromium sockets; an execution escalation failed before launch because its filesystem mount setup failed. The same tests then ran through the authorized cloud desktop terminal against the shared source, without changing permissions or reading restricted files. The separate GUI browser could reach the app once the server ran in that VM context.

### Web-MVP run

7/7 unit tests passed. 3/3 browser tests passed (about 1.7 minutes). Full timed garden progression used Enter for start, confirmation and continuation; D-pad, Back, pause, variant switching and reduced motion were checked separately. Final screenshots: home-1920.png, home-mobile.png, paused-1920.png, celebration-1920.png. Actual GUI browser independently verified Enter start, Back pause and Right/Right/Enter return to garden. The full suite reported no page errors. Production build and asset sync succeeded. `android-preflight.sh` explicitly reports missing Gradle; native build remains pending.


### Native build continuation

`assembleDebug` and `lintDebug` succeeded using official Android SDK tools, Gradle 8.9 and Java 21. APK signature verification and manifest inspection succeeded. The manifest exposes a Leanback launcher and requests no network/camera/microphone permission. Fixed launcher bitmap density and Android backup compatibility metadata. Remaining intentional lint warnings concern fixed landscape orientation (TV target) and enabling JavaScript (required for locally bundled app; external navigation blocked, no native bridge). Compilation is not runtime evidence.

### Native runtime attempt outcome

The official Android TV API 30 image and emulator were installed after separate Preview-license approval. This VM lacks KVM/CPU virtualization. Two cold-boot attempts (two cores, then one core after kernel diagnostics) did not reach boot-complete within their 10-minute observation windows. The one-core attempt reached system-server initialization. No APK installation, launch or native screenshot was reached. This does not establish either app success or app failure on Android TV/Fire OS. Next runtime test requires a practical accelerated emulator environment or an actual Fire TV.
