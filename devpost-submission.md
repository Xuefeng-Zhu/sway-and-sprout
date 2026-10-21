# Sway & Sprout

**A small movement. A growing garden.**

### ⏳ Not submitted yet

Nothing has been sent to Devpost. This draft describes the local prototype for
**OpenCV AI Competition 2026, powered by AWS**. A useful AWS component still needs
to run, current code must reach reviewers, and the demo is unfinished.

## Inspiration

The first version concentrated on recognizing a particular arm raise. That made
the movement rules more important than the reason for playing. The goal changed:
give someone a reason to move a little, in a way that feels comfortable.

A garden made sense for that. A wave, a small stretch or a sway can help something
grow. There is no prescribed left-right order or exact pose to hold. The player
can sit or stand, pause, and come back.

## What it does

Sway & Sprout has three short moments: wake the garden, catch the sunshine and
make some rain. The player starts with seeds, sees a sprout grow during activity,
confirms the moment, and gathers a basket after tending all three. Earned blooms
stay saved when the player starts again.

Manual play works without a camera. The player presses **Count my movement** and
sees the next plant stage. The interface calls this self-reported play. A button
press does not establish that the game saw a person move.

Sunshine also has a local recognition path. Its activity policy looks for changes
in confident wrist or torso landmarks. Either arm, both arms or a small sway can
contribute. Smoothing, noise and jump rejection, cooldowns and a six-count limit
bound the credit. The policy has deterministic tests; broad natural-movement
reliability remains unverified.

An optional web backup flow saves and restores only confirmed garden progress.
It is off by default and makes no request until a valid endpoint is configured
and the player explicitly chooses an action. The backend and client work in
local tests. No AWS endpoint is deployed, and backup is disabled in the current
Android host.

## How it was built

The interface uses JavaScript, CSS and code-drawn garden artwork, built with
Vite. Keyboard and remote navigation have visible focus. Progress stays in local
storage. The Android host displays the interface in a WebView.

The Mac vision service uses **OpenCV 5** for person detection and pose estimation
with pinned OpenCV Zoo ONNX models on the CPU. It verifies model hashes, maps
outputs into landmarks and passes activity events to the game. It can produce a
small annotated preview in memory. Camera capture is opt-in.

A bounded test used an existing, licensed video excerpt through the actual
OpenCV service and game modules. All **136 frames** reached inference and EOF.
Three activity events became **three rays, growth 0.5 and ACK 3** in the actual
main/reducer/view functions running in a VM. The run took **5.579 seconds** of
processing and made **zero saved-participation writes**. It did not render a
browser or emulator, finish a round, or measure recognition accuracy. The clip
has no newly annotated activity count, so three events are not three verified
correct movements. Source and model hashes are preserved in the evidence.

The separate Android video diagnostic uses LiteRT/MoveNet. It is not OpenCV on
Fire TV. Generated landmarks test scoring and acknowledgements; generated
geometry video tests packaging or throughput, not human recognition.

The planned AWS service uses API Gateway HTTP API, Python Lambda and DynamoDB.
Only completed-moment IDs and a harvest counter leave the device after opt-in;
frames, landmarks and audio stay out of that API. Random capabilities, conditional
writes, generation/version checks and bounded deletion tombstones protect each
backup. Local tests cover retries, conflicts, ownership, expiry and offline
failure. **Implementation is complete locally; AWS execution is not.** The
competition's requirement to run a meaningful component on AWS remains open.

## Challenges

Changing the movement goal meant separating gameplay from the old strict-pose
diagnostics. Those diagnostics remain available, but their prescribed movements
no longer define the game's acceptance rules.

OpenCV 5 exposed a model-wrapper integration issue: output order differed from
the wrappers' assumptions. An adapter now matches unique tensor shapes before
passing outputs to the unchanged wrappers.

Testing also found an initial animation timestamp that could stop the countdown,
replay that could erase saved blooms, and screens that did not fit a 960×540 CSS
viewport. Those were fixed and checked. Backup review caught an expiry/recreate
race; generation-aware writes and deletes now have regression tests. The older
windowed replay that accepted only 8 of 188 frames remains a separate unresolved
failure. The successful Mac file run does not explain or fix it.

## Accomplishments

The complete manual loop works in the browser and a windowed Android TV emulator:
enter, count activity, see growth, confirm, harvest and play again. The native
record passed **32 layout checks** at source `f23f9e7`, including interruptions
and saved-garden reload. It used automated manual input with camera and microphone
off. It is historical UI evidence, not verification of the newer backup feature.

Current verified local results include **151 Node tests, 168 sidecar Python tests, 90 progress checks,
33 backend tests and 12 permitted-runner tests**. The Node suite includes backup client/UI checks. The build passed with existing dependencies. The full sidecar suite passed after existing models were linked. Earlier Java
verification recorded 1,067
assertions; that is a prior result, not a new rerun. None of these totals measures
user impact or recognition accuracy.

## What was learned

Visible plant growth and explicit confirmation make the intended progression
concrete. Keeping the input source visible also matters: manual participation,
detected activity and test data need different labels. A functional video-to-game
result is useful, but it cannot answer whether a person understands or enjoys
the experience. That still needs observation.

## What's next

Finish the bounded native diagnostics and an honestly labelled demo. Expand
permitted movement and neutral-input evaluation before making accuracy claims.
Test actual people and physical Fire TV hardware only with the necessary access
and consent. Separately approve and verify a small AWS pilot, or do not claim this
local build meets OpenCV26's cloud requirement. No deployment or spend is approved.

## How AI and Codex were used

Pose models provide landmarks; no conversational model runs the game. Codex
helped implement the activity policy, garden flow, backup and local test harnesses.
It reviewed rendered screens, investigated failures and added regressions. Its
tests and generated inputs are development evidence, not human validation. Coding
assistance alone does not make this an Agentic Vision award entry.

## Built with and licensing

JavaScript, CSS, SVG, Vite 6.4.1, Python, OpenCV 5.0.0
(`opencv-python-headless` 5.0.0.93), NumPy 2.5.4, OpenCV Zoo ONNX models,
Java/Android WebView, LiteRT 1.4.2 and MoveNet for separate Android diagnostics,
Node tests and Playwright. API Gateway, Lambda and DynamoDB are implemented as an
undeployed backup design. COOL is not used.

Owner-authored code and documentation are MIT licensed, copyright 2026 Xuefeng
Zhu. `THIRD-PARTY-NOTICES.md` preserves separate dependency, wrapper, model and
media terms. The permitted Taco Fleur excerpt is CC BY-SA 4.0; it is excluded
from the source/package, and MIT does not cover it. The repository remains private.

Current code checkpoint: `3a301733a5b0deabd3834b1a7cbc2f17ab0167a9`
(license commit `97f4a4a`, then backup). Final documentation/source identity will
be recorded in the regenerated package manifest after private-push verification.

## Official form copy and links

| Field | Draft value / action |
| --- | --- |
| Title | Sway & Sprout |
| One-line summary | A small movement. A growing garden. |
| Repository URL — required, ID 28209 | https://github.com/Xuefeng-Zhu/sway-and-sprout — private. Reviewed changes on `work/activity-progression` are awaiting the authorized private push and remote-SHA verification. Judge access is not arranged. |
| Testing instructions — required, ID 28210 | Use `REVIEWER-GUIDE.md` from the supporting package after confirming the exact source. It separates manual play, file inference and local backup tests. |
| Working web endpoint — optional, ID 28211 | Missing. An arranged live screen-share is an allowed alternative; none is arranged. |
| Video | Missing. Prepare a public or unlisted judge-accessible video of at most five minutes. No upload is authorized. |
| ZIP | Supporting draft only. Use the supporting package manifest for its exact source and remote checkpoint. |
| Special Award Consideration — optional, ID 28208 | Leave unselected. No COOL-on-Graviton or qualifying agent workflow is evidenced. |

The checked form has no required tool-feedback or Codex-session-ID question.
Optional factual notes are in `TOOL-NOTES.md`.

## Testing instructions

Manual play needs no camera, Python, model, account or credentials. From the
current source with locked Node dependencies available, run `npm run dev` and
open `http://127.0.0.1:4173`. Select **Start growing**, choose seated or standing,
and keep **Manual play** for Sunshine. Count six chosen movements, finish and
explicitly confirm each moment. Harvest, grow again, and reload to check saved
blooms. Arrow keys move focus; Enter selects; Space pauses; Escape/Back pauses
before leaving. Do not enable capture to review the interface.

The permitted file run has a separate preflight and explicit bounded execution
recipe in `docs/MOTION-TO-GARDEN-20261021.md`. It requires the exact existing
licensed clip and pinned local models. It is not a general download recipe.
Backup tests use injected storage and mocked transport; no AWS credentials or
shared database are needed. A normal unconfigured build sends no backup requests.

## Screenshot and demo materials

Four unedited native screenshots show entry, three manual counts, harvest and
saved-garden reload. They come from source `f23f9e7`, temporary test storage and
automated manual input. They do not show detected motion or the newer backup UI.
`SCREENSHOTS.md` retains their provenance and hashes. The old package manifest
and ZIP await regeneration. No complete demo recording exists yet.

## Readiness and sources

The supporting `JUDGING-GAP-AUDIT.md` covers all six weighted criteria. The
remaining gates are running AWS, current-source review access and demonstration
deliverables. Plan for **26 October 2026, 11:45 p.m. PDT / 27 October, 06:45 UTC**.
Some official prose says 11:59 p.m.; confirm before relying on that later time.
[Event and requirements](https://opencv26.devpost.com/),
[official rules](https://opencv26.devpost.com/rules),
[organizer updates](https://opencv26.devpost.com/updates).
