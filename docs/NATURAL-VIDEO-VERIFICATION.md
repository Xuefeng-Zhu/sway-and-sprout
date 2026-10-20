# Natural-motion video verification

Video verification has two separate questions: whether decoded model events are
scored and acknowledged consistently, and whether recognition matches a reviewed
movement sequence. Consistent zero-event scoring answers only the first.

`sidecar/verify_video.py` now checks the selected video's SHA256 against its
manifest **before inference**. A same-named, different file cannot inherit an
expected sequence. Reports identify the exact manifest hash, fixture hash and
verification outcome. `--require-complete-goal` exits 1 unless an independently
expected six-gesture sequence also produces six scored rays and matching ACKs.
That result covers the selected fixture; it does not verify a live user or
general recognition accuracy.

## Repeat the bounded checks

From the repository root, after the opt-in local media preparation described in
[the migration test plan](MIGRATION-TEST-PLAN.md):

```sh
mkdir -p verification-results
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/clear-public-arm-fixture.mp4 --expected sidecar/fixtures/clear-public-arm-fixture.json --require-complete-goal --output verification-results/clear-goal.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/held-public-arm-fixture.mp4 --expected sidecar/fixtures/held-public-arm-fixture.json --require-complete-goal --output verification-results/near-face-goal.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/frontal/bounded-frontal/continuous-source-original640.mp4 --annotation sidecar/fixtures/frontal/bounded-frontal/continuous-source-original640.partial.json --require-complete-goal --output verification-results/natural-original.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/frontal/bounded-frontal/continuous-source-mirrored640.mp4 --annotation sidecar/fixtures/frontal/bounded-frontal/continuous-source-mirrored640.partial.json --require-complete-goal --output verification-results/natural-mirror.json
```

Expected current outcomes:

| Input | Actual inference / game result | Goal check |
|---|---|---|
| Clear authored held/cut fixture | 6 events, 6 rays, ACK6 | Exit 0; selected fixture verified |
| Preserved near-face held/cut fixture | 1 event, 1 ray, ACK1 | Exit 1; expected sequence mismatch |
| Natural-speed original public clip | 0 events, 0 rays, ACK0 | Exit 1; complete goal not verified |
| Natural-speed reflected public clip | 0 events, 0 rays, ACK0 | Exit 1; complete goal not verified |

The normal-speed files retain all 319 frames in order at 30fps. Resizing and
re-encoding preserve timing; the mirror is a disclosed derived input. Partial
annotations bind those exact files, but deliberately leave `expectedGestures`
null. The public source is a dancing clip, not a certified six-alternating-raise
trial. A previously frozen review supports a filmed right-up/opposite-down
window at frames 35–46; it does not certify the initial 300ms calibration or a
complete game sequence. Reflected labels do not add an independently filmed
left-arm action. No complete natural sequence was inferred from model outputs.

Without `--require-complete-goal`, an observation-only run may exit 0 when its
transport and scoring are consistent. Read `verificationOutcome`: status
`observed-only` and `completeGoalVerified: false` are not recognition passes.
An explicit empty expected list is a negative control, also not a complete goal.

## What this establishes

The scalar [contract evidence](verification/natural-video-contract-20261020.json)
records actual file decoding → detector → pose → classifier/service → event →
JavaScript game results. Both natural files still produce zero events. That is
a reproducible gap in the available positive evidence, not by itself proof of a
classifier or decoder defect. No thresholds were lowered or media timing
changed to fit a result.

The focused regression tests separately demonstrate that mismatched fixture
hashes are rejected before inference, partial annotations cannot smuggle a full
expected sequence, and consistent zero events cannot satisfy the complete-goal
acceptance check. Those contract tests mock inference and do not establish pose
recognition.

Physical cameras and sockets are not needed. File input is constrained to the
selected local file and FFmpeg backend. Preview JPEGs stay in memory and are
cleared; reports contain no image data. Media/models remain ignored by Git.
Before a live test, the remaining acceptance need is confidently annotated
natural left/right movement with adequate visible neutral periods, followed by
actual inference and scoring. The current dancing clip cannot supply that
complete test, and held images cannot substitute for it.

## Rebuild the continuous files without PNGs

A fresh clone does not contain fixture images or videos. Once the pinned public
source is in the ignored cache (via the explicit source preparation recipe in
[the test plan](MIGRATION-TEST-PLAN.md)), the continuous comparison files need no
frozen PNGs:

```sh
python3 scripts/rebuild-natural-video-fixtures.py
mkdir -p verification-results
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/.cache/rebuilt-natural/continuous-source-original640.mp4 --annotation sidecar/fixtures/frontal/bounded-frontal/continuous-source-original640.partial.json --require-complete-goal --output verification-results/natural-original.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/.cache/rebuilt-natural/continuous-source-mirrored640.mp4 --annotation sidecar/fixtures/frontal/bounded-frontal/continuous-source-mirrored640.partial.json --require-complete-goal --output verification-results/natural-mirror.json
```

Use `--source "$PUBLIC_SOURCE"` for another local copy of the pinned source.
Use `--output-dir` to select a fresh local output directory, and adjust the
verification input paths accordingly.

The helper uses only the local hash-pinned source, FFmpeg and FFprobe. Its
default outputs and scalar `rebuild-report.json` stay under the ignored
`sidecar/fixtures/.cache/rebuilt-natural/`. It refuses existing output files or
a previous report; select a fresh output directory to repeat reconstruction.
FFmpeg 8.1.1 reproduced both frozen hashes exactly, with 319 frames at 30fps and
640×360 dimensions. Other encoder versions may differ: retain any mismatch
report, and do not replace the frozen annotation hashes to bless new bytes.
The helper neither downloads media nor generates annotations or gesture
expectations. Successful reconstruction is not successful motion recognition.
