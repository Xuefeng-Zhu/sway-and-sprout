# Latest UI APK checkpoint — 2026-10-21

Superseded by the [subsequent native journey result](NATIVE-JOURNEY-20261021.md):
the corrected `f23f9e7` APK passed the complete manual native journey. This page
preserves the earlier `2b3c24d` build and initial lock checkpoint.

The current garden UI was built into a new debug APK. Native runtime verification
did **not** start: a read-only Mac console check reported
`CGSSessionScreenIsLocked: true` at 13:58:18.847768 UTC. The user explicitly
instructed us to report a lock without unlocking. No emulator, app installation,
replay, capture or demo recording was attempted in this continuation.

## Exact build

- Branch: `work/activity-progression`.
- Application source: `2b3c24d7bb43d58c4855fd96cf680400fad8b4f2`.
- APK: 22,756,785 bytes; SHA-256
  `50de6d11ff5496d549db40f0a12f0b8c0f39633391913f2c49b4e87b3c90a530`.
- Preserved task-local deliverable:
  `../native-ui-20261021/sway-and-sprout-ui-2b3c24d-debug.apk`, relative to the
  worktree root. It is deliberately excluded from Git.

The web build, Android asset sync, configuration generation, direct existing-JDK
compilation and cached offline packaging all returned exit 0 between 13:59:08 and
13:59:18 UTC. Nineteen Java sources produced 34 classes. All five packaged web
assets match the latest web build. This reused the previously successful direct
`javac` recipe and excluded Gradle's blocked JavaCompile worker task; it is not a
successful ordinary Gradle compilation.

The first post-build verifier incorrectly looked for MainActivity only in
`classes.dex`. Inspecting all DEX files found it and ActivityMachine in
`classes3.dex`. The verifier was corrected without rebuilding or changing APK
bytes; `build-attempt-1.json` preserves the initial assertion failure. No app
failure can be inferred from that verifier error.

An independent read-only review verified the APK v2 signature with the existing
SDK's `apksigner`: one Android Debug signer. The existing `aapt` reports package
`com.togethermove.tv.motion`, minimum SDK 25, target SDK 35, debuggable, and only
the INTERNET permission. It also rechecked the source, class, DEX and web hashes.
These are static build checks, not evidence that the activity launches.

The original OS network-deny profile is unchanged, SHA-256
`3bf9fa87d9d3867cc258a863635d0c7a993eb09881397c7d8b0b6aa419a6e222`.
Only installed offline dependencies were used. No models or video were copied,
no software was installed, and no camera, microphone, credentials, security
settings, paid service, upload, push, publication or submission was used. The
canonical checkout remains clean at `45ced16`. A final read-only process check
found no task emulator, probe service or build process to clean up.

## Runtime status and next bounded run

| Requested native check | Outcome this continuation |
| --- | --- |
| Windowed boot and corrected PID waiter | Not run; Mac locked |
| Entry → activity → growth → harvest → replay | Not run |
| Pause/resume, saved garden, score and ACK isolation | Not run |
| Historical replay throughput and CPU/wall timing | Not run |
| Complete native demo and local submission materials | Pending native pass |

The [previous bounded attempt](BOUNDED-PROBE-20261021.md) remains a failed startup
attempt against the older `25abbd3` APK. Its repaired PID waiter has deterministic
test coverage but still lacks an on-device rerun. Browser journey verification
remains separate evidence in the [rendered UI audit](UI-EXPERIENCE-AUDIT-20261021.md);
it does not establish this APK's behavior.

After the Mac is available through the user's normal session, use the preserved
new APK and corrected PID waiter for one windowed emulator, bounded startup and at
most 60 active seconds per diagnostic, followed by task-owned cleanup. Run the
manual garden journey separately from explicitly labelled synthetic activity
events; simulated completion must never save participation. Preserve the 1,500 ms
lease, six-ray cap, pause/reset semantics and existing network restrictions.

The throughput investigation also needs an explicitly named synthetic geometry
fixture plus per-attempt wall/CPU, epoch, poll-age and discard-reason measurements.
The current APK deliberately contains no model or video. The existing bulk video
preparation script includes historical external footage and must not be used for
this task. Do not relabel synthetic bytes as a historical human-media case.

The historical comparison supports broad pipeline slowdown and heartbeat gaps:
the windowed replay accepted 8/188 frames, decoded 27 and discarded 19, with 28
poll gaps above 1,500 ms and a maximum gap of 9,198 ms. The same historical APK
completed 188/188 headlessly with no discards. The capped game timer explains why
120 credited seconds took 236.365 wall seconds; it does not identify the source of
the decoder/inference slowdown. Host sleep, contention and window rendering
remain hypotheses. No new runtime result resolves them.

Only after native checks pass should a complete software-capture demo and local
submission materials be produced. Physical Fire TV behavior, live human motion
recognition and target-device performance remain unverified.

[Structured checkpoint and operational evidence hashes](verification/native-ui-20261021.json)
bind the build, lock observation and pending outcomes without changing prior
failed-run evidence.
