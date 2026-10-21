# Movement-first garden experience — audit and implementation

The local web experience now completes **enter → move → see garden growth →
confirm participation → harvest → grow again**. This pass used the rendered app,
then changed the implementation and checked the same journey again. It is a local
interaction test, not evidence of a person moving or a camera recognizing them.

The user's goal is comfortable activity, without prescribed poses or side order.
Manual play remains usable without a camera. Existing strict recognition and
recorded-video diagnostics remain available separately.

## Scope and evidence

The initial audit used an isolated local origin in Chrome at 1280 × 720. The
in-app browser was unavailable. Screenshots below were captured in this audit,
saved, and inspected. The three baseline screens precede these UI changes. The
baseline activity could not reach completion: an actual animation-clock exception
left it at 30 seconds. Completion was captured after that defect was fixed.

The numbered screenshots are in the sibling task folder `ui-audit-20261021/`;
automated screenshots, geometry, console records and source hashes are in
`journey-browser-qa/`. These operational artifacts are intentionally outside Git.
The automated browser fixtures use disposable storage, mocked semantic packets
and mocked previews. They deny external requests and never open a camera.

## Findings and fixes

| Priority | Finding | Evidence and resulting behavior |
| --- | --- | --- |
| P0 — functional | The initial RAF timestamp can precede the click's `performance.now()`. The new timestamp guard in `25abbd3` threw and stopped the countdown. | Observed in Chrome's error log during the baseline audit. The round now establishes its baseline from its first RAF callback, including after resume. The 250 ms frame-credit cap remains unchanged. A deterministic test covers the earlier first timestamp and exclusion of paused time; the real browser countdown advances. This does not establish the earlier emulator slowdown's cause. |
| P1 — functional | A recorded diagnostic with no packet could reach ordinary self-report. Synthetic results also shared the ordinary reward surface. | Source review and actual-main tests. Video origin is latched at Start; synthetic/video results say the saved garden is unchanged and offer replay/return only. Manual fallback inside a simulated round retains its test origin. |
| P1 — functional | Growing again erased saved blooms; leaving before harvesting could hide the unclaimed reward. | Source review, deterministic tests and the rendered journey. Saved blooms now survive replay. Home keeps an unclaimed harvest available. Harvest can be claimed once per visit. |
| P1 — functional | Help lost setup/check context. An inactive diagnostic response could relabel an ordinary reward after returning. | Help now returns to its previous screen, with play paused. A late inactive response releases its client without relabelling a manual screen. Actual-main regression tests cover the response race and retained harvest. |
| P2 — interaction | Manual play gave a countdown and decorative symbol, without immediate garden feedback. | Baseline activity screenshot. An explicit **Count my movement** action now produces six bounded, visible plant stages. It is labelled self-reported play. Counting and elapsed time do not save participation; the player confirms the moment. |
| P2 — layout | Intermediate confirmation artwork pushed the footer below the TV viewport. Automated QA also found 20 px of paused overflow and 6 px of strict-diagnostic overflow. | Artwork size and spacing were corrected. Final affected 1280 × 720 screens fit their controls and footer without shrinking the body copy. Original failed geometry/screenshots remain in the QA records. |

The visual changes below are design judgments rather than objective correctness
claims. The fully bloomed backdrop, repeated decorative symbols, radial halos and
large rounded cards made the garden feel like a poster. They were replaced with a
consistent local illustration whose seeds, sprouts and blooms reflect counted or
confirmed progress. The green/cream/lime palette and warm flower colors remain.
Plain controls, stable typography and concrete copy give movement and growth more
visual weight than decoration. No new asset service, font download or package was
used. This is a scoped improvement, not a claim that all aesthetic judgment can be
reduced to an “AI slop” test.

## Captured journey

1. **Enter — healthy.** The empty garden visibly contains seeds; the primary
   action starts a visit. Earned blooms are visible when returning.

   Before:
   ![Original home](../../ui-audit-20261021/01-before-home-720.jpg)

   After:
   ![Movement-first home](../../ui-audit-20261021/04-after-home-720.jpg)

2. **Get comfortable — healthy.** Seated/standing choices remain explicit.
   Manual play explains how to count a movement and confirm participation.
   Camera sunshine remains opt-in, with local-processing and camera-off copy.

   ![Manual setup](../../ui-audit-20261021/05-after-setup-720.jpg)

3. **Activity — healthy in the tested manual/mocked paths.** A small wave,
   stretch, reach or sway is suggested, with no required pose or side order.
   Manual counts show immediate growth and stop at six. Pause disables counting
   and freezes credited time; Resume starts a fresh clock baseline.

   Before:
   ![Original activity](../../ui-audit-20261021/03-before-activity-720.jpg)

   After three manual test inputs:
   ![Visible counted growth](../../ui-audit-20261021/06-after-three-manual-counts-720.jpg)

4. **Confirm and see the saved change — healthy.** Counting never silently
   becomes saved participation. Explicit confirmation adds the bloom. Camera
   recognition and self-report remain distinct; test input cannot add a bloom.

   ![First saved bloom](../../ui-audit-20261021/09-after-first-garden-bloom-720.jpg)

5. **Harvest — healthy.** Tending all three distinct moments during the visit
   makes the local garden reward available. It is a garden illustration, with no
   inferred fitness, calories, streak pressure or claimed recognition accuracy.

   ![Completed local harvest](../../ui-audit-20261021/12-after-harvest-720.jpg)

6. **Return, repeat and interrupt — healthy within the tested scope.** Growing
   again keeps saved blooms. Home preserves access to an unclaimed harvest;
   Help returns to context; Back first pauses and then returns home. Reload keeps
   earned blooms. Active counts and the current visit ledger remain in memory;
   reload starts a new visit rather than resuming an unfinished round.

   ![Saved garden after growing again](../../ui-audit-20261021/13-after-grow-again-keeps-blooms-720.jpg)

## Accessibility observations and limits

The app retains semantic buttons, visible focus outlines, spatial arrow-key
navigation and Enter selection. Pause/Resume receives deliberate focus; changing a
setup choice keeps focus on that choice. Disabled counting is excluded from
directional navigation. Growth has text as well as color/illustration, and reduced
motion is supported. The 720-pixel layout uses 46 px headings, 24 px body copy,
28 px cues, and generally 16–18 px secondary labels.

Browser geometry and keyboard checks support these observations. They do not
prove screen-reader compatibility, full WCAG conformance, physical remote
behavior, or readability at every viewing distance. Natural movement recognition,
the previous video decode slowdown, and physical Fire TV behavior remain outside
this web audit. At 960 × 540, the strict diagnostic screenshot is 741 pixels
high: it scrolls, and its legacy bottom-only assertions do not prove whole-screen
fit. The stronger 720/1080 journey guards pass. No new public footage was downloaded
or analyzed.

The Mac locked after the visual captures. Closing the task-created Chrome audit tab
(and resetting its temporary viewport) could not be confirmed; that desktop cleanup
requires unlocking the Mac. The task-owned preview server, automated test browsers,
emulator and synthetic service are stopped.

## Verification

- Actual Chrome manual interaction: three moments, confirmation, harvest,
  growing again and retained blooms were captured above.
- **114 Node tests pass**, covering the actual app's timing/navigation/persistence logic, the
  activity reducer, diagnostic contracts and bounded illustration stages.
- The separate preservation harness retains the original saved bytes and object
  identity for simulated completion across 90 checks.
- **Five portable journey cases and 13 legacy mocked motion case assertions pass**. The legacy run reached its 120-second global deadline after 11 passes; the two unexecuted layout cases passed in a separate targeted run. The original deadline/teardown errors are retained rather than reported as a successful whole run.
- Automated browser records include full manual flow, interruptions, mocked
  scoring/ACK/duplicate handling, simulated fallback, unavailable input, strict
  diagnostics, reduced motion and responsive layout. Test inputs do not establish
  model or native runtime accuracy.
- Production web build passes using existing dependencies.

The final counts and source/artifact hashes are recorded in
[the verification manifest](verification/ui-experience-20261021.json).
The separately built `25abbd3` APK predates these UI changes. Its single bounded
emulator attempt did not reach active input; see
[the exact incomplete probe outcome](BOUNDED-PROBE-20261021.md).
