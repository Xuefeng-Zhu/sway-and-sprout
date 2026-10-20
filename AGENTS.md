# Sway & Sprout development

This checkout is the canonical development source. The old dated TogetherMove export is an unchanged backup.

- Use the visible product name Sway & Sprout. Preserve `togethermove.v1`, Android IDs, bridge names and local protocol identifiers unless a deliberate compatibility migration is requested.
- Run `npm test` and `npm run build` for app changes. Python tests use `sidecar/.venv`; see `docs/MIGRATION-TEST-PLAN.md` for the locked setup and verification commands.
- Camera capture is opt-in. Prefer synthetic/public-file verification, preserve explicit input provenance, keep frames local, and never describe synthetic or stock-video results as a live user test.
- Synthetic/video completion must not alter saved participation. Retain the progress-preservation tests.
- Keep credentials, virtual environments, model binaries, licensed public media, build outputs and operational logs ignored. Restore public media only through the documented opt-in recipe; keep provenance and third-party notices.
- No emulator or Docker is needed for normal web/sidecar development. Native runtime claims require separate evidence.
