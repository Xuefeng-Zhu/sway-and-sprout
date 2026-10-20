# Milestone record

## 2026-10-15

1. Read official Devpost overview, rules, resources and Amazon remote input reference. Selected web runtime plus Fire OS Android host. Recorded actual-device/simulator demo requirement.
2. Generated full-screen concept and separate original botanical asset. Created warm forest design tokens, remote-first screen structure and three authored moments.
3. Implemented position choice, timed cues, pause, Back handling, self-report completion, shared progress, celebration, replay and local storage normalization.
4. Built production bundle and offline Android host source. Added Leanback manifest, native key handling, lifecycle pause, isolated asset serving and original launcher graphics. Host build blocked by missing toolchain; no device claim.
5. Added unit and browser tests. Resolved npm cache issue with temporary cache; resolved local Chromium execution using cloud VM terminal. Browser tests caught a selector issue and rapid-key focus race. Fixed focus synchronously.
6. Visually reviewed desktop/mobile/play/celebration screenshots. Fixed card title/icon overlap and missing pause glyph; kept all text code-native.
7. Prepared run instructions, architecture, provenance, submission draft, English demo script and factual friction log. External publication and submission remain pending user approval and native runtime verification.

## Native build continuation — 2026-10-15

Verified clean source at 405d9ad and 29 GB available space. Downloaded Gradle 8.9 from its official distribution endpoint, verified the official SHA-256, and successfully ran it on installed Java 21. Generated a checksum-pinned Gradle wrapper for reproducible builds. Gradle's network URL probe failed although curl downloaded and verified the same distribution; wrapper generation used the already-verified URL without repeating that probe. Android SDK download and use remain paused pending the user's explicit acceptance of the SDK license. No KVM device is exposed in this executor, so emulator acceleration is not established.

### APK milestone

After the user approved the standard SDK agreement, installed checksum-verified official command-line tools plus SDK platform/build tools. Compiled the native host and passed lint; verified debug APK signature, Leanback manifest and bundled web assets. Fixed backup and launcher-resource metadata. User separately approved Preview terms for the Android TV compatibility image. Actual Fire TV/Vega testing is still required for a qualifying demo; generic Android TV testing is tracked separately.

### Runtime diagnostic outcome

Official Android TV emulator installation succeeded under the approved Preview agreement. Process-local home/runtime paths resolved initial filesystem assumptions. With no CPU virtualization, two 10-minute software boot attempts did not reach boot-complete; one-core kernel logs showed Android system-server startup. Stopped the emulator cleanly and retained factual diagnostic logs. No native app launch was reached. Delivered verified debug APK and updated source; actual Fire TV runtime remains the next release/submission gate.


## Mac development continuation — 2026-10-20

- Continued on local `work/natural-motion-diagnostics` from private-main checkpoint
  `ed4e1f5f12003319fc2cb4a93c4c203fee104adb`; no subsequent push or deployment.
- Demonstrated and fixed conflicting preview/arming instructions and stale Ready
  after frame stalls. Added bounded calibration diagnostics; thresholds and
  classifier/event behavior remain unchanged under differential review.
- Bound video expectations to exact input bytes and made complete-goal acceptance
  explicit. Preserved near-face 1/6 and natural original/reflection zero-event
  outcomes rather than treating consistent transport as recognition success.
- Canonical checks: 55 JS, 113 Python, 90 progress, 37 synthetic, six decoder,
  production build, 12 mocked Chrome cases and one real HTTP synthetic Chrome
  case passed. Capture was guarded off; all test services were stopped.
- Added repeatable diagnosis and source-only natural-video reconstruction, current
  setup/demo documentation and [developer handoff](DEVELOPMENT-HANDOFF.md).
  Complete natural-motion accuracy, live user recognition and native runtime
  remain unverified; two-player camera work was not implemented.
