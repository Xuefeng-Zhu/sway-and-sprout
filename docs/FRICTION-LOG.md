# Build and demo friction log

Observed while preparing Sway & Sprout on October 23, 2026. These issues describe
the exercised local workflow; they are not general reliability ratings.
Suggestions marked P1 would prevent incorrect output or blocked builds; P2 would
improve setup and documentation.

The [demo capture plan](DEMO-SCRIPT.md) and [dated submission record](SUBMISSION-DRAFT.md)
describe the recording workflow and final verification scope.

## 1. Android toolchain setup

**Task:** Rebuild the native Android TV host.

**Steps:** Build the web assets, synchronize them to Android, and select the
documented local Gradle toolchain.

**Expected / actual:** A clear compatible build path. The exported AGP 8.7.3 /
Gradle 8.9 pair was absent on the test Mac; the installed AGP 8.13.2 / Gradle 8.13,
JDK 17 and SDK 35 required an explicit local override.

**Severity:** Medium; setup-specific.

**Workaround:** Use the [documented cached-toolchain path](../android/README-motion.md)
while preserving the exported version pins.

**Suggestion (P2):** Provide one prerequisite checker that reports the compatible
SDK/JDK/Gradle combination and separates the ordinary host from optional diagnostic
model dependencies.

## 2. Static endings in Android screen recordings

**Task:** Record a readable restart-persistence result.

**Steps:** Complete a round, restart the app, and hold the unchanged garden on screen.

**Expected / actual:** The final garden remains visible for the intended hold.
Android `screenrecord` did not encode that full unchanged tail, leaving less than
half a second of the manual take's post-restart result.

**Severity:** Medium; the evidence became difficult to read.

**Workaround:** Re-record the continuous take with actual garden navigation after
the persistence result, then verify the encoded ending before editing.

**Suggestion (P1):** Add a capture preflight that compares the requested recording
duration with the encoded end and warns when a static tail is missing.

## 3. Export color and pixel format

**Task:** Export the demo as H.264 with limited-range `yuv420p`.

**Steps:** Render the Remotion composition with the requested pixel format and
inspect the result with `ffprobe`.

**Expected / actual:** The first export should match `yuv420p`; it reported
full-range `yuvj420p` with BT.470BG color metadata instead.

**Severity:** Medium; the file missed the required delivery format.

**Workaround:** Render directly from PNG frames with explicit BT.709 color space.
The final export reports limited-range `yuv420p` and BT.709.

**Suggestion (P1):** Offer an explicit limited-range delivery preset and validate
the encoded pixel format and color metadata after rendering.

## 4. Captions across intentional silence

**Task:** Keep burned-in captions aligned with narration pauses.

**Steps:** Insert a narration gap and preview the interval after a cue ends but
before the next cue starts.

**Expected / actual:** The caption disappears at its authored end. The caption
component held the previous text through the intentional silence.

**Severity:** Medium; the displayed text no longer matched the audio timing.

**Workaround:** Gate caption visibility at each cue's `endMs`; verify the blank
interval and the following cue in the preview and export.

**Suggestion (P1):** Honor cue end times by default and include a silence-gap
example in the caption component's documentation.

## 5. Polly CLI argument handling

**Task:** Generate bundled spoken activity prompts.

**Steps:** Invoke the AWS CLI's custom `polly synthesize-speech` command using a
generic `--cli-input-json` request.

**Expected / actual:** The generic request supplies the synthesis parameters.
The command rejected it before producing audio output.

**Severity:** Low; invocation-specific.

**Workaround:** Supply explicit `--text`, `--voice-id` and `--output-format`
parameters, as used by the [prompt generation script and guide](AWS-SPOKEN-PROMPTS.md).

**Suggestion (P2):** Highlight the custom command's argument behavior beside a
complete working example and point generic-JSON failures to that example.

## 6. Offline release dependency availability

**Task:** Build debug and release targets without downloading dependencies.

**Steps:** Run the cached Mac build script with offline dependency resolution.

**Expected / actual:** Both targets use available cache contents. Debug assembly
passed; release lint required the uncached `com.android.tools.lint:lint-gradle:31.13.2`
artifact and could not complete offline.

**Severity:** Medium; release validation was blocked in that environment.

**Workaround:** Run `:app:assembleDebug` separately for the emulator build. Preserve
the release failure without bypassing lint or claiming a release pass; see the
[dated build report](verification/aws-spoken-prompts-native-build-20261023.json).

**Suggestion (P1):** Preflight dependencies for every requested target and report
missing release artifacts before starting a combined offline build. Expose debug
and release as separate documented commands.
