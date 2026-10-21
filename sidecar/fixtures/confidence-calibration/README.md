# Independent human-keypoint calibration pilot

This local dataset uses official COCO2017 validation human annotations and original COCO-hosted JPEGs. It is separate from Sway & Sprout's Pexels/DVIDS clips. No pose model was loaded or run, and no predictions, fixtures, production gate thresholds or acceptance results were inspected to build it.

The selection and source-image/person-instance split were frozen at **2026-10-20T18:18:16.109495+00:00**, before inference. The intended 180/120 keypoint sample was infeasible under the fixed source/license/geometry criteria. All 88 eligible keypoint images are retained; this is a bounded pilot with limited statistical precision.

| Stratum | Calibration | Held-out | Meaning |
|---|---:|---:|---|
| `primary_visible` | 47 | 32 | All four target joints have human visibility `v=2` |
| `occluded_v1` | 6 | 3 | At least one target joint is labeled but not visible (`v=1`) |
| `no_person_annotation` | 20 | 20 | COCO has no person annotation; human presence requires separate visual review |
| Total | 73 | 55 | 128 original images, 20,393,475 bytes |

The 88 keypoint images contain 70 lowered-pose and 18 raised-pose examples, defined solely by whether either human wrist y-coordinate lies above the mean shoulder y-coordinate. This geometric descriptor is not an activity or correctness label.

## Files and frozen hashes

- `manifest.json`: native-harness input, `schemaVersion: 1`; each image has `id`, `asset`, `sha256`, `bytes`, `width`, `height`, `split`, `kind` and `stratum`. SHA256 `4fc65ec9056d346d805044150fc4631a7f48ba277788ce67b80e16303a5864e2`.
- `calibration/<sha256>.jpg`: original, unmodified JPEGs for both source-image splits. Directory name does not indicate the image's split; use its manifest field.
- `humanGT.json`: raw target x/y/visibility, full original 17-joint triples, original target bbox and annotation IDs. SHA256 `27385ff3111c1744cda10dfd029bae0ff306edfb6ad87ae324178bb990f64736`.
- `selection.freeze.json`: complete fixed image split, selection policy, ranks and eligibility counts. SHA256 `2db4935d90f0d76b82b5092a77ffde63e15ad5f23001115f3276269b90d711f3`.
- `selection-policy.json`: fixed human-label-only criteria and seed.
- `source/person_keypoints_val2017.json`: exact official validation annotation JSON, 10,020,657 bytes; SHA256 `788e2dae83c86bd547be7fab269d6399df5671063d29a61360cdb2cc370d2b14`.
- `source/selected_coco_original.json`: verbatim source image/license/category/annotation objects for the selected subset. SHA256 `9b1f12941877c2f186fd3b02c2c362b9fba479e94a13057bb5ada6e0c85964fc`.
- `provenance.json`: official URLs, range extraction details, source hashes and license provenance.
- `credits.json` and `CREDITS.md`: per-image copyright/license/source metadata and public-source creator/title lookups where available. Credit completeness limitations are explicit.
- `negative-contactsheet-*.png`: inspection aids made from original pixels only. Separate visual-review labels must not overwrite original COCO annotations.
- `prepare_dataset.py`, `fetch_selected.py`, `create_contact_sheets.py`: reproducible selection, bounded retrieval and inspection scripts; none imports a pose model or accepts predictions.

Raw annotations, selected annotations, selection policy, split, manifest and JPEGs have read-only filesystem permissions. SHA256 values provide the integrity contract; permissions alone are not a cryptographic seal.

## Selection and split

Only COCO image license IDs 4 (Attribution), 5 (Attribution-ShareAlike), and 8 (US Government Work) were eligible. The selected images contain 90 ID-4 and 38 ID-5 images; no ID-8 image was selected. Noncommercial, no-derivatives, unknown and no-known-restrictions categories were excluded.

Each positive source image has **exactly one person annotation**, counting even `num_keypoints=0` and `iscrowd` annotations. The target must be noncrowd, have at least 10 annotated keypoints, have all four shoulder/wrist visibility values at least 1, occupy at least 10% of image area by bbox area, have shoulder span at least 40 original-image pixels, and have all four target coordinates inside image bounds. These checks use human annotations exclusively. All 88 eligible instances were kept.

Within `primary_visible` and `occluded_v1`, records are ranked by SHA256 of `seed:image_id:annotation_id`; the first fixed calibration count goes to calibration and the remainder to held-out. No-person-annotation candidates use `seed:no-person-annotation:image_id`; the first 20 go to calibration and the next 20 held-out, from 583 eligible images. Exact seed and recipe are in `selection-policy.json`.

Source image IDs, positive person-annotation IDs, and exact JPEG byte SHA256s are disjoint across splits. COCO contains person-instance IDs rather than persistent physical-person identities. The same physical person in distinct photographs cannot be ruled out, and near-duplicate scene content has not been exhaustively audited. This is an image/person-instance split, not an independently verified physical-identity split.

## Human ground-truth semantics

[Official format documentation](https://raw.githubusercontent.com/cocodataset/cocodataset.github.io/master/dataset/format-data.htm) defines 0-indexed original-image pixel `(x,y,v)` triples. `v=0` means not labeled (`x=y=0`), `v=1` means labeled but not visible, and `v=2` means labeled and visible. `num_keypoints` counts `v>0`. Bboxes are original `[x,y,width,height]` with top-left x/y.

The target joints are COCO indices 5, 6, 9 and 10: left shoulder, right shoulder, left wrist and right wrist. Left/right use the source anatomical convention. No point was redrawn, inferred, converted to a synthetic model label, or relabeled from a model score. V1 coordinates remain human labels and are not automatically incorrect localizations. V0 coordinates are unknown, not negative localization labels. No-person-annotation entries have no target coordinates and do not assert that an image is empty. COCO's human annotations can still contain annotation error.

## Retrieval, licensing and attribution

The [official download page](https://raw.githubusercontent.com/cocodataset/cocodataset.github.io/master/dataset/download.htm) links `http://images.cocodataset.org/annotations/annotations_trainval2017.zip` (252,907,541 bytes). Only a 65,536-byte archive tail and a 2,986,706-byte ZIP entry were downloaded. Central-directory metadata, uncompressed length and ZIP CRC32 `668491812` were verified. The full archive was not downloaded, so no full-archive SHA256 is claimed. Server ETag and per-range headers are preserved.

Verified TLS retrieval used the same official public S3 bucket as `https://s3.amazonaws.com/images.cocodataset.org/...`, because HTTPS on the original images.cocodataset.org hostname failed hostname certificate validation. TLS verification was never disabled. The actual URL, original `coco_url`, original `flickr_url`, license ID, capture timestamp, dimensions, source IDs, JPEG hash/length, server metadata and retrieval timestamp are preserved per image.

[COCO's published terms](https://raw.githubusercontent.com/cocodataset/cocodataset.github.io/master/dataset/termsofuse.htm) license COCO Consortium annotations under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Image copyright remains with the respective photographers, with individual licenses recorded in source metadata. Do not treat the annotation license as the image license. COCO's download page refers to these published terms; this work used no account, paid resource, click-through registration or uploaded material.

Selected source metadata reports [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) or [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) for each original image. Public original Flickr pages were queried for creator/title attribution without an account or API key. **70 of 128 credits resolved; 21 pages no longer exposed photo metadata and 37 lookups encountered HTTP 429 rate limiting.** Source image URLs and original license records remain available for every image. Eight resolved pages reported current Flickr license IDs different from COCO's historical metadata; these are flagged in `credits.json`. This is not a complete clearance or attribution determination. Review unresolved credits and historical/current-license differences before any redistribution; this task creates local evaluation data only.

Paper credit: Tsung-Yi Lin et al., *Microsoft COCO: Common Objects in Context* (2014), [arXiv:1405.0312](https://arxiv.org/abs/1405.0312). Annotation credit: COCO Consortium. Photographer/title credits, where resolvable, appear in `CREDITS.md`.

## Reproduction and verification

`python3 prepare_dataset.py --policy selection-policy.json` recomputes eligibility counts using source labels only. Adding `--freeze` verifies existing frozen content and refuses to replace it with different content. `python3 fetch_selected.py` verifies cached originals and refuses manifest replacement; fresh downloads are bounded to the frozen records. `python3 create_contact_sheets.py` regenerates the two negative-challenge inspection sheets.

Verification checked every image's JPEG integrity, decoded dimensions, byte length and SHA256, source-ID/annotation-ID/byte-SHA split disjointness, exact raw source-label equality and fixed sample counts. No calibration result or model accuracy is claimed by the data-preparation step. Calibration and held-out inference must be separate, and any fitted candidate must be frozen before held-out predictions are inspected.
