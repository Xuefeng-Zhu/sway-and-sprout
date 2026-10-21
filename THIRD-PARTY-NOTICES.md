# License scope and third-party notices

The root [MIT license](LICENSE), copyright 2026 Xuefeng Zhu, applies to
owner-authored project code and documentation. It does not replace a file's
existing third-party terms or license model weights, media, dependencies or
operating-system images. Repository visibility remains private; adding a license
does not publish the repository or authorize distributing test artifacts.

- **OpenCV Zoo wrappers:** `sidecar/vendor/mp_persondet.py` and `mp_pose.py`
  retain the Apache-2.0 licenses alongside them. Exact upstream revision, hashes
  and corresponding model sources are in `sidecar/models.lock.json`.
- **TensorFlow-derived crop code:**
  `android/app/src/main/java/com/togethermove/tv/MoveNetCrop.java` retains its
  TensorFlow Authors copyright and Apache-2.0 header. The full license and
  attribution remain in `android/app/src/debug/assets/third-party/`.
- **Diagnostic runtimes and weights:** LiteRT, Support API and MoveNet terms,
  exact sources and hashes remain in `android/native-video-assets.lock.json`
  and the existing third-party notices. OpenCV Zoo and optional model artifacts
  retain their respective source licenses. None of these weights or runtime
  binaries is relicensed by MIT or added to this repository by this change.
- **Dependencies:** npm package licenses remain recorded in `package-lock.json`;
  Python and Android dependencies retain their upstream terms. Preserve their
  license and attribution files when distributing a build. Android SDK/system
  images and other local toolchains are outside this project's MIT grant.
- **Taco Fleur video:** the existing Kettlebell Suitcase Row and Press excerpt
  is a derivative of [this Wikimedia Commons source](https://commons.wikimedia.org/w/index.php?title=File:Kettlebell_Suitcase_Row_and_Press.webm&oldid=1004642243),
  licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
  Its exact identity, credit and frame-trim/re-encoding changes remain in
  `sidecar/fixtures/natural-controls/suitcase-both-up-negative.expected.json`.
  The media stays excluded from Git. If an adaptation is distributed, retain
  attribution/change notices and comply with ShareAlike; MIT does not cover it.
- **Other historical footage:** Pexels, uncleared DVIDS and unlicensed YouTube
  material is not cleared for new analysis or publication. Historical manifests
  and credits are provenance, not a new permission grant. Do not include those
  clips, frames or diagnostic APKs in a release merely because code is MIT.

Project-authored CSS/SVG garden art is part of the project code. No third-party
art, photo, font, footage or model becomes MIT by appearing in a screenshot or
being referenced in a manifest. Check each artifact's source terms before any
future public distribution. This notice records scope; it does not assert that
every possible release bundle has been cleared.
