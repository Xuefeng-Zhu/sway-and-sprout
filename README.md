# Sway & Sprout

**Every move helps your garden grow.**

A cooperative living-room movement garden with three short moments: **Wake the
garden**, **Catch the sunshine**, and **Make some rain**. Play seated or standing,
follow the prompts, and confirm your own participation to grow a shared garden.
Manual play needs no camera, account, Python runtime, or credentials. Progress
stays in the same browser on the same device.

Catch the sunshine also has an optional, single-person local motion prototype.
It supports explicitly selected synthetic input, local-file replay, or camera
capture. Camera frames stay in memory and are not saved or uploaded. Natural
alternating gestures and live-user recognition remain unverified.

## Quick start

Use Node.js 20.19+ or 22.12+, npm, and a modern browser. From the repository root:

```sh
npm ci
npm run dev
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173), select a garden moment, choose
seated or standing, and start. Ordinary rounds last 30 seconds. Manual completion
is self-reported; choose **We joined in** to save that moment.

| Control | Action |
| --- | --- |
| Arrow keys | Move focus |
| Enter | Select the focused button |
| Escape / Backspace / native Back | Pause during play; go back on other screens |
| Space / media play-pause | Toggle pause during play |
| Mouse or touch | Select visible controls |

To check the app and preview its production bundle:

```sh
npm test
npm run build
npm run preview
```

Stop a development or preview server with **Ctrl-C** before starting another on
port 4173. See [Getting started](docs/GETTING-STARTED.md) for optional motion setup,
browser checks, and troubleshooting.

## Choose your path

| Goal | Read |
| --- | --- |
| Run the app or a labelled synthetic demo | [Getting started](docs/GETTING-STARTED.md) |
| Find a guide or verification report | [Documentation index](docs/README.md) |
| Understand screens, input, and persistence | [Architecture](docs/ARCHITECTURE.md) |
| Select checks and interpret their results | [Quality and verification](docs/QUALITY.md) |
| Recreate the pinned Python runtime and public fixtures | [Portable local verification](docs/MIGRATION-TEST-PLAN.md) |
| Work on local pose inference or file replay | [Sidecar guide](sidecar/README.md) · [Video testing](sidecar/VIDEO-TESTING.md) |
| Continue the current motion investigation | [Development handoff](docs/DEVELOPMENT-HANDOFF.md) |
| Inspect the Android host and debug modes | [Native source guide](android/README-motion.md) |

## Motion evidence and limits

Keep these verification layers separate when reporting results:

| Layer | Recorded result and limit |
| --- | --- |
| Synthetic landmarks and mocked input | Exercise state, transport, UI, and saved-progress guards; do not measure recognition accuracy. |
| Constructed public-video poses | Default OpenCV backend produces six gestures/rays on selected clear and frontal fixtures, but retains the near-face **1/6 failure**. The opt-in Full IMAGE backend produces six on that same near-face fixture. [Full comparison](docs/MEDIAPIPE-FULL-VERIFICATION.md). |
| Independent natural footage | The latest cohort has **zero definite positive opportunities**; positive recognition benefit cannot be estimated. [Evaluation and limits](docs/INDEPENDENT-NATURAL-EVALUATION-20261021.md). |
| Native diagnostic replay | Two previously interrupted clips complete under the explicit **120-second** diagnostic round. The original 30-second failures remain recorded; replay completion does not establish recognition accuracy or Fire TV performance. [Replay evidence](docs/verification/replay-duration-120-20261021.json). |
| Live users and target hardware | Natural alternating-six recognition, live-user performance, and physical Fire TV/Vega runtime remain unverified. |

Synthetic and video results never add saved participation, including after
confirmation or reload. Held frames, cuts, and reflected left poses are disclosed
in fixture provenance; they are not independently filmed left/right trials.
Camera capture is a separate opt-in workflow in the sidecar guide.

## Repository map

| Path | Purpose |
| --- | --- |
| [`src/`](src/) · [`public/`](public/) | JavaScript/CSS app and local interface artwork |
| [`sidecar/`](sidecar/) | Local pose backends, gesture classifier, loopback service, fixtures, and Python tests |
| [`tests/`](tests/) · [`scripts/`](scripts/) | Node/browser checks, fixture preparation, and verification tools |
| [`android/`](android/) | Fire OS host source and debug-only native video diagnostics |
| [`docs/`](docs/README.md) | Guides, architecture, dated reports, and scoped evidence |

This is the canonical development repository; the earlier dated TogetherMove
export is an unchanged backup outside it. The visible product name is
**Sway & Sprout**. Compatibility identifiers deliberately retain `togethermove.v1`,
`com.togethermove.tv` / `.motion`, bridge names, WebView origin, and local protocol
names so branding changes do not discard progress or break integrations.

## Assets and licensing

Project-authored source and documentation are licensed under the [MIT License](LICENSE).
Original project artwork is included with the project. Third-party components
retain their existing licenses; preserve their committed notices and
[source/asset provenance](docs/PROVENANCE.md). Model
binaries, virtual environments, public test media, build outputs, credentials,
and operational logs stay ignored. Restore public media only through the
[explicit preparation recipe](docs/MIGRATION-TEST-PLAN.md#public-media-stays-local)
and retain each fixture's attribution and license. There are no required `.env`
secrets; [`.env.example`](.env.example) documents optional browser-test settings.
