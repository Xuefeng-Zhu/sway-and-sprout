# Sway & Sprout — submission record

Submitted to Build, Ship, Shape: Amazon Developer Hackathon on October 23, 2026, at 10:53:48 a.m. Pacific (17:53:48 UTC). Devpost returned submission ID `1255413`, and a fresh live readback and the finalization page both confirm **Submitted**. The initial entry selected **Fire TV**, with no mini challenges; the later mini-challenge additions are recorded below.

The later owner-requested update is now saved: **Fire TV + AWS Builder + Open
Source**. Both mini-challenge opt-ins read **Yes** on a fresh Additional Info
page load, their required explanations/links are populated, and Devpost still
returns **Submitted** for ID `1255413`. The project story is version 4. The
original submitted-at timestamp and public 165-second video remain unchanged.

- Public project: https://devpost.com/software/sway-sprout
- Public demo: https://www.youtube.com/watch?v=eQlCzsax3fI
- Public repository: https://github.com/Xuefeng-Zhu/sway-and-sprout

The project story, repository link, video and custom thumbnail are saved on Devpost. The source is MIT licensed at commit `794903dc34cffb80b08482c336c39eeb2cdf17d5`; third-party assets retain their documented licenses. The user explicitly confirmed the required personal answers, Amazon Developer account, rules, terms and eligibility declarations before the final submission. Sanitized API receipts and a visual confirmation are retained in the ignored demo artifact folder.

## Elevator pitch
A little movement, a lot of together: turn three playful living-room moments into a shared garden, using just one TV remote.

## Inspiration
Living-room experiences can welcome people with different energy levels and ways of moving. Sway & Sprout makes participation cooperative and pressure-free: seated, standing, small movements, or simply watching along.

## What it does
Families follow three 30-second authored moments: Wake the garden, Catch the sunshine, and Make some rain. Each offers seated and standing prompts. A remote can pause, replay, change position, and move through the app. At the end of each manual moment, participants decide whether they joined in; their shared garden records that self-reported choice. Manual play needs no camera or performance score.

Catch the sunshine also contains an optional single-person motion prototype. The demo uses explicitly labelled synthetic landmarks from a local Mac service, displayed in the Android app. Those generated inputs collect six test rays without changing saved participation. They do not establish native pose inference, human recognition, or live-camera performance.

## How it was built
An offline JavaScript/CSS app with Vite, original AI-generated botanical art, a remote-first focus system, local progress, and an Android WebView host designed for Fire OS. The native host maps Fire TV keys into the same interaction logic and packages all web assets locally.

## Current verification status
On October 23, 2026, the production web build passed, 86 Node tests passed, and the separate progress-preservation harness passed 90 checks. A fresh signed Android debug APK was built from the current source; all five bundled web assets match the production build.

A new recording on an isolated Android TV API 34 ARM64 emulator demonstrates native D-pad navigation, pause/resume, seated-to-standing switching, all three real 30-second manual rounds, self-confirmation, and saved garden persistence after restarting the app. A second take demonstrates six synthetic rays through the native-to-Mac local bridge; the raw saved progress is byte-identical before input, after completion, and after restart.

The organizer's current [FAQ](https://amazonappdev2026.devpost.com/details/faqs) explicitly permits the Android TV Emulator for submission and judging. This clarification supersedes the older submission-readiness assumption that generic Android TV footage could not qualify. It does not establish Fire OS, Vega OS, physical Fire TV performance, or live-user recognition; those remain unverified. Historical test reports retain their original scope.

## What is distinctive
Cooperative self-report, equal seated/standing participation, short sessions, no camera setup, no account, no remote server, and no fabricated motion metrics.

## Track
Submitted primary track: Fire TV / family entertainment. The initial 10:53 a.m.
entry excluded mini challenges. The later owner-requested update includes both
mini challenges with the substantive additional work described below. The API
submission receipt, live project readback and saved Additional Info fields all
confirm the update. Sanitized receipts and the saved-field screenshot remain in
`artifacts/demo-submission-20261023/submission-prep/` and `verification/`.

### AWS Builder addition, October 23

Amazon Polly Joanna Neural now generates 18 bundled manual-play instructions
through the application's documented build-time asset pipeline. Optional Spoken
prompts play locally, stop on pause/leave, restart on resume and follow position
changes. They default Off after app restart and do not alter saved-progress
formats. The new web build passes 98 Node tests, seven focused browser checks and
the 90-check preservation harness. Real browser audio decoded all 18 clips and
played/paused one with no external requests. The updated signed debug APK builds
offline and contains byte-identical copies of all 18 clips and current web assets.
The separate release lint target lacks an uncached dependency; no release build
pass is claimed. A separate fresh Android TV Emulator run passes 21 checks with
15 actual D-pad inputs, verifies real audio decode/playback and pause/position
behavior, preserves nonempty saved progress byte-for-byte and resets audio Off
after restart. All seven layout checkpoints fit the actual 960×540 CSS viewport.
The clone/key copies are removed and all seven original AVD image hashes remain
unchanged. See [integration and evidence](AWS-SPOKEN-PROMPTS.md).

### Open Source addition, October 23

[Caption Pause Map](https://github.com/Xuefeng-Zhu/caption-pause-map) is an
additional standalone MIT project created and published during the hackathon.
The [initial contribution](https://github.com/Xuefeng-Zhu/caption-pause-map/commit/5c86021449ef2a811132e8e6976ac9146e369bcc)
generalizes demo caption timing work into a Python standard-library CLI. It
preserves all source audio in its segment plan, maps captions around inserted
pauses, validates cue boundaries and refuses output overwrites. Its synthetic
example and 35 tests require no media, credentials or network. GitHub username:
`Xuefeng-Zhu`. This additional project contains no primary-app media or receipts.

## Submitted deliverables
The approved English video is public on YouTube: 165 seconds, 1920×1080 at 30 fps, H.264/yuv420p with AAC audio, burned-in captions and a matching SRT. All 16 final format, decode and subtitle checks pass. Narration waveform and timing checks pass; an independent human listening assessment was not recorded by the automated verification. Signed-out YouTube playback was verified before submission. The public repository is accessible and GitHub detects its MIT license. Deadline verified from Devpost's live key dates: October 23, 2026, noon Pacific time (19:00 UTC). The project page remains editable until then.

The local video project, source recordings, sanitized verification receipts and narration are under the ignored `artifacts/demo-submission-20261023/` directory. The candidate is `deliverables/sway-and-sprout-submission.mp4`, with an editable Remotion preview and a portable project ZIP beside it. The video predates the later spoken-prompt feature: its Polly use is narration. The added AWS Builder work is the separate documented application asset integration, with offline app playback. Combined conservative Polly reservations are $0.069888 within the $1 cap.
