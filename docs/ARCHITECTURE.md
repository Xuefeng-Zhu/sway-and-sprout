# Architecture

Sway & Sprout is a local JavaScript/CSS app bundled by Vite. Manual play has no
runtime network dependency. Optional Catch the Sunshine recognition uses an
explicitly started Python/OpenCV sidecar on Mac loopback; it is single-person.

Screens follow home → setup → play → check/celebrate. requestAnimationFrame
advances each 30-second round, with pause/background handling. Directional focus
uses button centers, and native Java forwards remote input to the same handlers.

Manual participation is self-reported. A completed six-ray camera round can also
save sunshine participation. Incomplete camera rounds retain the labelled manual
confirmation path. Explicit video/synthetic provenance survives fallback, so
simulated completion never saves human participation. `src/model.js` normalizes
`{completed: string[], sessions: number}` under the preserved `togethermove.v1`
key; unknown IDs and invalid counts are rejected. Storage failure is disclosed.

`src/motion.js` bounds/validates packets and filters source, runtime, round,
revision, age, sequence and anatomical alternation. `src/calibration.js` validates
optional feedback without creating events. `motion-view.js` renders readiness;
preview visibility alone cannot authorize a raise.

The sidecar verifies pinned model/wrapper hashes and matches unique DNN output
shapes. It detects and estimates pose independently per frame; no temporal ROI
tracker exists. The gesture machine requires confident neutral before a held
expected-arm raise. Service leases, capture epochs and ACK reconciliation prevent
old frames or transport resets from scoring a new context. Calibration snapshots
describe actual frame evidence; old frames suppress readiness without changing
the classifier's state. Preview uses one bounded in-memory image from the same
inference frame, and preview reads cannot activate capture or renew the lease.

The release Android host serves packaged local assets and blocks external
navigation. The separate debug motion prototype has a fixed proxy to the emulator
host alias; it does not request a TV camera and is not a physical Fire TV route.
Current native runtime verification is separate from Mac/browser evidence.

The visual system uses forest, cream and lime, with coral/gold/lavender moments,
large system type, visible focus and reduced-motion support. Product artwork is
local. See [the development handoff](DEVELOPMENT-HANDOFF.md) for commands, exact
invariants, evidence and unresolved acceptance checks.
