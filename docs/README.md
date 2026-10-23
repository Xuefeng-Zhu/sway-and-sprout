# Sway & Sprout documentation

Start with [Getting started](GETTING-STARTED.md) to run manual play or a labelled
synthetic demo. Commands assume the repository root unless a guide says otherwise.
The [project README](../README.md) gives the product overview and controls.

## Development guides

| Guide | Use it for |
| --- | --- |
| [Getting started](GETTING-STARTED.md) | Web setup, controls, local progress, optional motion setup, and troubleshooting |
| [Architecture](ARCHITECTURE.md) | Module responsibilities, input flow, local storage, and native/debug boundaries |
| [Quality and verification](QUALITY.md) | Choosing tests and separating mocked, synthetic, video, browser, and device evidence |
| [Portable local verification](MIGRATION-TEST-PLAN.md) | Hash-locked Python setup, explicit public-media restoration, and reproducible checks |
| [Sidecar guide](../sidecar/README.md) | Local inference runtime, gesture rules, loopback protocol, and explicit camera opt-in |
| [Video testing](../sidecar/VIDEO-TESTING.md) | File-only verification/replay and optional Full backend commands |
| [Native source guide](../android/README-motion.md) | Android host, proxy/debug modes, and native verification entry points |
| [Development handoff](DEVELOPMENT-HANDOFF.md) | Current investigation summary, next acceptance gate, and dated milestone context |
| [Source and asset provenance](PROVENANCE.md) | Authored/generated assets, vendored code, model locks, and third-party notices |
| [Demo script](DEMO-SCRIPT.md) | Manual and clearly labelled synthetic demonstration |
| [AWS spoken prompts](AWS-SPOKEN-PROMPTS.md) | Real Polly asset generation, optional offline playback, cost accounting and dated verification |

## Reading verification evidence

Reports below describe specific runs. Their dates, test counts, environments,
source hashes, and outcomes are scoped to those runs. A passing build, synthetic
test, completed replay, or Android emulator run does not establish live-user
recognition or physical Fire TV/Vega readiness. Fresh output belongs in ignored
`verification-results/`; keep the frozen expectations and historical failures.

### Latest natural-motion investigation

| Report | Main finding or purpose |
| --- | --- |
| [Independent natural evaluation — October 21](INDEPENDENT-NATURAL-EVALUATION-20261021.md) | Three-source diagnostic cohort has zero definite positives; separates headless Full, native game UI, bridge-only checks, and the later 120-second rerun. |
| [120-second replay evidence](verification/replay-duration-120-20261021.json) · [independent review](verification/replay-120s-support/analysis-review/ui-120-result-review.md) | Two interrupted clips finish in the explicit diagnostic UI flow; preserves the original 30-second failures and unchanged progress. |
| [Natural evaluation contract](NATURAL-EVALUATION-CONTRACT.md) | Geometry, confidence admission, timing uncertainty, frozen labels, and human-review requirements |
| [Natural-left timing audit](NATURAL-LEFT-TIMING-AUDIT.md) | Retains the early-event timed failure and separates model timing from uncertain physical onset. |
| [Python Full natural benefit](PYTHON-FULL-NATURAL-BENEFIT.md) | Existing Full backend's bounded natural-left/negative comparison; no native candidate promotion |
| [Native confidence verification](NATIVE-CONFIDENCE-VERIFICATION.md) · [coordinate sanity](NATIVE-CONFIDENCE-SANITY.md) | Calibration/held-out pilot found no qualifying replacement gate; 0.65 stays unchanged. |
| [Native MediaPipe eligibility](NATIVE-MEDIAPIPE-ELIGIBILITY.md) | Static packaging and telemetry/dependency eligibility decision; not a native accuracy result |

The [frozen cohort archive](../sidecar/fixtures/independent-natural/cohort-20261021/README.md)
includes scoped summaries and a [DVIDS768147 provenance correction](../sidecar/fixtures/independent-natural/cohort-20261021/analysis-review/DVIDS768147-PROVENANCE-CORRECTION.md).
That asset's redistribution eligibility remains uncleared. The archive is not a
self-contained downloadable media corpus or a human-approved acceptance set.

### Mac/browser and public-file records

| Report | Scope |
| --- | --- |
| [Full IMAGE verification](MEDIAPIPE-FULL-VERIFICATION.md) | Optional local-file backend, constructed near-face 1→6 improvement, actual browser replay, isolated restore recipe, and limits |
| [Model candidate comparison](MODEL-CANDIDATE-COMPARISON.md) | Bounded Heavy/RTMPose comparisons; no replacement promoted |
| [Natural control verification](NATURAL-CONTROL-VERIFICATION.md) | Independent right-only control and rejected crop-expansion experiment |
| [Natural motion diagnosis](NATURAL-MOTION-DIAGNOSIS.md) | Frame-level calibration, geometry, and confidence diagnosis |
| [Natural video verification](NATURAL-VIDEO-VERIFICATION.md) | Bound fixture commands, constructed versus continuous inputs, and complete-goal acceptance |
| [Migration verification](MIGRATION-VERIFICATION.md) | Recorded checks from the canonical checkout after migration |
| [Initial motion prototype](MOTION-PROTOTYPE.md) | Earlier implementation, lease/privacy rules, and historical verification boundaries |
| [Public fixture provenance](../sidecar/fixtures/README.md) | Per-source licensing, construction recipes, and disclosed held/reflected inputs |

### Native records

These reports retain earlier baseline decisions and failed/partial runs. Use the
latest natural evaluation above for the subsequent replay-duration result.

| Report | Scope |
| --- | --- |
| [Native video verification](NATIVE-VIDEO-VERIFICATION.md) | Debug LiteRT/MoveNet pipeline, official reference update, positive/negative controls, and failures |
| [MoveNet reference parity](MOVENET-REFERENCE-PARITY.md) | Exact sampled input/output parity boundary and independent crop checks |
| [Full-frame baseline](NATIVE-FULLFRAME-BASELINE.md) | Rejected historical preprocessing baseline |
| [Portable Fire OS audit](FIREOS-PORTABLE-BASELINE-AUDIT.md) | Static packaging/API/ABI audit; no device acceptance claim |
| [Native verification](NATIVE-VERIFICATION.md) | Original APK build and unsuccessful cloud-emulator boot attempts; later Mac emulator runs are recorded separately. Its legacy launcher is not a current setup command. |

## Project history and drafts

- [Milestones](MILESTONES.md): dated implementation and migration checkpoints.
- [Tool feedback](FEEDBACK.md): historical tool and environment friction.
- [Submission record](SUBMISSION-DRAFT.md): approved event-facing copy, actual
  submission receipt and dated verification scope; review live Devpost for current status.
- [`verification/`](verification/): checked-in structured summaries and supporting
  reviews. Some records reference local-only raw artifacts; those paths are
  historical provenance, not fresh-clone setup requirements.

Keep the visible product name **Sway & Sprout** while preserving storage, package,
bridge, and protocol identifiers. Follow [repository instructions](../AGENTS.md)
when changing code, restoring fixtures, or reporting verification results.
