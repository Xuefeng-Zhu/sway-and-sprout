# Submission demo — manual garden and labelled synthetic input

## October 23, 2026 recording

The submission video is 165 seconds in English. The main footage runs the
current signed debug APK on a disposable Android TV API 34 ARM64 emulator clone.
The organizer's [current FAQ](https://amazonappdev2026.devpost.com/details/faqs)
explicitly permits Android TV Emulator footage. This does not establish physical
Fire TV, Fire OS or Vega OS behavior. Preserve the dated native reports.

| Video window | Recorded story |
| --- | --- |
| 0–8 seconds | Sway & Sprout home and the shared garden idea. |
| 8–38 seconds | Wake the garden: seated start, native remote pause, switch to standing, resume, then self-confirm participation. |
| 38–68 seconds | Catch the sunshine using **Manual play**, then confirm participation. |
| 68–98 seconds | Make some rain, then confirm the third moment. |
| 98–110 seconds | Celebration and **3 of 3 moments grown**, retained after app restart. |
| 110–153 seconds | Synthetic sunshine through the Mac loopback service, six test rays, timed completion, and unchanged saved participation after restart. |
| 153–165 seconds | Cooperative play and current evidence limits. |

Every recorded ordinary round uses the actual 30-second timer. Cirro may speed up
idle waits, with its visible fast-forward indication; it must retain the
interaction order, important prompts, confirmations and outcomes. The opening
may naturally reach setup slightly before the nominal chapter boundary.

## Reproduce the capture

1. Sync the base safely, run `npm test` and `npm run build`, and run the existing
   simulated-progress preservation harness. Synchronize Android assets, build
   with the existing toolchain, verify the APK signature, and compare bundled
   asset hashes with `dist`.
2. Clone the AVD configuration and every writable image into a disposable local
   profile. Verify all writable image paths remain in that clone. Keep both
   cameras disabled, snapshots off, and external networking denied. Confirm
   the demo serial and clone identity before resetting only its app storage.
3. Launch the normal debug app without `nativeVideo` extras or
   `input=video-verification`. Capture actual D-pad/select/play-pause actions.
   Complete all three manual moments with **We joined in**. Do not select
   **Grow together again**, which intentionally resets participation.
4. Record the garden before and after app restart. Preserve the exact raw
   `togethermove.v1` value as the baseline for the next take.
5. Start `npm run motion:synthetic`. The debug native bridge uses the fixed
   `10.0.2.2:8765` endpoint to reach the Mac loopback service. Choose sunshine,
   then **Camera sunshine**, and Start. Verify the actual response identifies
   `source: synthetic`, and keep **SYNTHETIC TEST · NO CAMERA** visible.
6. Let the generated input collect six rays and allow the actual 30-second round
   to finish. Show the garden and restart again. Verify raw saved progress is
   byte-identical before input, after completion, and after restart. These are
   generated landmarks, not human recognition or native pose inference.
7. Retain original takes and actual input logs. Dispatch intervals are not exact
   input timestamps; omit animated event overlays when synchronization is not
   established. Stop only processes created for the demo, verify listener
   release and original AVD hashes, and remove disposable credential copies.

The ignored `artifacts/demo-submission-20261023/` folder holds the recording kit,
raw takes, Cirro screenplays, Remotion project, Polly narration and verification.
The Remotion composition is `SwayAndSproutSubmission`: 1920×1080, 30 fps,
4,950 frames. Use the retained lockfile and the reproduction instructions in
its README. The final MP4, matching SRT, original-art thumbnail and portable
project ZIP are in `deliverables/`. The export passes all 16 format, full-decode
and subtitle checks. Captions clear at their authored ends, including the
deliberate pause before synthetic saved-progress narration.

## Narration and publication

Use AWS Polly Joanna Neural (`en-US`, `us-west-2`) through the existing `tally`
profile, with the approved aggregate $1 ceiling for audio, speech marks and any
corrections. Cache successful requests and retain sanitized receipts. Polly is
video narration in this recorded edit. A later October 23 update adds optional
Polly-generated app prompts, documented separately in
[AWS spoken prompts](AWS-SPOKEN-PROMPTS.md); the existing video does not show
that new control. No microphone, stock
verification footage or music is needed.

Manual participation is self-reported. Synthetic/video results never grow saved
participation. Natural alternating-six recognition, live-user performance and
physical Fire TV behavior remain unverified. Do not start camera mode without
user readiness for a later test.

Review the complete exported video before publication, including a human
listening pass for pronunciation and naturalness. Objective waveform checks
confirm all eight narration segments at their intended positions with no
clipping; they do not establish a listening review. The [official submission
rules](https://amazonappdev2026.devpost.com/rules) call for a public English
YouTube/Vimeo video under three minutes. Local export, public upload, and final
Devpost submission are separate steps; this recording workflow does not perform
the latter two.
