# Current source and asset provenance

## Licensing update, 2026-10-23

Project-authored source and documentation are licensed under the root MIT
License, selected with owner approval on October 23, 2026. Original
project artwork remains included. Third-party code, model/runtime dependencies
and optional test media keep their original licenses and notices. Optional
licensed media and model binaries remain ignored and are not relicensed by the
project license. Historical licensing statements below record the earlier
repository state.

## Sway & Sprout migration, 2026-10-20

The renamed app preserves the original TogetherMove compatibility identifiers and authored source. The new private source repository includes current local-motion code and tests; generated caches/builds and historical emulator logs are excluded.

The original web garden artwork and favicon remain covered by the historical authored/generated account below. The new native launcher wordmark is authored SVG typography, rasterized locally; it introduces no stock imagery or bundled font file.

The motion prototype additionally contains two vendored OpenCV Zoo Python wrappers and their preserved Apache-2.0 notices. `sidecar/models.lock.json` pins Zoo commit `47534e27c9851bb1128ccc0102f1145e27f23f98`, upstream URLs, byte counts, and SHA-256 for the wrappers, notices and optional model downloads. ONNX models are restored locally by `fetch_models.py` and are excluded from Git. This current source inventory supersedes any blanket historical claim that no external code or assets were fetched.

Optional test footage derives from Artem Podrez's [Pexels video 6003772](https://www.pexels.com/video/a-woman-dancing-at-home-6003772/) under the [Pexels License](https://www.pexels.com/license/). Media remain ignored local inputs; only provenance, fixed expectations, annotations, reconstruction tools and sanitized public-file results are committed. They are not public domain, CC0, Apache-licensed stock media, or evidence of user camera recognition. Repeated frames, hard cuts and reflected poses are explicitly disclosed.

No user camera frames or browser storage are committed. No project-wide open-source license was selected during migration. Third-party license notices remain intact.

## Historical original export account

The following text describes the original authored web prototype, before the local motion additions. Its old product name and historical statements are retained as a scoped record.

# Provenance

Created on October 15, 2026 for TogetherMove. Source, challenge prompts, styling, native wrapper, tests, banner and vector icon were authored for this project with AI assistance. No pre-existing project code was copied.

`artifacts/design-concept.png`: built-in OpenAI image generation, full-screen design concept. Brief: premium Fire TV home screen, midnight forest, cream large text, lime CTA, coral/gold/lavender botanical garden; left heading “A little movement. A lot of together.” and three lower challenge cards.

`public/garden.png`: built-in OpenAI image generation, original decorative artwork. Brief: 16:9 paper-cut forest diorama, right-side terracotta bowl with coral poppy, smiling golden sunflower and lavender flower, left negative space, no text or logos. No uploaded or third-party reference artwork was used.

Fonts: system Trebuchet MS/Arial fallbacks, not redistributed. Banner raster generated with locally installed DejaVu Sans; no font file is bundled. Unicode symbols are decorative system glyphs, not third-party sprites. No music, video, user photographs, trademarks, or external asset fetches.

Build dependencies: Vite (MIT), Playwright (Apache-2.0), transitive dependencies listed in package-lock.json. Gradle 8.9 and Android SDK command-line tools were downloaded from their official sources and checksum-verified after authorization; SDK platform 35 and build tools 34/35 were installed. SDK Preview terms were separately approved for the Android TV test image. Toolchain downloads, caches, generated keys and emulator images are excluded from source. No open-source license for the project has been selected on the user's behalf.

Official references consulted October 15, 2026:
- https://amazonappdev2026.devpost.com/
- https://amazonappdev2026.devpost.com/rules
- https://amazonappdev2026.devpost.com/resources
- https://developer.amazon.com/docs/fire-tv/remote-input.html
- https://developer.amazon.com/docs/fire-tv/getting-started-developing-apps-and-games.html

## Optional local Full-model evaluation

Google MediaPipe1.1.1 and its official Full Pose Landmarker task are pinned
separately by exact wheel/model hashes. The model card marks the models
Apache-2.0; installed wheel licenses/notices remain local with the isolated
environment. See [the Full report](MEDIAPIPE-FULL-VERIFICATION.md) for original
Google sources, graph/confidence semantics, telemetry/network policy and rejected
Heavy/Apple Vision comparisons. No exact Lite/Full/Heavy identity is invented for
the older Zoo ONNX artifact. Model binaries and all evaluation venvs stay ignored.

The newer both-up negative derives from Taco Fleur's
[Kettlebell Suitcase Row and Press](https://commons.wikimedia.org/wiki/File:Kettlebell_Suitcase_Row_and_Press.webm),
CC BY-SA4.0 with item-specific VRT confirmation. A contiguous trim/rebase/re-encode
removes audio; there is no reflection, retiming or duplicated hold. Retain creator,
source, license and modification notice in the frozen annotation and Full report.
The media is ignored and was not published. Metadata-only MEVA research and a
rejected flag-wave source are not positive recognition evidence.
