# Optional Full model verification — 2026-10-20

The selected official Google Full model fixes the preserved near-face constructed
fixture: **six actual inferred gestures, six game rays and ACK6**, compared with
one using the existing default backend. Clear/frontal six-event controls and two
natural negative controls do not regress. This is an opt-in **local-video** path;
the default OpenCV Zoo backend remains unchanged. Natural alternating-six and
live-user recognition remain unverified. The physical camera stayed off.

## Actual integrated results

Both canonical CLI paths decoded the same frozen files, ran their actual pose
model, the unchanged classifier/service, same-frame in-memory preview and the
actual JavaScript game reducer. Full used the committed loopback-only macOS
launcher. The complete-goal flag was required for the three constructed inputs.

| Frozen input | Default events / rays / ACK | Full IMAGE events / rays / ACK | Scope |
|---|---:|---:|---|
| Clear held | 6 / 6 / 6 | 6 / 6 / 6 | Constructed goal verified |
| Frontal held | 6 / 6 / 6 | 6 / 6 / 6 | Constructed goal verified |
| Near-face held | 1 / 1 / 1, exit1 | **6 / 6 / 6**, exit0 | Same six-event expectation |
| DVIDS right-only | 0 / 0 / 0 | 0 / 0 / 0 | Left-first wrong-side negative |
| Commons both-up | 0 / 0 / 0 | 0 / 0 / 0 | Both-up negative |
| Continuous original | 0 / 0 / 0 | 0 / 0 / 0 | Partial annotation, observed only |
| Continuous reflection | 0 / 0 / 0 | 1 / 1 / 1 | Reflected, observed only |

The constructed clips contain repeated frames, cuts and disclosed reflected
left poses. They verify the existing ordered six-event expectation, scoring and
ACK; they have no independently certified event-time windows and do not verify
natural six-action recognition. All reports record zero physical camera opens,
zero saved output frames/uploads, cleared preview caches and unchanged private
participation. Synthetic landmark tests are a separate regression category.

The actual Chrome → Vite → Full video sidecar check **passed**: six displayed
rays, six alternating model events, ACK6 and53 available previews, with the sixth
ray at13.881s. The scalar [verification record](verification/full-image-20261020.json)
binds the report and harness hashes. It uses real HTTP, model output, previews
and the app's renderer/reducer; no semantic events are mocked. The video badge
remained explicit and isolated saved progress was identical after six rays,
the automatic replay result and reload. Capture API calls, browser console/page
errors and HTTP errors were zero. No screenshots or preview frames were saved.
The browser, Vite and sidecar were stopped afterward. Earlier harness failures
(Chrome Unix IPC policy, first-poll badge timing and an incorrect expected
completed-page heading) are retained locally; no product change was needed.

Fresh regression checks: **156 Python tests,55 JavaScript tests,90 saved-progress
checks,37 synthetic-landmark checks, six decoder checks and production build all
passed**. The prior13 mocked browser cases were not rerun; the connected Full
video browser check is one separate new check.

## Why the existing model fails

The official-reference audit confirms anatomical indices11/12/15/16, RGB order,
input layout, normalization, one sigmoid for each visibility/presence logit,
scalar whole-pose presence and inverse crop transforms. The detector uses
NCHW/RGB[-1,1]; the pose model uses NHWC/RGB[0,1]. These deliberately differ.
The pinned Zoo artifact's exact Lite/Full/Heavy attribution is unspecified by its
published provenance; it must not be inferred from file size.

On the frozen DVIDS right-up frames136–151, all16 raw model wrists already have
**down geometry before confidence filtering**. At F148, projected right-wrist
y207.851px differs from the independent manual interval60.625–76.250px by at
least131.601px. Wrist visibility is .244189, wrist presence .995069, whole-pose
presence .998616. Replacing local visibility with a global score would retain
incorrect coordinates. No threshold was lowered.

The upstream Zoo wrapper omits official heatmap refinement. Adding the official
7×7/peak≥.5 algorithm in a controlled NumPy comparison still recovers **0/16**
raised frames and regresses selected near-face left gates8→2. The local peak at
F148 is .380214. A float32-style scalar replay preserves all256 joint decisions;
maximum coordinate difference from float64 is .00009156px. This is algorithmic
reference parity, not execution of Google's C++ calculator.

A separate Microsoft ONNX Runtime1.31.0 CPU comparison fed both engines identical
float32 tensors and the same locked weights on35 selected inputs. All35 gate
decisions agree; DVIDS remains0/16. Maximum four-joint displacement is
.00009651px, confidence difference .000001967. Some raw outputs fail the declared
elementwise tolerance, so the engines are not claimed bit-identical. Maximum
relative L2 error is6.0216e-6.

That runtime comparison used FFmpeg CLI BGR decoding; baseline used OpenCV
CAP_FFMPEG. A model-free comparison found no pixel-identical selected frames and
maximum channel difference3. F139 crosses detector .65 between the decoders
(.6385 versus .6501). Identical tensors were still shared between engines in the
runtime comparison. This is not a claim of decoder pixel identity.

Primary references: [pinned Zoo implementation](https://raw.githubusercontent.com/opencv/opencv_zoo/47534e27c9851bb1128ccc0102f1145e27f23f98/models/pose_estimation_mediapipe/mp_pose.py),
[Google model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf),
[official ROI graph](https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/mediapipe/modules/pose_landmark/pose_detection_to_roi.pbtxt),
[heatmap calculator](https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/mediapipe/calculators/util/refine_landmarks_from_heatmap_calculator.cc),
[Pose Landmarker Python API](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python).

## Selected implementation and tradeoffs

`--pose-backend mediapipe-full` lazily loads a separately pinned MediaPipe1.1.1
CPU graph and the9,398,198-byte official Full task. Its SHA256 is
`4eaa5eb7a98365221087693fcc286334cf0858e2eb6e15b506aa4a7ecdcec4ad`.
Verified model bytes are passed directly into the graph, avoiding a second file
read. Exact runtime versions and the model hash are emitted as metadata; no
Zoo commit is attributed to this graph. Inference never installs or downloads.

The model operates in stateless IMAGE mode on each file frame, so pausing or a
new round cannot reuse a temporal pose cache. The
[official task graph](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/pose_landmarker/pose_landmarker_graph.cc)
redetects in IMAGE mode; VIDEO/LIVE_STREAM can reuse previous ROIs. Built-in
landmark smoothing is configured only for single-pose stream mode. This adapter
uses `num_poses=2` to reject returned multiple poses, so no single-pose smoothing
benefit is assumed. IMAGE success cannot be transferred to VIDEO or future
multi-person operation. The model card also identifies face position/orientation
and facial occlusion as quality factors; those are documented limits, not proof
of the cause of this fixture's failure. It requests up to two poses and
accepts exactly one returned33-landmark pose; this is a conservative response to
observed multiple detections, not a general proof that every extra person will
be detected. The four used joints’ values must be finite/in range, anatomical, unreflected,
and in frame. Per-joint confidence remains min(visibility,presence). Task
admission/presence/tracking thresholds remain .65. The API exposes no measured
detector/global-pose score: observation/event confidence .65 is explicitly a
**conservative task-admission lower bound**, and caps the displayed minimum.
It must not be presented as a measured global confidence or compared as such to
the Zoo output. Native graph cleanup occurs on verifier exits and after worker
shutdown. The optional backend is rejected for camera/synthetic/smoke modes
before dependency initialization; invalid local files are also rejected first.

On this8GB Apple Silicon Mac, Full median inference is about23.2ms/frame versus
22.2–22.4ms for the existing pipeline in this run. Whole450-frame DVIDS processing
is10.885s versus10.402s, excluding startup. File replay retains every frame and
slows down when necessary. The first fresh-environment Full command took44.822s
wall time with3.838s measured processing; startup/cache overhead was not isolated.
Subsequent152-frame runs took4.37–4.59s wall time. These are local measurements,
not a device-independent real-time guarantee.

Full matches6/16 certified overhead frames; the longest selected correct run is
66.733ms, below350ms. Heavy improves that selection only to9/16 at69.16ms/frame
and30.7MB; it was not integrated. Apple Vision's already-installed framework
matches15/16 overhead frames, including a433.767ms run, at47–48ms/request, but
misses both near-face raised controls0/8 each. Its coordinate mappings and
confidence semantics were independently checked; decoder pixel identity with
OpenCV was not established. It was not integrated or scored end to end. Full
VIDEO mode regresses the clear/near-face cut controls to zero events; it is not
available. No model fusion, reflected fallback or fixture-specific gate changes
were adopted.

## Restore and exercise locally

Run from the canonical root on CPython3.14/macOS14+ arm64. The existing
`sidecar/.venv` remains the default headless OpenCV environment. The optional
19-wheel hash lock uses its own environment, including OpenCV contrib required
by Google's package; never combine the two OpenCV distributions in one venv.
The official package/model are Apache-2.0; preserve Google's model card and the
installed distributions' license notices. Restore explicitly:

```sh
python3.14 -m venv .toolchain/mediapipe-venv
.toolchain/mediapipe-venv/bin/python -m pip install --require-hashes --only-binary=:all: --no-deps -r sidecar/requirements-mediapipe-macos-arm64.lock
python3 sidecar/fetch_mediapipe_model.py
mkdir -p verification-results
python3 scripts/run-local-pose.py verify sidecar/fixtures/held-public-arm-fixture.mp4 --expected sidecar/fixtures/held-public-arm-fixture.json --require-complete-goal --output verification-results/full-nearface.json
```

The source URL contains `latest`, but size and SHA256 are frozen: changed bytes
fail restoration. Existing mismatched files are preserved. The helper never runs
automatically. Media/model binaries, venvs, logs and output reports stay ignored.
Public held-fixture restoration remains in [the test plan](MIGRATION-TEST-PLAN.md).

For actual app replay, start the web app and the separate file sidecar:

```sh
npm run dev
# In another terminal, from the same root:
python3 scripts/run-local-pose.py replay sidecar/fixtures/held-public-arm-fixture.mp4
```

Choose Catch the Sunshine, then its existing camera-input connection and Start.
The sidecar source must display **VIDEO REPLAY · NO CAMERA**. This path opens only
the selected local file via FFmpeg, and the game labels its rays as simulated.
Replay follows the selected file cadence; `--seconds` is a verification-only
bound and is rejected for replay. Stop the sidecar with Ctrl-C after use.

Google documents utilization/performance telemetry in MediaPipe. The launcher
uses macOS `sandbox-exec` to deny external networking while allowing only
loopback for the app bridge, and redirects caches into ignored `.toolchain`.
No unsandboxed fallback is allowed. This OS policy applies to native code and
child processes; it does not pretend that the library itself disables telemetry.
The profile was checked with a successful actual loopback exchange and a denied
external UDP-connect attempt without sending data. Direct backend invocation
bypasses this launcher policy and is not the recommended operational command.

## New both-up control and remaining input

[Taco Fleur's Kettlebell Suitcase Row and Press](https://commons.wikimedia.org/wiki/File:Kettlebell_Suitcase_Row_and_Press.webm)
is creator-authorized CC BY-SA4.0, confirmed by the item's VRT record. Preserve
attribution, source link, [license](https://creativecommons.org/licenses/by-sa/4.0/)
and modification disclosure. The source SHA256 is
`6e0054cc92c28ff1d265f00c2e74ca68540d1d30885d88088d0398c96de26a18`.
Every source frame720–855 was independently reviewed before any inference.
A contiguous136-frame trim/rebase/re-encode at30fps,640×480 removes audio;
no reflection, splicing, duplicate holds or retiming was added. The derivative
SHA256 is`e5d5cecc1d981e6589432add534a6a09fbd4ee692864a3f0ec4603ef5864ef80`.
The frozen [expectation](../sidecar/fixtures/natural-controls/suitcase-both-up-negative.expected.json)
requires zero gestures. Its initial500ms has both wrists down with a bent torso;
its final500ms has both wrists up. These windows are not an ideal upright
calibration or a positive alternating goal. Full matches15/16 down and16/16 up
versus13/16 and13/16 for default; both correctly score zero.

The exact opt-in selection recipe, after retrieving and verifying the source
from the item page into the ignored cache, is:

```sh
ffmpeg -nostdin -v error -n -i sidecar/fixtures/.cache/natural-controls/suitcase-row-and-press.webm -vf 'trim=start_frame=720:end_frame=856,setpts=PTS-STARTPTS' -an -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -threads 2 -fps_mode passthrough -movflags +faststart sidecar/fixtures/.cache/natural-controls/suitcase-both-up-negative.mp4
```

Encoder differences remain a binding mismatch; do not rewrite frozen truth.
The further Commons flag-wave source has both hands on a pole, occlusion and
camera motion, so no left-positive was certified. Creator-licensed MEVA metadata
and122 exemplar titles supplied no suitable arm-raise candidate; only metadata
and a65KB ZIP tail were fetched, with no pixel-level rejection invented. No
additional purchases, credentials or bulk datasets were used.

Needed next: a rights-cleared, continuously filmed≤30s frontal single-person
clip with a visible anatomical left-up/right-down action, both-down neutral
intervals≥500ms and single-up holds≥500ms, ideally three left/right alternations.
Shoulders/wrists and raised-hand context must stay in frame. Pixel annotation
must be frozen independently before inference. No reflection, duplicated holds
or model-derived expected sequence can satisfy that missing natural-positive
gate. Existing DVIDS overhead failure remains open; no permission is pending.
