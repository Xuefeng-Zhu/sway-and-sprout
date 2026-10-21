# Fixed natural-study video fixtures

`study_clips.py` verifies existing clips or explicitly reconstructs candidates from **local, SHA256-pinned inputs**. Python3, FFmpeg with `libx264`, and FFprobe are required. There are no downloads, inference calls or automatic pin updates. Existing files and directories are never overwritten.

| Clip | Fixed source interval | Frames / cadence | Size | Pinned MP4 SHA256 |
|---|---|---|---|---|
| `left-natural.mp4` | DVIDS679690 original frames285–367 inclusive (`[285,368)`) | 83 / 30fps; 640×480 | 1,804,899 bytes | `e4cc461c1c8c162c0f2bd0d256dcd99cd229e997b2ac4175715e34e0240ca8c8` |
| `right-short.mp4` | First156 frames of the pinned existing DVIDS551039 right-negative36s–51s clip (`[0,156)`) | 156 / 30000÷1001fps; 1024×576 | 5,342,215 bytes | `85f473cc8bd8261a2e8046372c01188cc2f3fc6919d9e32e2a52c98aa182f4fa` |

The original selection-before-inference and derivative-verification records are copied verbatim beside the script. Their SHA256s, input pins, output pins and explicit decoded-pixel sequence pins are in `study-clips.lock.json`. `verification-current.json` records fresh successful verification of both existing clips with FFmpeg8.1.1; reconstruction was not run and no derivative was changed.

Run from this directory, supplying local input paths:

```sh
python3 study_clips.py verify \
  --left-source /path/to/679690-source.mp4 \
  --right-source /path/to/dvids-551039-right-negative-36s-51s.mp4 \
  --derivative-dir /path/to/video-fixtures \
  --report /path/to/new-verification.json
```

Use `--case left-natural` or `--case right-short` to verify only one clip and supply only that source. Omit `--report` for stdout only; a report path must not already exist.

To reconstruct explicitly, use the same source arguments with `reconstruct --output-dir /path/to/new-directory`. The output directory must not exist. The recipe trims decoded frames, rebases timestamps, removes audio, and encodes lossless H.264 (`libx264 -crf 0 -preset medium -pix_fmt yuv420p -fps_mode passthrough`). It introduces no spatial crop, reflection, frame duplication, retiming or splicing.

The exact original encoder command was not recovered; embedded metadata identifies FFmpeg8.1.1/libavcodec62.28.101, libavformat62.12.101 and x264core165r3222. **MP4 byte reproducibility across encoder builds or versions is not promised.** Verification requires the pinned MP4 SHA256 by default. Explicit `--allow-container-difference` permits inspection of a reconstructed candidate with a different container SHA, while still requiring the exact pinned decoded YUV420P frame sequence and one-to-one source-frame correspondence. It reports `canonicalPinNeedsExplicitReviewAndUpdate: true` and never edits any canonical pin or existing derivative. Such a candidate requires separate review before adoption.

Each decoded YUV420P frame is SHA256-hashed. The sequence pin is SHA256 of the lowercase hexadecimal frame hashes joined with LF, including one final LF. Source and derivative hash lists must be identical, ordered and exactly83/156 frames long; dimensions and rational frame rate must also match. The older `frameHashSequenceSha256` values are retained verbatim in the lock as legacy metadata, separately from this explicitly defined sequence serialization.

## Credits and study scope

- **Left:** *Kettlebell Overhead Lunge*, Capt. Matthew Holfinger / U.S. Marine Corps Training and Education Command, DVIDS679690, VIRIN190510-M-JT909-020. [Official source](https://www.dvidshub.net/video/679690/kettlebell-overhead-lunge). The archived source page marks PUBLIC DOMAIN; [DVIDS public-use restrictions](https://www.dvidshub.net/about/copyright) apply.
- **Right:** *Dumbbell Snatch*, Capt. Matthew Holfinger / U.S. Marine Corps Training and Education Command, DVIDS551039. [Official source](https://www.dvidshub.net/video/551039/dumbbell-snatch). Existing upstream credits mark PUBLIC DOMAIN with the same DVIDS restrictions. The input is the previously credited right-negative derivative; the reconstruction script does not recreate that upstream450-frame input from a remote original.

The appearance of U.S. Department of War (DoW) visual information does not imply or constitute DoW endorsement.

The text in `canonical-credits-addition.txt` has been applied to the repository debug VIDEO-CREDITS file. These are local diagnostic excerpts. The left clip covers one fixed neutral-to-left cycle; right-short is a wrong-side negative from an already used source, not an independent positive. Blind visual annotations were made by **AI reviewers**, not human annotators. Distinct source asset IDs do not establish person-identity separation. These clips do not certify a natural six-action alternating sequence.
