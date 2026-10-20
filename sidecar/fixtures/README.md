# Local public-video fixtures

These two 15.2-second, 10-fps clips contain licensed realistic human imagery.
They use held frames and hard cuts, not natural continuous arm movements. Left
poses are disclosed horizontal reflections of a right pose. They are file-input
fixtures, not human camera tests.

Credit: Artem Podrez, [Pexels video6003772](https://www.pexels.com/video/a-woman-dancing-at-home-6003772/).
The [Pexels License](https://www.pexels.com/license/) permits use and modification
subject to its restrictions. These local testing fixtures imply no endorsement.
No redistribution, artifact upload or publication is part of this task.

The original source is an unmodified 319-frame, 30-fps MP4, SHA256
`d891db0b4b326b5adaa07dbc6af080024ae4ed2e3e3e9c671bf8f75e39708c51`.
Each JSON manifest records source URLs, exact selected frame indices,
transformations, timeline, SHA256, and independent expected gestures.

- `held-public-arm-fixture.mp4`: neutral source frame225; right source frame165
  near the face; mirrored left. Intended six alternating gestures. Actual locked
  model result on2026-10-19: **one left raise and one ray**. This failing challenge
  is preserved. The right wrist prediction was in the shoulder transition band.
- `clear-public-arm-fixture.mp4`: neutral225; right170 with wrist clearly above
  the head; mirrored left. Selected visually before evaluation of this new clip.
  Actual result: **six alternating raises, six rays and completion**. This
  additional clear-pose case does not replace the failed near-face case.

Timeline for both: neutral2.0s, then `(left1.0s, neutral1.2s, right1.0s,
neutral1.2s)` three times. Expected gesture lists were set before model evaluation.

The continuous source and fixture-construction scripts are retained in the local
task's `video-fixtures/` evidence folder. No user/private camera frames were used.
