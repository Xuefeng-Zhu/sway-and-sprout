# Frozen natural-motion negative control

See [the source, independent reviews, exact hashes, reconstruction recipe and limitations](../../../docs/NATURAL-CONTROL-VERIFICATION.md).

The public-domain DVIDS551039 source and450-frame contiguous selection stay in the ignored `../.cache/natural-controls/`. Two independent visual reviews preceded inference. Do not edit the frozen expectation hash or expected sequence to match predictions.

`expectedGestures: []` is a wrong-side game negative under the unchanged left-first policy. Its certified natural right-up pose window currently fails recognition. Neither the empty expectation nor its empty timing windows certify a positive gesture or complete goal.
