# Native MediaPipe official-route eligibility — 2026-10-21

**Pause the stock 1.1.1 Android AAR integration before build or task initialization.** Static Android/ARMv7/no-Play-Services requirements pass, but the inspected official SDK unconditionally initializes remote statistics and exposes no public supported opt-out in the pose task path. This activates the latest delegation’s explicit condition to pause when telemetry is required and not bypass it. It is a task constraint, not a tool approval rejection. No blocked action executed, no uncertain outcome, and no pending approval.

## Sample accounting

| Split | Visible person | Occluded person | Person subtotal | Reviewed backgrounds | Native inference total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Calibration |47|6|53|20|73|
| Independent validation |32|3|35|20|55|

Thus53/35 refers to person images, while73/55 includes20 backgrounds in each split. The88 original person rows, splits and human labels remain unchanged. The separately frozen MoveNet selection remainsNone; the0.65 native/frontend gate and all frozen video annotations are unchanged. This continuation does not reopen heldout outputs.

## What was verified

The exact official tasks-core1.1.1 AAR SHA256 is38fa5886edfe8dd8c83292f4c2fb069488b6e8f3856c1c42042eaf13432d0b61; tasks-vision SHA256 iscf6565d27feb96b411bbb2e5cb38b3db37e0e0d3109f30ec0c9a8178055051e6. Both minSDK 24 manifests are compatible statically with the provisional API 28 target. Core contains a10,099,244-byte `armeabi-v7a` library verified as ELF32 ARM. The22-coordinate declared effective dependency closure has no com.google.android.gms. These are static facts, not real FireTV or32-bit runtime validation. The root AAR manifests add no permissions/components, but exact required stock transport AARs are not cached. The staged nontransport subset is incomplete for the unmodified SDK; no complete stock merged-manifest or added-permission claim is made.

Official binary/POM origins are Google Maven and Maven Central; no new credentials, explicit legal terms or Play Services are required by this audited closure.

Fresh javap on those unchanged class jars confirms PoseLandmarker.createFromOptions→TaskRunner.create. TaskRunner invokes the stats factory at bytecode offset9, before graph loading34 or starting102. The factory unconditionally calls TasksStatsProtoLogger.create at3; its constructor creates RemoteLoggingClient. That constructor calls TransportRuntime.initialize at8, selects CCTDestination at14 and creates the transport at37; logEvent calls Transport.send at8. The public pose/BaseOptions builders and TaskRunner factories have no logger or telemetry-disable parameter; the TaskRunner constructor accepting a logger is private. Two independent code reviews agree. This proves a statistics transport path; it does not prove or allege that image frames are uploaded. Nothing was initialized or sent.

The official TasksStatsDummyLogger is a real no-op, but there is no supported injection into this stock pose path. The previously staged449fdec6…b8b65 AAR changes a factory class and is therefore a local SDK modification, not an official configuration switch. It remains unexecuted outside the canonical checkout. It will not be substituted to bypass the current condition, nor will missing transport dependencies, reflection or network blocking be treated as an official opt-out.

## Outcome and next boundary

No experimental APK build, dependency installation, graph initialization, camera, emulator or three-video inference was started. Consequently there is **no new MediaPipe recognition or latency result** and no reason yet to run its full regression. The canonical default backend and0.65 stay intact. MoveNet raw keypoint scores and MediaPipe visibility/presence estimates remain different semantics; the frozen MoveNet calibration is not transferred to another model.

Recommendation: stop the stock 1.1.1 AAR candidate under the present condition. A verified official telemetry-off runtime, or explicit revised authority for a maintained SDK fork, is needed to resume this route. The earlier factory/adapter/frontend drafts remain local and unintegrated; their synthetic checks do not establish native runtime success. No push, deploy, upload, spending, credentials or persistent permission changes occurred. User has no FireTV hardware; hardware capture and sustained performance remain unverified.

`eligibility.json` records exact hashes, bytecode offsets, composition and blocked-action status. Full saved bytecode evidence remains in the local dated workspace; no binary/log artifact is uploaded.
