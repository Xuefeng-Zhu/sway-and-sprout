# Clean native checkpoint — 23 October 2026

The concise UI and native manual garden journey work. Native video processing is
not real-time, and reliable natural-movement recognition remains unverified.
This record preserves failures before any conditional cloud experiment.

## Source and build

The measured source was `ef56bae09759a1a82119de8e598fb6584b7d8564` plus the
native RGB packing, reference-profile and timing changes committed with this
record. Its 373-file source-tree SHA-256 was
`b8dfe9e5ca9505da81720fd737ffe24e6c9da28d92970b0bfac9c636a12b04a4`.
The separate canonical checkout stayed at `45ced16`.

Existing JDK 17.0.20+8, Gradle 8.13, AGP 8.13.2, SDK 35 and build-tools 35.0.0
were used. The explicit cached-toolchain init-script override leaves the declared
Gradle 8.9/AGP 8.7.3 pins intact. Official Google Maven/Maven Central resolution
cleared the earlier missing dependency cache. No SDK agreement or security
setting changed. The clean invocation used fresh output/project-cache directories:

```text
clean --rerun-tasks --no-build-cache :app:assembleDebug :app:assembleRelease :app:lintDebug
```

The first attempt compiled and packaged but failed API-25 lint because
`CRC32.update(ByteBuffer)` requires API 26. Reusable RGB byte packing and
`CRC32.update(byte[], offset, length)` fix that compatibility error. Tests compare
complete tensors, diagnostic totals and checksums against the old packing recipe.
The second clean build passed in 18.577 seconds: 92 of 93 tasks executed; one had
no work. Lint reported zero errors and 11 warnings. This rebuilt project Java,
Dex and packaging; the pinned prebuilt LiteRT AAR was not rebuilt from C++ source.

Debug APK: 27,974,422 bytes; SHA-256
`29729ab6c596324d302b861cd704df8e03bde396d52c89e5c3bc1182c2e4ef8a`.
Unsigned release: 2,621,117 bytes; SHA-256
`08016e36af9eae0d6f4e1145f3d1857aa6ae38ec097f8f670b32e06d26913e17`.
Release excludes debug ML/media assets. APKs, weights, footage and raw operational
logs remain local and are not part of Git. Signature and ZIP alignment checks
are not physical-device compatibility evidence.

## Verified results and failed measurement

- 159 Node tests passed. All 23 Android Java sources compiled and eight host Java
  programs passed, including fake-clock lease and full RGB byte/checksum parity.
- The clean APK passed ten manual-journey gates on the windowed Google Android TV
  API 34 ARM64 emulator: entry, growth, confirmation, harvest, grow-again, saved
  reload, focus, pause/Back and Help return. Input was explicit manual self-report.
  The original garden was restored and reload-verified.
- Two-second generated geometry reached 20/20 frames and EOF in 14.363 seconds
  with sampled references and 10.800 seconds with references off. All 20 final
  input/output CRCs matched. Geometry contains no person and establishes no
  recognition accuracy. A single sequential pair does not establish a stable
  percentage speedup. Sampled-reference default remains unchanged.
- The existing licensed Taco Fleur CC BY-SA 4.0 excerpt (136 frames, 30 fps;
  SHA-256 `e5d5cecc1d981e6589432add534a6a09fbd4ee692864a3f0ec4603ef5864ef80`)
  stopped at 77 accepted frames, zero events and no EOF. Its frame-77 attempt
  recorded control age 1,833 ms against the unchanged 1,500 ms lease. Maximum
  native poll gap was 2,770 ms. The WebView controller later hit a bounded
  observation deadline. Owned processes were stopped; graceful native object
  closure and that session's final garden read were unknown. The subsequent
  manual run restored the same original garden.
- The 77 accepted poses contained 51 tracking and 26 low-confidence statuses.
  Low-confidence resets movement history. The longest tracking stretch covered
  200 ms of file time, below the activity rule's 250 ms minimum. Why the model
  confidence fluctuated is unproved; hip scores/path rejection details were not
  logged. No activity-count ground truth exists for this clip.
- Accepted human frames averaged 321 ms per attempt, including 200 ms for three
  primary inference passes; 30 fps affords 33 ms. Diagnostic references were off.
  There were no events, so positive event-to-JS/ACK latency was not measured.

Inference runs in the Android worker; same-origin WebView polls refresh its
control lease. No AWS service participates. A slow frame does not necessarily
expire the lease if independent polls stay fresh. The logs prove stale control,
not its scheduler/renderer/host cause. A post-failure high-swap observation is a
hypothesis to investigate, not a causal finding. The historical 8/188 replay was
not directly retested and remains unresolved.

The scoped patch adds init/decode/crop/resize/pack/inference/classification/ACK
observations and explicit debug `sampled|off` reference profiles. It does not
change the model, three primary passes, confidence policy, scoring, 1.5-second
lease or stop semantics. Performance rows cannot count as accepted frame coverage.

## Reproduction and evidence boundaries

Use the pinned dependency/media recipes in [native verification](NATIVE-VIDEO-VERIFICATION.md)
and [permitted input provenance](MOTION-TO-GARDEN-20261021.md). Older media recipes
are not renewed clearance for restricted footage. `scripts/verify-native-source.py`
compiles against explicit existing SDK/AAR caches without downloads or inference;
`npm test` and `npm run build` cover the app. Native video tests require a separately
approved, bounded emulator run and preserved save state.

Raw build commands, source snapshots, APK binding, stage timing rows, recovery
manifest and failed controller records are preserved in the local dated workspace
`native-clean-20261023/`. The main files are `REPORT.md`, `build/BUILD-REPORT.md`,
`build/clean-build-proof.json`, `BENCHMARK-ANALYSIS.json`,
`runtime/taco-off-02/RECOVERED-native-scalars.jsonl` and `FINAL-CLEANUP.json`.
They are QA evidence, not public demo material. All owned processes and task ports
were closed. No camera, microphone, paid service or physical Fire TV was used.

Next diagnostics should isolate control-request scheduling and pose-history reset
reasons. Do not weaken the safety lease, silently discard source frames, equate
synthetic performance with accuracy, or treat an EC2 result as Fire TV performance.
