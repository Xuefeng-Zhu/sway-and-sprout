# Permitted video to garden credit — 21 October 2026

One bounded local run processed a continuous human-motion excerpt through the
existing OpenCV 5 models, activity service and actual game code. It reached EOF
with **136/136 frames, three activity events, three game rays and ACK 3**.
The in-memory view reported three collected rays and growth 0.5. Recorded-video
credit caused **zero saved-participation writes**. This is a working functional
connection between image inference and temporary garden progress.

## Input and license

The input is the existing `suitcase-both-up-negative.mp4` excerpt, SHA-256
`e5d5cecc1d981e6589432add534a6a09fbd4ee692864a3f0ec4603ef5864ef80`,
332,963 bytes, 640×480, 136 frames at 30 fps. It selects decoded source frames
720–855 from Taco Fleur's
[Kettlebell Suitcase Row and Press](https://commons.wikimedia.org/w/index.php?title=File:Kettlebell_Suitcase_Row_and_Press.webm&oldid=1004642243),
then re-encodes to MP4 without audio, reflection, resizing, retiming or splicing.
The source is own work under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
with Wikimedia permission-confirmation ticket 2017110310008425. The source hash
is `6e0054cc92c28ff1d265f00c2e74ca68540d1d30885d88088d0398c96de26a18`.
The asset page, CC legal code and Wikimedia non-text reuse terms were checked
before this use. No new media was downloaded or distributed. Media stays ignored;
any future distributed adaptation must retain attribution/change notices and
meet ShareAlike. MIT covers neither this clip nor its derivative.

The old filename and empty strict-gesture expectation remain unchanged. The clip
was a negative for the historical prescribed single-arm policy. It contains
both-arm movement relevant to comfortable activity, but has **no newly annotated
activity count or accuracy ground truth**. Its low angle, backlighting,
letterboxing, equipment and short duration limit what can be learned from it.
Pexels, uncleared DVIDS and unlicensed YouTube inputs were not used.

## Execution and result

The run used OpenCV 5.0.0 (`opencv-python-headless` 5.0.0.93), NumPy 2.5.4 and
hash-pinned OpenCV Zoo CPU models. Model output went through the production
`MotionService` activity policy, then `src/main.js`, the reducer and view functions
in a VM with in-memory DOM/storage and inert clients/timers. The source was
explicitly `video`. The real 1.5-second input lease stayed unchanged.

| Observation | Result |
| --- | --- |
| UTC interval | 20:51:16.677–20:51:22.388 |
| Processing / outer elapsed | 5.579 s / 5.711 s |
| Bounds | 30 s internal; 45 s outer owned-process watchdog |
| Coverage | 136 decoded; 136 inferred; EOF; no skipped frames |
| Activity events | Frames 9, 39 and 123; sequence 1–3 |
| Game / view / ACK | 3 rays / 3 collected, growth 0.5 / ACK 3 |
| Status frames | 104 tracking, 18 low confidence, 14 no person |
| Mac inference time | Median 33.079 ms, maximum 38.662 ms; one per-frame CPU thread |
| Saved progress | Exact original bytes; zero writes |
| Repeated first inferred observation | Zero activity events; classifier-only control |
| Cleanup | Decoder released, service closed, Node adapter and owned process stopped |

The existing OS profile denied external networking. File capture was allowlisted
to the exact hashed MP4 using FFmpeg; Python socket creation was guarded before
model initialization. The report records one allowed file open, zero blocked
capture attempts and zero Python socket attempts. Native-library internal socket
attempts were not independently measured. No browser, emulator, physical camera,
microphone, model download, cloud call or upload was requested.

## Reproduction and limits

`scripts/verify-permitted-activity-video.py` defaults to hash/license/runtime
preflight. Actual execution requires `--run`, an explicit existing video,
`--model-root`, `--node`, a new output path and a bounded wall time. Do not treat
the script as permission to download other footage or open a camera. The current
runner accepts only the pinned permitted file and keeps its output separate from
participation. `scripts/activity-game-evidence.mjs` is the in-memory game adapter.
The [scalar evidence](verification/permitted-activity-20261021.json) includes all
17 tested source hashes, model hashes, frame outcomes, guards and cleanup. The
original local report hash is
`6023f1ba0444bda3443648461130453d7eee8944be8647f3b622895c514f89ec`.

This does not establish recognition accuracy, recall, a six-ray completion,
rendered web/native performance, sustained real-time processing, live-human
usability or physical Fire TV support. It does not fix or reproduce the separate
historical windowed-emulator 8/188 slowdown. Mac file inference timings must not
be presented as TV measurements. A post-measurement review fixed cloud-only
storage-startup and cancellation feedback; the report preserves the exact main
module hash that was exercised rather than silently rebinding the measurement.

The small post-measurement patch is retained at
[`verification/post-measurement-storage-review.patch`](verification/post-measurement-storage-review.patch).
Applying it in reverse to a disposable copy of the reviewed `src/main.js`
reconstructs the tested SHA-256 `a5b9ef51bd6de0e53e25f2620211ecad1aaa1b04e76496292d3a33c76458cfa0`.
The reviewed module is `2e00efd6a5610c0b2ea4633f83b9c3571ddd58a865fc1dfe1551de2ccdba9962`.
No second video-inference run was performed after those cloud-only corrections;
the final Node and progress-isolation checks exercise the reviewed source.
