# Native fixture preparation — 2026-10-21

Offline preparation is complete. No emulator, video inference, desktop control
or capture ran in this continuation. Desktop/emulator work is paused while the
separate SayGo task records. The last observed Mac session was locked; the later
fixture approval did not assert that it was unlocked, and no unlock was attempted.

## Resolved preparation scope

The earlier automatic review rejected fixture creation because a design-or-locate
restriction still applied. The parent supplied materially relevant authorization
superseding that restriction. Exactly one post-denial retry of
`prepare_synthetic.py` executed, exit 0, at 16:14:25.138–16:14:25.460 UTC. Later
approval was checked against this completed outcome; preparation was not repeated.
The original denial, failed nested-sandbox attempt and successful retry remain
separate saved records.

Existing ffmpeg generated H.264 `testsrc2` geometry: 640×360, 10 fps, 20 frames,
2 seconds, without people or external footage. Existing ffprobe counted all 20
frames. Gesture expectations are explicitly unknown with an empty expected-event
list. The existing pinned Lightning FP16 model was copied locally; no model was
downloaded. All three assets passed independent hash/config review.

| Ignored diagnostic asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `verification/synthetic-throughput.mp4` | 106451 | `02a3981f53dbe702966fde26097eff112e53a1b94cae925e17eec951dcc811bd` |
| `verification/synthetic-throughput.float16.json` | 554 | `dc33f6d10b13e9e48d6dba56af25289a93a008e2ae427aac1b60a4b3220a5000` |
| `verification/movenet-lightning-float16.tflite` | 4758512 | `0fac2226112d0371903ca86e3853cec24ef603a0b2f96f589b180f0ebdd135ab` |

## Separate diagnostic APK

The offline build passed all five stages at 16:18:55.903–16:19:12.782 UTC:
web build, Android asset sync, BuildConfig, direct existing-JDK compilation and
cached Gradle packaging. It compiled 21 Java sources into 37 classes. Every build
child retained the original network-denying profile. No new software, security
configuration, credentials, paid service or external upload was used.

- Build source: `127a1aecd9c00a76e2149e88b92bd074dc6a15c9` on
  `work/activity-progression`; its application bytes match `f23f9e7`.
- Local APK, relative to the worktree:
  `../native-ui-resume-20261021/build-video-fixture/app-debug-127a1aecd9c0-611b55e431a9.apk`.
- Size: 27,665,840 bytes; SHA-256
  `611b55e431a95c43f3e263662b74bcffd71097cf45a8fbff075eb8451362a10d`.
- Packaged web assets match the web build. The complete asset allowlist matches;
  its only media/model entries are the generated MP4 and existing FP16 model.
- The previously tested manual APK, SHA-256
  `59e03ce8d16c43e1caf110f79e626ebdf2c53c5fcdd086db09aa8576c59c023d`,
  remains preserved separately. The new diagnostic APK has not been installed.

The original network profile SHA-256 remains
`3bf9fa87d9d3867cc258a863635d0c7a993eb09881397c7d8b0b6aa419a6e222`.
The canonical checkout remained clean at `45ced16` before and after the build.
No gameplay source changed, so the previously passed 118 Node tests, 90 progress
checks and 1,067 Java assertions were not repeated for documentation/asset work.

## Pending runtime evidence

The [earlier native manual journey](NATIVE-JOURNEY-20261021.md) passed with 32
layout checks; this build does not add runtime proof. Full synthetic-input
completion/ACK/reset checks, native video timing/coverage, a complete labelled
demo and local submission materials remain unfinished. Resume only after SayGo's
desktop work has ended and desktop availability is actually verified, using a
fresh bounded run folder and the unchanged 1.5-second lease and cleanup guards.

The prepared video would exercise decode and inference throughput; it does not
contain human movement and cannot establish recognition accuracy. Its crop
workload differs from historical footage, so it cannot alone resolve the prior
8/188-frame windowed slowdown. No physical Fire TV or live human recognition
has been verified. No camera/microphone, push, deployment or public submission.

[Structured preparation, build and artifact pins](verification/native-fixture-preparation-20261021.json)
bind this checkpoint while preserving all earlier failed results.
