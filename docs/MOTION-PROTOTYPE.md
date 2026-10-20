# Local sunshine recognition prototype

The current product is **Sway & Sprout** — Every move helps your garden grow.
Development continues in `~/mygit/sway-and-sprout`; the dated TogetherMove export
is a preserved backup. Internal storage/native/protocol identifiers intentionally
retain TogetherMove names. Historical export and build provenance remains in the
[migration record](MIGRATION-VERIFICATION.md) and native verification notes.

Only Catch the Sunshine has optional single-person recognition. Manual play
works without Python or a camera. The pinned local OpenCV sidecar can explicitly
select synthetic, public video or camera input; the source label is preserved
through transport, scoring and persistence decisions.

For current setup, architecture, tests and next work, use the
[Mac development handoff](DEVELOPMENT-HANDOFF.md). For full file inference and
strict goal acceptance, use [natural-video verification](NATURAL-VIDEO-VERIFICATION.md).
The [normal-motion diagnosis](NATURAL-MOTION-DIAGNOSIS.md) records the concrete
zero-event causes and limits rather than asserting a decoder defect.

Recognition requires visible/confident shoulders and wrists, then 300 ms with
both wrists down before the expected anatomical arm is held up for 350 ms.
Wait for Ready; visible markers alone are insufficient. Lower both arms after
each ray. Wrong-side/both-arm raises, loss and long gaps discard partial holds.
The current UI explains calibration, visibility and stale-frame blockers.

Camera capture remains off during offline development. A later supervised user
test requires explicit readiness, local in-memory frames only and prompt capture
shutdown when finished or participation is unavailable. Synthetic/video rays do
not save human participation. Manual fallback remains available.

Clear/frontal constructed public fixtures score six rays; near-face remains 1/6.
The current dancing clips do not certify complete natural alternation, and no
successful live user recognition is claimed. Native APK/Fire TV/Vega verification
and two-player camera co-op remain separate future work. No publication or further
push is part of this local development milestone.
