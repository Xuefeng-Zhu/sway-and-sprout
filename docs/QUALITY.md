# Quality and verification

## What was verified

- Production Vite bundle builds successfully; Android asset sync succeeds
- Seven Node model tests cover authored challenge structure, saved-state filtering and idempotence, phase bounds and directional focus
- Playwright uses actual Chromium on the cloud VM for full gameplay and screenshots; no simulated success state or fake timer was injected
- Cloud GUI browser independently opened the app and Enter moved from home into setup with the correct primary focus
- Android wrapper compilation is now verified; actual Fire TV runtime remains **unverified**

## Visual review

Compared `artifacts/design-concept.png` with actual `artifacts/home-1920.png` using image inspection. Also inspected mobile and paused gameplay screenshots.

Five principal comparisons: (1) left-aligned large cream heading, (2) lime pill CTA and cream focus ring, (3) right-side original three-flower botanical scene, (4) three numbered lower challenge cards, (5) dark forest palette and lower remote hints. The above-the-fold headline, supporting line and CTA copy match. Functional status and safety copy were added deliberately.

Material fixes: explicit two-line card titles prevent symbol overlap; mobile navigation wraps rather than clipping; pause hint uses supported ASCII glyphs; synchronous initial focus eliminates a rapid-key race. Native 1920×1080 and 390×844 browser viewports are covered. Image assets are decorative, while all app content and controls remain native HTML.

Intentional differences from concept: independent generated background has different flower geometry; system typography is less rounded; simple Unicode challenge symbols replace detailed card illustrations; reduced card ornamentation keeps ten-foot text clear. This is a reviewed interpretation, **not a pixel-perfect claim**. Real TV viewing distance, safe-area behavior, VoiceView, old WebView versions, performance and remote hardware behavior still need device QA.

## Environment friction

The initial shell sandbox prevented Chromium sockets; an execution escalation failed before launch because its filesystem mount setup failed. The same tests then ran through the authorized cloud desktop terminal against the shared source, without changing permissions or reading restricted files. The separate GUI browser could reach the app once the server ran in that VM context.

## Web-MVP run — October 15, 2026

7/7 unit tests passed. 3/3 browser tests passed (about 1.7 minutes). Full timed garden progression used Enter for start, confirmation and continuation; D-pad, Back, pause, variant switching and reduced motion were checked separately. Final screenshots: home-1920.png, home-mobile.png, paused-1920.png, celebration-1920.png. Actual GUI browser independently verified Enter start, Back pause and Right/Right/Enter return to garden. The full suite reported no page errors. Production build and asset sync succeeded. `android-preflight.sh` explicitly reports missing Gradle; native build remains pending.


## Native build continuation

`assembleDebug` and `lintDebug` succeeded using official Android SDK tools, Gradle 8.9 and Java 21. APK signature verification and manifest inspection succeeded. The manifest exposes a Leanback launcher and requests no network/camera/microphone permission. Fixed launcher bitmap density and Android backup compatibility metadata. Remaining intentional lint warnings concern fixed landscape orientation (TV target) and enabling JavaScript (required for locally bundled app; external navigation blocked, no native bridge). Compilation is not runtime evidence.

## Native runtime attempt outcome

The official Android TV API 30 image and emulator were installed after separate Preview-license approval. This VM lacks KVM/CPU virtualization. Two cold-boot attempts (two cores, then one core after kernel diagnostics) did not reach boot-complete within their 10-minute observation windows. The one-core attempt reached system-server initialization. No APK installation, launch or native screenshot was reached. This does not establish either app success or app failure on Android TV/Fire OS. Next runtime test requires a practical accelerated emulator environment or an actual Fire TV.
