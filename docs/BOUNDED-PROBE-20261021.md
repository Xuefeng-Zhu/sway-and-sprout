# Bounded Android TV probe — 2026-10-21

The single windowed emulator attempt did **not** reach active gameplay. It booted,
installed the exact debug APK and issued the activity start command, then the
harness aborted on its first unsuccessful app PID query. This does not establish
whether the app crashed or was simply not ready.

This evidence applies only to commit `25abbd3d16651967f05b196069c7319d85c2dd46`.
Later UI/source changes are not in this APK. Historical strict results remain
unchanged; this run does not resolve the earlier visible replay slowdown.

## Build and approval chronology

Automatic approval initially rejected the task-local no-fork compiler override
before execution, citing the earlier read-only diagnosis restriction. Fresh parent
authorization clarified the later testing/build scope. One retry was approved and
executed with the original network-deny profile; it still failed in
`:app:compileDebugJavaWithJavac`, at `WorkerDaemonStarter` →
`TcpIncomingConnector.accept`, with `Operation not permitted`.

A direct existing-JDK `javac` fallback had launched before the subsequent coordinating-agent
stop arrived and finished before process inspection. It compiled 19 sources,
including main/debug sources and generated configuration (34 classes), then cached
Gradle packaged offline with only the blocked JavaCompile task excluded. This was
not a successful ordinary Gradle compilation. Packaging finished at 08:44:32.784
UTC. Both checkouts were clean at that point; the build changed no tracked source.
Existing JDK 17, Gradle 8.13, AGP 8.13.2, SDK 35, pinned AARs and debug keystore were
reused. No new software was installed; no models or media were copied or downloaded.

- APK: `android/app/build/outputs/apk/debug/app-debug.apk`, 22,750,906 bytes.
- SHA-256: `e20ba3cc0c030741484c98d54f9477f2beae7b8928ac206e83dd9d688cfe0dbf`.
- Installed APK hash matched these exact bytes.

## What the one attempt measured

| Observation | Actual result |
| --- | --- |
| Run interval | 08:49:25.485–08:50:08.472 UTC |
| Windowed emulator boot | 16.761 seconds; 90-second startup bound |
| Active input | Never started; configured maximum 60 seconds |
| Activity start command | Returned `Starting: Intent`; no running activity confirmed |
| First app PID query | Exit 1 raised `CalledProcessError` before WebView attachment |
| Synthetic service | OpenCV 5.0.0 verified by pinned hashes, zero-tensor forwards and output shapes; warmup 46.75 ms |
| Input and events | 0 polls, 0 accepted/rejected observations, 0 generated events, ACK sequence 0 |
| Video | None decoded; frame coverage not applicable |

No WebView score, ACK exchange, game timer, active poll age/epoch/invalidation,
app/emulator CPU-versus-wall comparison or runtime pause/reset/dedup result was
obtained. The service's 1.317-second wall / 0.385-second CPU lifetime covers startup,
warmup and shutdown only. Its cleanup audit epoch is not gameplay evidence.
Cameras were off, natural media was unused, and the original network policy hash
remained `3bf9fa87d9d3867cc258a863635d0c7a993eb09881397c7d8b0b6aa419a6e222`.
The 1,500 ms lease and event TTL were preserved.

## Cleanup and confirmed harness repair

The app was force-stopped. The emulator kill command returned 0, but its 12-second
graceful deadline expired; the task-owned process was then stopped with exit -9.
Task ADB on 5041 closed; pre-existing ADB on 5038 was untouched. The synthetic HTTP
and worker threads joined, its token became null, and no events remained. The
parent's subsequent process check reported no task-owned processes left running.

The PID supervisor now treats empty `pidof` exit 0/1 as startup retries within a
real three-second deadline, retains query diagnostics and collects bounded
package-only failure logs before cleanup. All 14 deterministic fake-clock/response
tests passed. They started no subprocess, service or emulator. The original policy,
cleanup functions, 58-second active guard and single-run marker were preserved.
No second emulator attempt verified this repair.

[Structured evidence and operational-file hashes](verification/bounded-probe-20261021.json)
identify the saved records in the sibling task-local `probe-20261021` directory.
The app launch outcome, end-to-end activity scoring, and historical replay root
cause remain unverified. No physical Fire TV or natural-motion accuracy claim is
supported.
