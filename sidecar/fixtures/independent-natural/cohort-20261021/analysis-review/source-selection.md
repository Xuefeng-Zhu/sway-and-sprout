# Source selection and limits — frozen independent natural-video cohort

The frozen cohort contains **three contiguous clips, 593 frames, and zero definite positive event opportunities**. It supports preliminary negative/challenge diagnostics; it cannot establish event recall, positive timing accuracy, natural alternating-gesture reliability, or a reason to port a candidate model. Labels are model-blind **AI visual annotations**, not human ground truth, user-supplied labels, or user-approved labels. Different credited productions establish source-group separation, not verified performer identity or statistically independent people.

This note was compiled after cohort freeze from the existing provenance, selection, annotation and proof artifacts. It does not change them or use inference outcomes to justify source selection. The whole-cohort plan [execution-plan.freeze.json](../execution-plan.freeze.json), frozen at 2026-10-21 04:46:56 UTC, has SHA256 `fb84346ad034457d469ff7963f54ec3e518be2675f39ac7aedfbf37cf389f73b`.

## Exact sources and usage evidence

| Case | Original public page and credited production | License evidence recorded before visual selection | Evaluated source interval |
|---|---|---|---|
| both-press | [Kneeling Overhead Press - Fitness Workout, DVIDS768147](https://www.dvidshub.net/video/768147/kneeling-overhead-press-fitness-workout); Petty Officer 2nd Class Robert Price / AFN Sasebo; credited instructor Kelly Stratoti | Official asset page explicitly marks **PUBLIC DOMAIN**; [DVIDS public-use restrictions](https://www.dvidshub.net/about/copyright) apply. [Archived asset HTML](../discovery-source-b/dvids768147-page.html), SHA256 `038ae7c668384fcd8c6ed498302e9d4fe75e1bad069139d597fd3b60960aaa7c`; [URL/license preflight](../discovery-source-b/dvids768147-source-preflight.json). | Source frames [180,390), 6.006–13.013 s, 210 frames at 30000/1001 fps, 1024×576. |
| both-stretch | [Woman Stretching Her Arms, Pexels7628775](https://www.pexels.com/video/woman-stretching-her-arms-7628775/); ArtHouse Studio | Official asset Free-license link to the [Pexels License](https://www.pexels.com/license/), recorded in [asset snapshot](../discovery/metadata/pexels-7628775-web-snapshot.txt), SHA256 `76b99e3fb121561b1be154955b07845d309f4a1e5600c537a53b449fe457c44a`. Official license text is in the shared [page/license snapshot](../discovery/metadata/pexels-4586958-web-snapshot.txt), SHA256 `9d893f945c1596dec4952c5be9a63bff5f4e2b826b543d8a62d338bd31b34334`. | Source frames [0,188), 0–7.520 s, 188 frames at 25 fps, 1080×1920. |
| cross-stretch | [A Woman Stretching her Arms in the Street, Pexels8401267](https://www.pexels.com/video/a-woman-stretching-her-arms-in-the-street-8401267/); RDNE Stock project | Same official [Pexels License](https://www.pexels.com/license/); [asset snapshot](../discovery/metadata/pexels-8401267-web-snapshot.txt), SHA256 `4d3d01532d17ddbc19cd8d6dbaea85a7539502d50d646d5f30035d5b6118ddb2`; same separately pinned shared official license snapshot above. | Source frames [150,345), 5.000–11.500 s, 195 frames at 30 fps, 1920×1080. |

Direct media URLs, preserved as source bytes:

- both-press: https://d34w7g4gy10iej.cloudfront.net/video/2010/DOD_108006492/DOD_108006492-1024x576-1769k.mp4
- both-stretch: https://videos.pexels.com/video-files/7628775/7628775-hd_1080_1920_25fps.mp4
- cross-stretch: https://videos.pexels.com/video-files/8401267/8401267-hd_1920_1080_30fps.mp4

The three asset IDs and credited production groups differ from the old DVIDS679690 kettlebell clip and its Capt. Matthew Holfinger / U.S. Marine Corps Training and Education Command exercise-production group. They are also outside the other excluded prior DVIDS, Pexels and Taco Fleur groups in [excluded-prior-sources.json](../discovery/excluded-prior-sources.json). None is a recut of the old kettlebell video. No facial matching, biometric analysis, or cross-video physical-person identity verification was performed. The two Pexels credits are distinct creator groups; that does not prove distinct shoots, participants, or population independence.

## Transformations and verification

There are **three evaluated derivatives: one contiguous temporal interval per source**. Each uses lossless H.264/yuv420p encoding, omits audio, and uses a zero-based display clock while preserving source cadence. There are **zero spatial resizes/crops, zero mirrors, zero retimes, zero splices, and zero inserted/repeated frames** in these evaluated video files. Review contact sheets, enlarged regions and model input preprocessing are separate from the evaluated source derivatives.

All **593/593 ordered decoded YUV420p frames** were compared with their exact selected original frames. CFR/PTS checks and source-frame maps are pinned in [both-press verification](../cases/both-press/derivative-verification.json), [both-stretch verification](../cases/both-stretch/derivative-verification.freeze.json), and [cross-stretch verification](../cases/cross-stretch/derivative-verification.json). Frame-count durations sum to **21.027 s**; this is not a certified negative-exposure denominator. Negative coverage and uncertain intervals must use the frozen cohort's declared sample policy. Different encoders can produce different container bytes despite identical decoded pixels; current derivative hashes are pinned.

The both-press draft was shortened from [180,480) to [180,390) for a pre-inference native execution-time budget; the superseded 300-frame draft was retained for traceability. This was not an outcome-driven trim. Other source offsets are fixed in the case records. No transformed, repeated, or assembled gesture sequence is presented as a naturally filmed alternating sequence.

## Bounded search and rejection scope

The discovery branches screened **nine downloaded media assets: five DVIDS and four Pexels**, using official metadata/license evidence and source pixels before model inference. Three became the frozen challenge cases above. The remaining six did not establish a clean positive:

- DVIDS809463: training montage, multiple people, weapons/body occlusion and cuts.
- DVIDS74422: overlapping crowd, backs and multiple plausible targets.
- DVIDS846626: vehicle/body occlusion and cuts.
- DVIDS992978: opposite wrists behind backs/out of frame in close shots; distant/back views and dissolves later. Only its official modest HLS rendition was retained; the 111 MB original was not downloaded.
- Pexels4586958 (Ketut Subiyanto): greeting/wave, but the opposite wrist is cropped in inspected samples.
- Pexels8391684 (Los Muertos Crew): alternating side bends, with raised/supporting wrists cropped.

The retained Pexels7628775 has bilateral stretching, and Pexels8401267 has cross-body stretching; neither established the requested sustained single-arm positive. DVIDS768147 is bilateral pressing with asynchronous/uncertain transitions. Sparse discovery overviews do not prove that an entire rejected source contains no useful frame; they did not justify declaring a clean positive under the contract.

Additional bounded metadata/access checks did not enlarge the cohort: Commons T.Fleur_Lift was excluded as the prior Taco Fleur production; two Commons shoulder-press assets had pending external-YouTube license-review claims and no established positive advantage, so were not downloaded. Official Pexels7320032 media returned HTTP403 and was not bypassed. A final Commons Ricardo Morte conference-video poster showed cropped wrists/multiple tiles; the large video was not downloaded or exhaustively screened. No account, new terms, installation, payment, credentials, camera capture, or uploads were used. Discovery stopped after the parent's bounded further-candidate limit. These records describe search yield, not an exhaustive survey of public footage.

Exact candidate URLs, original-byte hashes and historical decisions are preserved in [DVIDS/Commons discovery log](../discovery-source-b/DISCOVERY-LOG.json), [Pexels discovery log](../discovery/research-log.pexels.freeze.json), and [last poster screen](../discovery-last-positive/screening-result.json). Their stage-specific wording remains unchanged.

## Why no definite positive; both-press reference derivation

The contract requires observable neutral, the expected wrist above its shoulder margin with the opposite wrist down, continuous 350 ms hold, and the existing state-machine arming/reset rules. Human-visible geometry is kept separate from model confidence. Frozen AI joint bounds, occlusion and transition uncertainty do not certify any positive opportunity across these clips. Thus positive recall and event timing agreement have no definite denominator. The both-stretch and cross-stretch whole-event references remain **null**, with only their certified negative subsets and explicit uncertainty available for evaluation. Zero model events on them cannot, by itself, be called correct whole-clip recognition.

The original both-press [case.proposal.json](../cases/both-press/case.proposal.json) and [annotations.proposal.json](../cases/both-press/annotations.proposal.json) conservatively kept `expectedSequence: null`; both remain byte-for-byte unchanged. Before model inference, an independent reviewer recomputed every original joint-region row and exhaustively applied the **literal current GestureMachine.update** to a relaxed superset of all allowed physical gate combinations. The [derived-zero-proof.json](../cases/both-press/derived-zero-proof.json), SHA256 `130f99b837ef6975c59926fa525cf0cf9b915406f944bdfca343e4ec806ad773`, checked **7,444 transitions** and returned event-count bounds **[0,0]**; [region binding](../cases/both-press/derived-zero-proof-region-binding.json) confirms all 210 original rows are unchanged.

The key temporal constraint is that frames85–91 force disarming. Fresh neutral can begin92 and arm101 after300.3 ms; a new hold starts no earlier than102 and reaches only66.7 ms by104 before105 forces disarming again. Other relaxed left-correct runs are at most200.2 or333.7 ms, or isolated. No first-left event can occur within the annotated superset. The final [case.freeze.json](../cases/both-press/case.freeze.json), SHA256 `41d2a0b2938a213233531a1af02e4b81404b93a8934bef87705893ac0c35ef5a`, therefore pins a separate **derived** `expectedSequence: []`. It does not relabel joint bounds, erase the original null proposal, apply model confidence to physical labels, or claim human-confirmed truth. The proof is conditional on the AI visual regions; synthetic arithmetic checks are not natural-video inference results.

The remaining concrete input gap is new, rights-cleared natural footage whose neutral-to-single-arm raises and opposite-down/hold conditions can be adjudicated independently, preferably across multiple production groups and people. This cohort alone cannot demonstrate an improvement on the unresolved positive-recognition failure or establish Fire TV hardware performance.
