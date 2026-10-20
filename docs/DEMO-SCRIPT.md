# Mac demo — manual play and labelled synthetic input

Use the current canonical checkout and a fresh test browser profile when a clean
garden is useful. Do not clear an existing user's saved garden. This Mac demo
does not establish Fire TV/Vega compliance or live camera recognition.

1. Start `npm run dev` from the repository root. Show the Sway & Sprout name and
   “Every move helps your garden grow.” Choose a position and manual play.
2. Show Wake the Garden, pause/resume and visible keyboard focus. At the endpoint,
   choose “We joined in.” Explain that manual participation is self-reported and
   saved only on this device. All three moments remain available without a camera.
3. For a separate deterministic transport/game demo, start `npm run motion:synthetic`
   in another terminal. Choose Catch the Sunshine → Camera sunshine → Start.
   Verify the badge says `SYNTHETIC TEST · NO CAMERA`; no camera image should appear.
4. Let synthetic input collect six rays. Pause, change position and resume. At
   completion, show that the previously saved garden/session data is unchanged,
   including after reload. Say explicitly that these are generated landmarks,
   not human recognition. Stop the sidecar with Ctrl-C after the demo.
5. Use [the full-pipeline file checks](NATURAL-VIDEO-VERIFICATION.md) for a separate
   evidence review. Clear/frontal held public poses score six rays; near-face
   remains one of six. The current normal-speed dancing clips do not verify a
   complete natural sequence.

The improved calibration UI can be demonstrated with the mocked browser test;
its camera-labelled JSON is not a live-camera result. Do not prompt a person or
start camera mode until they explicitly say they are ready for a later test and
the offline acceptance boundary in the [handoff](DEVELOPMENT-HANDOFF.md) is met.
Actual Fire TV/Vega recording requires separate device verification. No clinical,
fitness, general detection-accuracy or two-player camera claim is supported.
