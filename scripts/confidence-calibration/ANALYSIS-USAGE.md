# Frozen native score analysis

`analyze_calibration.py` is stdlib-only and runs no model, emulator, camera or network. Native image inference and dataset preparation are separate. Read `PROTOCOL-DRAFT.md` and the bound protocol first. Ten synthetic contract tests and a reviewed-v2 data-only validation pass; they do not establish actual model results.

## Select from calibration only

From this directory, substitute the actual calibration result path/SHA and a fresh output directory:

```sh
python3 -B analyze_calibration.py select \
  --protocol protocol-bound.json --protocol-sha256 e446a86e315182eb465e75776a1d9ad288b4120994c5710fed24f66f6bfa4d9a \
  --manifest data/manifest-reviewed.json --manifest-sha256 98ab3ecb0bda14784250bf6639f2f316e641030402154bca1544c271b660cec7 \
  --gt data/humanGT-reviewed.json --gt-sha256 47c15f65b8517c52754662edc96de862e2fbfc49c2147db4649a96f29875c586 \
  --absence-review data/background-reviewed.freeze.json --absence-review-sha256 bccf74a215e1832f6a781adcdca201156d02262b83c4f40502e1568f590edb9f \
  --native ACTUAL-CALIBRATION-RESULT.json --native-sha256 ACTUAL-RESULT-SHA256 \
  --out analysis-calibration
```

The script verifies all73 calibration IDs, images/model/profile/runtime, raw scores/coordinates, invalid masks, completion and cleanup. It writes `analysis.json`, per-image and per-joint CSVs, the18-threshold table and then **publishes `selection.freeze.json` last**. The stdout/report gives the exact selection SHA. The selection may be `null`; that is a valid rejected calibration, not a reason to relax rules. Existing output directories are never overwritten.

## Heldout only after the selection is frozen

Use the same bound input arguments with mode `heldout`, the actual55-image heldout native result/SHA, a new output directory and `--selection PATH/selection.freeze.json --selection-sha256 EXACT-FROZEN-SHA`. The script validates the frozen script/input identities and exact split IDs **before opening the heldout prediction file**. It evaluates only.65 and the single frozen choice; it never searches an alternative grid on heldout. No candidate produces a baseline-only report. Do not modify the analyzer between selection and heldout; its digest is pinned in the freeze.

The four raw native scores remain unmodified. Primary point quality requires all4 joints within.10human-annotated shoulder span; boundary geometry, occluded labels and reviewed no-person false pose admissions remain separate. Output includes each joint's source coordinates, score/error quantiles, admission counts/IDs and exact one-sided95% bounds. A no-person still-image admission is not a gesture event. The statistical unit is source image, never4 joints or repeated video frames. No production or FireTV certification follows from this small image pilot.

Run the synthetic checks without opening any real prediction artifacts:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v test_calibration_analysis
```
