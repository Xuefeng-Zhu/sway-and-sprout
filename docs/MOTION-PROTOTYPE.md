# Local camera sunshine prototype

This Mac prototype adds one single-player vertical slice to the existing TogetherMove export. It is not a contest eligibility determination or actual Fire OS verification.

The current visible product name is **Sway & Sprout**. Preserved TogetherMove exports, APK labels, internal IDs, paths, and dated verification evidence below retain their original names. New debug native builds use the launcher label **Sway & Sprout Motion**.

## Baseline versus new work

The original source ZIP records commit `6f2cf17e34e38a36a8b9d6bfd3fb94217ba2bfec`. All 55 original source files matched that archive before changes. The original export and APK remain preserved; the baseline backup and integrity manifest are under `../../../evidence/togethermove-motion-20261018/`. No local Git metadata was supplied, so this is export provenance, not verification of a current VM HEAD.

New work: optional camera input for Catch the Sunshine; six alternating arm raises; live sun/flower feedback; semantic input filtering and local transport; an OpenCV 5 sidecar using the official Zoo person detector and pose estimator; a debug-only Android proxy and separate prototype identity; synthetic tests and Mac verification evidence. Wake the Garden and Make Some Rain retain manual play.

## Run on this Mac

From `apps/togethermove`, first verify the isolated runtime and pinned model hashes:

```sh
npm run motion:verify
npm test
sidecar/.venv/bin/python -m unittest discover -s sidecar -p 'test_*.py' -v
```

Start the local camera service and the web app in separate terminals:

```sh
npm run motion:camera
```

```sh
npm run dev
# Open http://127.0.0.1:4173
```

Choose Catch the Sunshine → seated or standing → Camera sunshine → Start. Face the camera with both shoulders and wrists visible. Begin with both arms down. Raise your anatomical left wrist above its shoulder, hold briefly, then rest both arms; repeat on the right. Six alternating raises collect six rays. The flower grows immediately, and the 30-second round adds the completed moment to the saved garden. Progress from incomplete camera rounds requires clearly labelled manual confirmation.

The classifier requires 300 ms in neutral, a 350 ms raise hold, and a 500 ms cooldown. Missing/low-confidence landmarks, both arms raised, a wrong-side raise, frame gaps and pauses invalidate a partial hold. These are prototype thresholds, not measured accuracy guarantees or exercise recommendations.

Pause with Space, media play/pause or Back. Changing position also pauses. Accepted rays survive a pause, but both arms must return to rest before the next raise. “Use manual play” keeps the standard self-report path available.

For a deterministic demo with no camera:

```sh
npm run motion:synthetic
```

Synthetic input passes through the gesture state machine and real HTTP transport; it is visibly labelled `SYNTHETIC TEST · NO CAMERA` and does not establish human recognition. Stop one sidecar with Ctrl-C before starting another. A source/service change resets an in-progress camera round and pauses it rather than mixing evidence.

## Live framing preview

Camera sunshine includes a live preview in the Mac browser. It comes from the
same captured frames and pose estimates as recognition, with shoulder/wrist
markers, wrist visibility, confidence, the expected hand and hold feedback. The
browser does not request or open another camera. Synthetic mode has no real
camera preview.

Start the round to see the preview. Pause, completion, leaving camera play,
camera errors and polling-lease timeout clear the image and stop capture. The
preview is off before Start and in manual mode. This preview is a Mac-browser
feature; the previously built APK has not been rebuilt or changed.

## Privacy and transport

Camera capture is explicit CLI opt-in. Frames are never recorded, written to disk
or uploaded for inference. The user-requested preview sends one bounded JPEG at a
time over Mac loopback to this local browser; image data lives in process/browser
memory and is cleared when preview is off. Only the latest image is retained by
the sidecar, with a short expiry. Preview reads require the currently active local
client/round/revision and cannot start capture or extend its polling lease. There
is no upload endpoint or arbitrary URL proxy. The semantic event endpoint
continues to carry no images or landmark coordinates.

The browser polls same-origin `/motion/events` and `/motion/preview` routes through Vite's fixed loopback proxy. The debug APK provides the identical route through a fixed native proxy to the emulator host alias `10.0.2.2:8765`. Requests carry a client UUID, round UUID, revision, active flag, position and acknowledgement cursor. Old revisions, duplicates, stale events and events outside the active round cannot advance progress. Source identity is retained so synthetic results cannot be relabelled as camera verification.

The sidecar listens only on `127.0.0.1`, bounds requests, event queues and response size, and has no arbitrary URL proxy. The Android debug build permits network access only for this purpose and scopes cleartext access to the emulator alias. Release retains its offline network policy. No TV camera permission is requested. A physical Fire TV cannot use the emulator-only alias.

## Android build and verification boundaries

```sh
npm run build
npm run android:sync
# From the task root, using this Mac's already cached toolchain:
sh evidence/togethermove-motion-20261018/android/build-cached-mac.sh
```

The debug application ID is `com.togethermove.tv.motion` and its label is TogetherMove Motion. It installs alongside the original app; it must not overwrite the baseline. See `android/README-motion.md` for the fixed native proxy and the explicit cached-toolchain override. Original Gradle/AGP pins remain unchanged.

Version/model pinning, measured checks, screenshots and camera blockers are recorded in the task's motion evidence/report. Synthetic landmark tests, actual DNN forward execution, browser tests, emulator compatibility and human camera recognition are distinct forms of evidence. Existing-project competition reuse remains unconfirmed. No GitHub push, AWS deployment or publication is part of this prototype.
