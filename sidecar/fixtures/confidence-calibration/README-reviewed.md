# Reviewed calibration pilot v2

Frozen before inference at **2026-10-21T00:46:19.277538+00:00**.

The original V1 manifest, source human annotations, humanGT and split remain unchanged and read-only. V2 preserves all 88 original keypoint manifest and ground-truth rows exactly, including every split, coordinate and visibility value. Only eight background records changed after independent source-pixel review, with four replacements per split.

| Stratum | Calibration | Held-out |
|---|---:|---:|
| All four human joints visible (`v=2`) | 47 | 32 |
| Human-labeled occlusion challenge (`v=1`) | 6 | 3 |
| Independently reviewed clear backgrounds | 20 | 20 |
| Total | 73 | 55 |

## Frozen deliverables

- `manifest-reviewed.json` SHA256 `98ab3ecb0bda14784250bf6639f2f316e641030402154bca1544c271b660cec7`.
- `humanGT-reviewed.json` SHA256 `47c15f65b8517c52754662edc96de862e2fbfc49c2147db4649a96f29875c586`.
- `selection.reviewed.freeze.json` SHA256 `01e9225f09d8b9e14dc5a66c663d88a50f7d2391882dac661d732817ab8bb4de`.
- `background-reviewed.freeze.json` SHA256 `bccf74a215e1832f6a781adcdca201156d02262b83c4f40502e1568f590edb9f`.

`verification-reviewed.json` records all128 original JPEG hashes, lengths/dimensions/integrity checks, exact preservation of88 positive rows, original V1 manifest integrity, and source-image/person-instance/exact-JPEG-SHA split disjointness. Original assets remain under `calibration/<sha256>.jpg`, for both splits. The final manifest contains128 images; unused and excluded source images remain in the folder as preserved evidence and must not be inferred by directory scanning.

## Review provenance and replacement recipe

The prior independent reviewer inspected all40 original background JPEGs. Its final32-clear/eight-exclusion decisions were faithfully transcribed to `original-visual-review.freeze.json` because its original file-write attempt failed when Mac execution disconnected. The file explicitly names the original reviewer, the transcriber and the exact trusted decision message with its SHA256. The transcriber does not claim a new pixel review.

For replacements, the unchanged original583 eligible zero-person-annotation candidates were ranked with the original seed and SHA256 recipe. Reserve global ranks40..51 were frozen before source-pixel review, assigning the first six to calibration and next six to held-out. After conservative independent reviews left one agreed-clear replacement short per split, ranks52..63 were frozen before supplemental pixel review with the same6/6 assignment. Both freeze files remain immutable.

Two fresh model-naive reviewers individually inspected all24 reserve original JPEGs. A candidate is accepted only when both classify it `clear_no_human`; human depictions and any reviewer ambiguity are excluded. Within each split, excluded original IDs in original hash-rank order map to the earliest agreed-clear reserve IDs in reserve-rank order. No model scores, predictions or acceptance outcomes entered selection or review.

| Split | Excluded original | Replacement | Original exclusion |
|---|---:|---:|---|
| calibration | 000000406570 | 000000458790 | ambiguous: Blurred teal upper-left region could be cropped clothing. |
| calibration | 000000495054 | 000000099053 | contains_human: Kneeling hi-vis ground worker; also nose-art woman. |
| calibration | 000000277197 | 000000304545 | contains_depicted_human: Paintings/photos depict people. |
| calibration | 000000263644 | 000000552902 | contains_depicted_human: White human figurine. |
| heldout | 000000098497 | 000000138856 | contains_depicted_human: Surfer silhouette sign. |
| heldout | 000000435880 | 000000439290 | contains_depicted_human: Fridge human photo collage. |
| heldout | 000000355677 | 000000502347 | contains_human: Distant swimmer head/outstretched arms. |
| heldout | 000000371677 | 000000452084 | ambiguous: Tiny monitor avatar unresolved. |

`background-reviewed.freeze.json` binds all40 final background IDs, original JPEG SHA256s, splits, `noPerson: true` decisions, reasons and source-review hashes. It has `modelBlindBeforeInference: true`. Its equivalent `images` and `reviews` arrays support consumers expecting either field. `selection.reviewed.freeze.json` binds this envelope and all source review files; the reviewed ground truth and manifest bind the selection and review hashes.

Human keypoint rows preserve `kind: human-keypoints`; background rows preserve `kind: no-person-annotation`, `stratum: no_person_annotation`, empty joint objects and keypoint arrays and no invented coordinate labels. A zero COCO person-annotation count alone is not used as proof of an empty scene; the separately bound human absence review supplies that evidence.

## Source and local-use limitations

Official COCO source/licensing details and semantic caveats remain in `README.md`, `provenance.json` and original credits files. New reserve sources preserve exact COCO image/license metadata and official public-bucket URLs in `source/replacement-fetch-records/` and `source/selected_coco_reviewed_original.json`. No additional Flickr credit lookups were made; new creator/title attribution remains unresolved. Image licenses follow historical COCO metadata (IDs4/5/8 eligible), and redistribution clearance is not claimed. All downloads were bounded official original JPEGs; no account, credential, upload, model inference, emulator or canonical app write was used.

The positive sample remains a bounded pilot with32 primary held-out images, not evidence for a high-precision production reliability claim. COCO provides person-instance IDs, not persistent physical identity; absence of the same physical person across distinct photographs cannot be certified.

## Reproduction

`prepare_background_replacements.py` without flags verifies or creates the first immutable reserve selection; `--download` retrieves only those fixed originals. `--batch-index 2` verifies or creates the extended immutable pool, and `--batch-index 2 --download` retrieves its missing originals. Existing frozen content is verified and never overwritten.

`transcribe_original_review.py` reproduces the clearly attributed original-review transcription. `finalize_reviewed_dataset.py` takes `--original-review` with its absolute path, four repeated `--reserve-review` absolute paths for the two first-batch and two supplemental reviews, `--candidate-pool` with `replacement-candidates-extended.freeze.json`, and `--candidate-manifest` with `replacement-candidates-extended.manifest.json`. It requires two distinct reviewers per reserve image and refuses insufficient clear candidates or altered frozen files. All finalizer inputs are in this folder.
