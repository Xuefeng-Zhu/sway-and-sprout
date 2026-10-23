# Native APK verification — October 15, 2026

This is a historical build/boot record for the original host and cloud VM.
For current native source guidance, start with [the Android guide](../android/README-motion.md).
Later [native video verification](NATIVE-VIDEO-VERIFICATION.md) and
[independent natural evaluation](INDEPENDENT-NATURAL-EVALUATION-20261021.md)
record separate Mac emulator runs. The legacy launcher at the end of this report
targets a fixed emulator and the old unsuffixed app ID; it is not a current setup
command. See the [portable plan](MIGRATION-TEST-PLAN.md) before native verification.

## Build

- Official Gradle 8.9 distribution verified against official SHA-256, checksum-pinned wrapper committed
- Official Android command-line tools build 15859902 verified against Google's published SHA-256
- Installed Android SDK platform 35, build-tools 35.0.0, platform-tools; AGP 8.7.3 also installed its required build-tools 34.0.0
- Java 21 compiled Java 8-targeted host source; compiler emitted obsolete-target/deprecated-API warnings, not errors
- `assembleDebug lintDebug`: successful, zero lint errors, two intentional warnings
- Debug APK signature verified with apksigner
- aapt confirms application com.togethermove.tv, minimum API 25, target API 35, launcher + Leanback activity and no permission requests
- All web assets are present inside APK; no external runtime dependency

The APK is a debug/test build, signed by the build environment's local debug key. It is not an Appstore release or a production signing-key handoff. Debug key material is not included in the repository or source archive.

## Intentional lint warnings

1. Fixed landscape orientation: TogetherMove targets a living-room television. The browser layout separately supports small screens.
2. JavaScript enabled: required for the bundled local app. External URLs are blocked, file/content access is disabled, the manifest has no INTERNET permission, and no JavaScript native bridge is exposed.

Added Android 12 data-extraction exclusions and disabled older full backup; moved the launcher banner into drawable-nodpi.

## Licensing and source trust

The user approved the Android SDK agreement and, separately, the SDK Preview agreement for the Android TV image. Only their approved prompts were accepted. The first preview prompt was declined until the separate approval arrived. SDK/Gradle tooling and emulator images are excluded from source.

## Runtime boundary

The generic Android TV API 30 emulator is a compatibility check, not an Amazon Fire TV or Vega simulator. Even a successful launch here cannot prove Fire OS behavior or satisfy the contest's platform-demo requirement. The official hackathon overview specifically asks for actual Fire TV or Fire TV/Vega simulator footage: https://amazonappdev2026.devpost.com/ . No qualifying Fire TV runtime demonstration is claimed.

Runtime outcome: hardware acceleration is unavailable (emulator acceleration check reports missing vmx/svm support). A two-core software-emulation cold boot did not reach boot-complete in 10 minutes. A kernel-log diagnostic showed progress with one core, so a second full one-core boot was attempted. It reached Android system-server initialization but still did not reach boot-complete in a further 10-minute window. Both attempts were stopped cleanly. The harness therefore never reached APK installation or app launch, and no native UI screenshots were produced. This is an emulator-environment limitation/unfinished boot result, not evidence that the APK crashes. Use a hardware-accelerated machine or actual Fire TV for the next runtime test.

## Repeating compatibility tests on a capable machine

Install the official Android SDK emulator and Android TV API 30 x86 image only after reviewing their respective license prompts. Create an AVD named TogetherMoveTV (1080p TV), set ANDROID_HOME and optional ANDROID_AVD_HOME, then run `bash scripts/test-android-tv.sh`. It uses hardware acceleration by default; EMULATOR_ACCEL=off selects software emulation. The script boots the emulator, installs the locally built APK, launches it, sends D-pad center and play/pause, and saves screenshots/logs. Screenshot inspection remains necessary; issuing input commands alone does not prove UI success. This script does not replace a real Fire TV test.
