# Independently annotated natural-motion control — 2026-10-20

New licensed footage reproduces an overhead-wrist tracking failure. A tested
crop expansion did not resolve sustained recognition and regressed an existing
result, so it was rejected. Recognition code, model bytes, confidence and
gesture thresholds remain unchanged. The camera stayed off.

The delivered fix concerns verification: optional authored event windows now
reject correctly ordered events emitted at the wrong time. A bounded generic
diagnostic helper reproduces file decode → detector → pose → classifier/service
→ actual JavaScript reducer and ACK, with numeric traces and explicit provenance.

## Source and independent truth

[Dumbbell Snatch, DVIDS 551039](https://www.dvidshub.net/video/551039/dumbbell-snatch),
Capt. Matthew Holfinger, U.S. Marine Corps Training and Education Command, is
explicitly marked PUBLIC DOMAIN on the official item. Retain its attribution and
the restrictions in the [DVIDS copyright policy](https://www.dvidshub.net/about/copyright).
The appearance of U.S. Department of War (DoW) visual information does not imply
or constitute DoW endorsement. Other rights are not waived. This is a private
local diagnostic use; media and images are excluded from Git and publication.

The normal unauthenticated public-player MP4 was acquired without credentials.
The 12,140,868-byte source SHA256 is
`53811c7890323606087b429e3ef83524f8cb961c08c16e8c2efda8750f946bc5`.
One contiguous selection, source frames **1079–1528 inclusive**, retains all
450 frames in order at **30000/1001 fps**, 1024×576, 15.015 seconds. Only trimming,
timestamp rebasing, re-encoding and audio removal were performed. There is no
reflection, splicing, holding, duplication or retiming. Its SHA256 is
`14100151f96412b84ea4fb3b9b01db1a8e3a7b2741109c452026c95b1b771e4d`.

Two independent pixel reviews certified every frame in the following windows
before any model evaluation. Shoulder locations under clothing have uncertainty;
the coarse wrist-above/below geometry has a clear margin. No model confidence
or exact landmark coordinates were assumed.

| Original frames | Selected frames | Timestamp span | Independent annotation | Baseline matches |
|---|---|---|---|---|
| 1080–1095 | 1–16 | 500.5 ms | Both wrists down | 16/16 |
| 1215–1230 | 136–151 | 500.5 ms | Anatomical right up, left down | 0/16 |

The [frozen expectation](../sidecar/fixtures/natural-controls/dvids-551039-right-negative.expected.json)
has SHA256 `d66045e78e2498b2e004bef31da2966a691333433765076f4a34123af893b6f7`.
Its empty `expectedGestures` and `eventWindows` are deliberate: the filmed
snatches use the right arm, while this game expects left first. Zero game events
is a correct **wrong-side negative control**. It is not a positive left-arm
trial, a six-alternation trial, or evidence that the overhead pose was tracked.
The primary and secondary visual reviews are stored beside that expectation.

Three additional Commons candidates by Taco Fleur were acquired under their
item-specific CC BY-SA 4.0/VRT records and screened before inference:
[Alternating Dead Swing Clean and Press](https://commons.wikimedia.org/wiki/File:Alternating_Dead_Swing_Clean_and_Press.webm),
[Alternating Half Snatch](https://commons.wikimedia.org/wiki/File:30_Minutes_Alternating_Half_Snatch_-_Half_Marathon.webm),
and [Open Palm Clean and Press](https://commons.wikimedia.org/wiki/File:Kettlebell_Open_Palm_Clean_and_Press.webm).
Free-hand height, apparent speed changes, or right-only motion prevented a
confident genuine left-up/opposite-down annotation. No positive expectation was
invented from these clips, and no model inference was run on them.

## Actual failure and rejected correction

The baseline processed 450 frames and produced **0 events / 0 rays / ACK0**,
matching the frozen game negative, with no saved participation. There were
289 confident neutral frames, 39 confident right-up frames, 81 frames rejected
for right-wrist confidence, and 11 inference-level rejections. Of the latter,
seven had multiple detector results and four had an unaccepted pose. The
certified 16-frame overhead window fails the pose acceptance check despite the
successful game negative.

At selected frame 148/original frame 1227, the resized image's crop bounds are
`(238, 62)–(531, 355)` with rotation −3.302°. The independently estimated raised
wrist box maps to model-input y **−2.095 to 12.258** in a 256-pixel image. It
crosses the top edge; the hand/dumbbell context above it is cropped. The other
three joint boxes remain inside. This demonstrates input-context loss, not an
inverse-coordinate decoding error or proof that cropping is the sole cause.

A fixed 1.25 pre-inference crop factor was declared before its comparison.
The [upstream MediaPipe ROI graph](https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/mediapipe/modules/pose_landmark/pose_detection_to_roi.pbtxt)
also uses a 1.25 expansion as a training margin; that supports investigating the
geometry but does not establish reliability for this converted model.

| Check | Current 1.0 | Experimental 1.25 |
|---|---|---|
| Certified neutral frames | 16/16 | 16/16 |
| Certified overhead frames | 0/16 | 2/16 |
| Clear held fixture, events/rays/ACK | 6/6/6 | 6/6/6 |
| Frontal held fixture | 6/6/6 | 6/6/6 |
| Preserved near-face failure | 1/1/1 | **0/0/0** |
| Original continuous dancing clip | 0/0/0 | 0/0/0 |
| Reflected dancing clip | 0/0/0 | 1/1/1, observation-only |
| New filmed right-arm negative | 0/0/0 | 0/0/0 |

The candidate regresses known partial recognition and still cannot sustain the
350ms hold in the certified overhead window. It was **not adopted**. A separate
in-memory reflection diagnostic, with anatomical labels and x coordinates
mapped back, matched 0/16 overhead frames at 1.0 and 7/16 at 1.25; its longest
correct run spans only 100.1ms. No reflected fallback was implemented, and this
does not create an independently filmed opposite-side trial. No factor sweep,
confidence lowering or gesture-threshold change was performed.

## Repeat locally

The acquired source and selected video are in ignored
`sidecar/fixtures/.cache/natural-controls/`. Use the frozen expectation above:

```sh
mkdir -p verification-results
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python sidecar/verify_video.py sidecar/fixtures/.cache/natural-controls/dvids-551039-right-negative-36s-51s.mp4 --expected sidecar/fixtures/natural-controls/dvids-551039-right-negative.expected.json --output verification-results/natural-right-negative.json
PYTHONDONTWRITEBYTECODE=1 sidecar/.venv/bin/python scripts/analyze-video-motion.py --project . --video sidecar/fixtures/.cache/natural-controls/dvids-551039-right-negative-36s-51s.mp4 --expected sidecar/fixtures/natural-controls/dvids-551039-right-negative.expected.json --output verification-results/natural-right-trace
```

For an opt-in reconstruction, retrieve the normal
[public-player source](https://d34w7g4gy10iej.cloudfront.net/video/1709/DOD_104836154/DOD_104836154-1024x576-1769k.mp4)
to the ignored cache as `dvids-551039-source.mp4`. Check its exact source size and
SHA256 above before encoding. Do not overwrite an existing source or result.
The exact selection recipe is:

```sh
ffmpeg -nostdin -v error -n -i sidecar/fixtures/.cache/natural-controls/dvids-551039-source.mp4 -vf 'trim=start_frame=1079:end_frame=1529,setpts=PTS-STARTPTS' -an -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -threads 2 -fps_mode passthrough -movflags +faststart sidecar/fixtures/.cache/natural-controls/dvids-551039-right-negative-36s-51s.mp4
```

The verifier rejects different selected bytes before inference. Encoder-version
differences must remain explicit mismatches; do not rewrite the frozen hash to
bless a different encode. The generic trace exposes this frame's detector ROI,
rotation and padding, allowing the frozen manual wrist box to be transformed
into model coordinates without saving images. Full traces and rejected-candidate
reports remain local ignored evidence.

## Verified limits and next work

[The scalar milestone record](verification/natural-control-20261020.json)
contains hashes, window comparisons, rejected-experiment results and fresh final
pipeline outputs. All six final baseline fixtures retain their previous game
results. Clear/frontal held inputs still pass the constructed six-event goal;
near-face remains an explicit failure, and both older natural clips remain
observation-only. These constructed fixtures never establish live recognition.

A separate actual-video contract negative deliberately supplied six impossible
zero-millisecond event windows for the constructed clear fixture. Decode,
models, sequence, game and ACK still produced six; timing correctly rejected
all six late events and the CLI exited 1. Those deliberately false times test
the acceptance mechanism only; they are not visual annotations or a recognition
claim.

Validation: **137 Python tests, 55 JavaScript tests, 90 saved-progress checks,
37 synthetic-landmark checks, six synthetic decoder checks, and production build
passed**. Tests use isolated storage; the user's garden was not read or cleared.
No frontend, service or recognition code changed, so the previous 13-case browser
milestone remains historical rather than being claimed as a new run.

The remaining acceptance need is an independently annotated, genuinely filmed
left/right natural positive with adequate neutral and hold intervals, followed
by an actual six-event/ray/ACK run. The certified overhead pose failure also
remains unresolved. No permission or approval is pending. No physical capture,
push, deployment, artifact upload, credential change or purchase occurred.
