# Native garden journey — 2026-10-21

The corrected debug APK passed the complete scripted manual journey in the
windowed Android TV emulator. The remaining synthetic completion and demo did
not run because the Mac locked again. The earlier video-fixture scope denial was
resolved by a single approved retry: preparation and a separate offline diagnostic
APK succeeded. See the [later preparation checkpoint](NATIVE-FIXTURE-PREPARATION-20261021.md).
That APK has not run. Historical replay slowdown remains unresolved; desktop and
emulator work is paused while SayGo records.

## Source and APK

- `5afb212`: per-attempt replay timing, exact synthetic-case guard and diagnostic
  extraction tests. The 1,500 ms lease, strict cases, defaults and accepted-frame
  coverage remain unchanged. Processing averages keep their historical scope;
  separate attempt timing includes decision-lock waits and worker/process CPU.
- `f23f9e72c138147632745bbe8e16aa538f56b4d5`: TV layout correction and rendered
  regression. A presentation class avoids a new `:has` selector requirement.
- APK: `../native-ui-resume-20261021/build-next/app-debug-f23f9e72c138-59e03ce8d16c.apk`
  relative to the worktree root; 22,800,431 bytes; SHA-256
  `59e03ce8d16c43e1caf110f79e626ebdf2c53c5fcdd086db09aa8576c59c023d`.

The build reused existing offline tools, direct javac and cached Gradle packaging
with the blocked JavaCompile worker task excluded. It compiled 21 Java sources
into 37 classes. Packaged web assets match the build. This APK contains **no video
or model assets**; its normal manual/proxy flow was the test target.

## Actual native result

The successful run lasted 16:00:55.273–16:01:39.226 UTC, with **14.144 active
seconds** and a 45-second controller limit beneath the unchanged 60-second outer
active guard. It verified entry, three six-count manual moments, seed-to-bloom
changes, explicit confirmation, cumulative saved blooms, unclaimed-harvest
return, harvest once, growing again and exact saved-garden reload. It also checked
pause, natural RAF resume, Help, Back and reset. A 1.009-second pause kept count
and timer unchanged. All **32 native layout checks passed** at 960×540 CSS pixels.

This was automated manual self-report input, not observed human movement. The
emulator already contained one saved Sun bloom; the test retained it and restored
the original `togethermove.v1` bytes after its temporary participation fixture.
Readback hashes matched. Every captured observation reported zero camera and
microphone calls. No pose inference or video decode occurred.

The supervisor's final PASS also required successful service shutdown, joined
threads, released token, empty event queue, stopped owned processes, confirmed
app stop and all five task ports closed. A final read-only process check found no
task emulator, controller, synthetic service or layout server left running.

Native screenshots are preserved in
`../native-ui-resume-20261021/manual-fixed/attempt-3/`: entry, three manual counts,
harvest and saved-garden reload. The earlier clipped native home screenshot is in
`../native-ui-resume-20261021/attempt-2/01-native-entry.png`.

## Preserved failures and specific fixes

| Attempt | Observed outcome | Follow-up |
| --- | --- | --- |
| `native-ui-resume-20261021` / original UI APK | App PID found on second query; immediate CDP attachment failed with socket hang up; no gameplay | Added bounded exact-target HTTP readiness; four fake-clock checks passed |
| `attempt-2` / original UI APK | WebView ready after six queries/2.457 s; manual journey and partial synthetic ACK/pause/resume passed, but combined test lacked time for a natural 30 s round | Preserved overall failure at 26.320 active s; split scenarios without extending limits |
| Same attempt | Native home height 618, play 678, check 646, celebrate 692 and harvest 673 exceeded the 540 px viewport | Corrected proportional layout, not zoom or overflow hiding |
| `manual-fixed` / corrected APK | HTTP target ready but immediate Playwright lookup had no matching initialized page; no UI input | Added bounded page observation and URL diagnostics; three pure tests passed; exact cause of the earlier mismatch remains unproven |
| `manual-fixed/attempt-2` | Failed after 6.697 active s on a zero-size intentionally hidden setup illustration; actual document/controls/footer fit | Corrected rendered-scene measurement; required growth scenes still must be visible |
| `manual-fixed/attempt-3` | Complete manual native PASS; all cleanup gates true | No further manual rerun needed |
| `synthetic-fixed` | Preflight reported Mac locked; no emulator/run marker created | Stopped before startup; no unlock attempted |

The original UI APK in the first two rows is source `2b3c24d`, SHA-256
`50de6d11ff5496d549db40f0a12f0b8c0f39633391913f2c49b4e87b3c90a530`.
Partial synthetic evidence there includes duplicate seq/ACK 2 without extra
credit, a 1.026 s quiescent pause, resume to count 3, 14 active poll-gap samples,
maximum 289.254 ms and zero active lease breaks. Those are generated-keypoint
service/proxy/WebView results, not native video inference or recognition accuracy.

Preflight also fixed two harness defects: PASS previously ignored service/cleanup
failure, and post-observe invalidation could retain rejection reason zero.
Six cleanup regressions and nine isolated rejection cases passed. The corrected
PID waiter passed 14 deterministic tests and now has actual startup retry evidence.

## Independent source verification

118 Node tests, 90 actual-main in-memory progress checks, production web build,
21-source Android compilation and 1,067 Java host assertions passed. The latter
include unchanged lease tests and new case/timing checks. Six browser regressions
passed; after the presentation-class adjustment the targeted 960×540 test again
passed all 26 states. Camera and browser errors were zero. These browser results
are separate from the native manual result.

## Runtime blocker and historical fixture denial

At **16:06:02.454 UTC**, read-only IORegistry confirmed
`CGSSessionScreenIsLocked: true`. The synthetic-only scenario stopped before
emulator startup. Its score/ACK/reset/six-ray/natural-30-second completion and the
complete demo remain pending; no demo or submission material is presented as
finished. Resume the prepared isolated synthetic controller only in an available
desktop session, then record the labelled demo after successful native checks.

At the original 16:06 checkpoint, the proposed video-fixture action was
`exec_command` with `require_escalated`,
running `PYTHONDONTWRITEBYTECODE=1 python3 .../throughput-prep/prepare_synthetic.py`.
It would generate 20 geometry frames at 640×360/10 fps, create their config and
copy an existing pinned FP16 model into ignored debug assets. Automatic review
**denied it before execution**, stating: “The command creates synthetic
video/config/model fixture files, while the trusted scope permits only designing
or locating the fixture without creating it yet.” At that checkpoint no
post-denial retry had occurred and no fixture, copied model or asset manifest
existed. An earlier nested-sandbox `ffmpeg -version` command failed with exit 71
before generation and is also preserved. Later scope clarification explicitly
authorized creation; one approved retry succeeded at 16:14:25 UTC. The original
denial and this report's structured manifest remain historical evidence; the
later preparation checkpoint records the resolved scope and new asset hashes.

The model intended for that future diagnostic matches the historical Float16
model/refinement, but geometry input would still have a different crop workload.
Neither compile checks nor synthetic bridge heartbeat measurements resolve the
historical 8/188-frame windowed replay. Physical Fire TV, sustained target-device
performance and live human recognition remain unverified.

The original network-deny profile is unchanged. No camera/microphone, new tools,
paid service, credentials/security changes, new external footage, upload, push,
deployment or public submission occurred. The canonical checkout remains clean
at `45ced16`.

[Structured results, source pins and artifact hashes](verification/native-journey-20261021.json)
bind the local evidence without overwriting any prior failed result.
