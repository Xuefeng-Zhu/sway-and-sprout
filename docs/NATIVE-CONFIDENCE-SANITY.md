# Calibration-only native integration sanity review

No heldout images, predictions or results were read. No model, emulator, build, canonical edit, gate or label change was performed. This review uses only the73 actual calibration outputs and47 primary calibration images.

All73 original JPEG SHA256 values and decoded dimensions match the native records. COCO shoulders5/6 and wrists9/10 agree with the NativeMoveNet required-point order. The predicted-row/GT-column normalized error matrix is strongly diagonal: matching means are .108/.102/.223/.228; cross-joint means are .98–1.68. Mean error is .165 under the actual mapping, versus1.676 after an artificial horizontal mirror and1.818 after x/y swapping. No global index/coordinate integration defect is demonstrated. Prior tensor/crop parity was not repeated.

## Why the frozen gate search cannot qualify

Only10/47 primary images satisfy the frozen **all4 joint errors <=.10 human-GT shoulder span**. Any rule admitting at least20 images must therefore admit at least10 inaccurate images, exceeding the5% error criterion regardless of score threshold. Joint-wise PCK counts are33/47 left shoulder,28/47 right shoulder,24/47 left wrist and27/47 right wrist. Median four-joint minimum native score is .37283; only one primary image clears .65. These are localization/pose admissions, not temporal false-gesture events or deployment error rates.

## Localization and gesture geometry differ

Of32 images with robust human-GT gesture geometry under the frozen error-bound definition,31 have the same predicted class:26neutral,3both-up,1left and1right match; one GTleft is predictedright. Thus a strict PCK failure does not by itself mean a wrong gesture. These observations must not replace the frozen selection metric after results.

Three calibration originals were visually inspected at original resolution, with numeric GT and predictions:

- **280930/421933:** the sole .65-admitted image (minimum .652776) fails only the left shoulder at .116737 GTspan: about11.11px versus9.51px permitted. Its predicted neutral geometry remains correct. All other required joints satisfy .10.
- **96493/451795:** all4 joints are within .10; the right wrist is within8px of its human point but has raw score .293108. Low raw score therefore need not imply an inaccurate point, invisible joint or absent person.
- **128654/432364:** an airborne, strongly rotated pose has large wrist errors consistent with left/right pose confusion. Low raw minimum .148326 rejects it. This is a per-pose model failure rather than evidence of a global array-index swap.

No thresholds are recommended or changed. The selected-none outcome follows the preregistered localization criterion; the model's natural temporal behavior and application scoring remain separate acceptance questions.

`review.json` binds the actual calibration evidence, all73 image/header checks, raw numerical examples and the error matrices.
