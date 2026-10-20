# Tool feedback and friction — truthful development record

## Amazon Fire TV documentation
Used the remote-input reference to map D-pad, select, Back and play/pause in the Android host. The event mappings were concrete and helpful. The hackathon resources make framework flexibility clear, while the requirement for an actual Fire TV/Vega demonstration is essential. No Fire TV SDK or device runtime was executed, so runtime onboarding, performance, stability and build-tool satisfaction are untested. Would continue with device testing before deciding on production use.

## Vite
Used for local app bundling and asset packaging. Production build succeeded with a small JavaScript/CSS payload and no runtime dependencies. On this restricted executor, binding all interfaces triggered an operating-system interface-enumeration error. Workaround: bind loopback explicitly. Severity: low/environment-specific. Suggestion: gracefully report interface-enumeration failure without aborting a usable loopback server.

## Playwright / Chromium
Used for real interaction tests and screenshots. Initial sandbox launch failed because Chromium could not create a local socket; normal execution escalation failed before launch due to a mount setup error. Workaround: run the same script through the authorized cloud VM terminal. This is environment friction, not an Amazon platform defect. An initial test selector failed because a CSS-generated checkmark changed the accessible name after selection; corrected the selector and expanded remote-only coverage.

## Image generation
Used for original concept and botanical art. Separable background assets enabled local offline delivery. Concept-to-implementation differences remain in exact flower geometry, icon treatment and system typeface; no claim of pixel-perfect reconstruction is made.

## Initial SDK/toolchain blocker (resolved for APK build below)
At the initial web-MVP milestone, the executor had Java but no Android SDK, Gradle, adb, Fire TV device, or Vega simulator. No SDK download, installation, license acceptance, credentials setup, or spend was attempted. Android wrapper remains unbuilt. Needed next: approved Android SDK/Gradle installation and accepted license, then actual Fire TV access or approved simulator.

## Native continuation update

After explicit user approval, downloaded and checksum-verified official Android command-line tools and Gradle. SDK Manager could not write its default home cache; directing ANDROID_USER_HOME to the project-local ignored toolchain directory resolved it. Gradle dependencies and APK build then succeeded. Gradle requested build-tools 34 automatically under the already accepted standard SDK agreement. Lint caught backup metadata and banner density issues, both corrected. Required TV landscape and local JavaScript warnings are documented. A Java-17 compile target experiment exposed that this VM's Java installation lacks jlink; reverted to the working Java-8-targeted source configuration rather than suppressing checks. SDK Manager warned its CLI is deprecated in favor of the newer Android CLI; it still completed package installation.

Android TV system images require a separate Preview license, even for the API 30 image. Paused, obtained separate user approval, then accepted. Emulator defaults also assumed writable home directories; redirected only its process-local HOME/runtime paths into ignored workspace toolchain files. Hardware acceleration check reports no vmx/svm support. This is VM-specific friction, not a claim about Fire TV.
