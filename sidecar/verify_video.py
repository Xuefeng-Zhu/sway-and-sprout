#!/usr/bin/env python3
"""Actual file decode → detector → pose → classifier → event → JS game verification.

The clock is deterministic file time. No camera is opened; JPEG preview is
exercised in memory and never written into the evidence report.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
from unittest import mock

from inference import OpenCVPose
from service import MotionService
from video_input import open_video, wrist_gates

PROJECT = Path(__file__).resolve().parent.parent
CLIENT = "12345678-0000-4000-8000-000000000101"
ROUND = "12345678-0000-4000-8000-000000000102"


def game_scoring_matches(observed, game):
    """One game goal: compare accepted rays, not only delivered event sequences."""
    target = 6
    return (game.get("target") == target
            and game.get("acceptedGestures") == observed[:target]
            and game.get("count") == min(len(observed), target)
            and game.get("completed") is (len(observed) >= target))


def verify(path, seconds=30, expected=None, score_script=None, motion_module=None):
    pose = OpenCVPose()
    path = Path(path).expanduser().resolve(strict=True)
    original_capture = pose.cv.VideoCapture
    opened = []

    def only_this_file(value, backend):
        if not isinstance(value, str) or Path(value).resolve() != path or backend != pose.cv.CAP_FFMPEG:
            raise AssertionError("Only the approved fixture file/FFmpeg backend may be opened")
        opened.append({"backend": "FFMPEG", "kind": "local-file"})
        return original_capture(value, backend)

    now = 0.0
    service = MotionService(pose.runtime, "video", clock=lambda: now)
    control = dict(clientId=CLIENT, roundId=ROUND, revision=0, active=True,
                   mode="standing", after=0)
    service.poll(control)
    packets, events, stages = [], [], []
    inference, classifications, gates = Counter(), Counter(), Counter()
    confidence_minima, elapsed_ms = [], []
    armed_transitions = preview_count = frames = 0
    longest_neutral = 0
    started = time.perf_counter()
    with mock.patch.object(pose.cv, "VideoCapture", side_effect=only_this_file):
        capture, fps = open_video(path, pose.cv)
        try:
            for index in range(min(3600, int(seconds * fps))):
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                now = index * 1000 / fps
                token = service.token()
                # Poll at each frame to exercise fresh event delivery/ACK without
                # conflating slow host processing with the fixture's timestamps.
                service.poll(control)
                token = service.token()
                was_armed, previous_status = service.machine.armed, service.machine.status
                observation, status, duration = pose.infer(frame)
                inference[status] += 1
                gates[wrist_gates(observation, service.machine.config)] += 1
                elapsed_ms.append(duration)
                if observation:
                    confidence_minima.append(min(observation.confidence, *(p.confidence for p in (
                        observation.left_shoulder, observation.right_shoulder,
                        observation.left_wrist, observation.right_wrist))))
                service.observe(token, observation, status, duration, fps)
                classifications[service.machine.status] += 1
                if service.machine.neutral_since is not None:
                    longest_neutral = max(longest_neutral, now - service.machine.neutral_since)
                if service.machine.armed and not was_armed:
                    armed_transitions += 1
                image = pose.preview(frame, observation, status)
                service.publish_preview(token, image, now)
                preview = service.preview(control)
                if preview["available"]:
                    preview_count += 1
                del image, preview, frame
                packet = service.poll(control)
                # Scalar packet contains no image or landmark coordinates.
                if packet["events"]:
                    events.extend({"gesture": event["gesture"], "seq": event["seq"],
                                   "atVideoMs": round(now, 2), "confidence": event["confidence"]}
                                  for event in packet["events"])
                    control["after"] = packet["seq"]
                packets.append(packet)
                if service.machine.status != previous_status or index % max(1, round(fps)) == 0:
                    stages.append({"videoMs": round(now, 2), "status": service.machine.status,
                                   "armed": service.machine.armed, "expected": service.machine.expected,
                                   "heldMs": service.machine.held_ms,
                                   "gate": wrist_gates(observation, service.machine.config)})
                frames += 1
            service.poll(control)  # Acknowledge the last delivered event.
        finally:
            capture.release()
            service.close()
    scorer = Path(score_script or PROJECT / "scripts/score-motion-fixture.mjs")
    module = Path(motion_module or PROJECT / "src/motion.js")
    scoring_input = {"source": "video", "roundId": ROUND, "packets": packets}
    scoring = subprocess.run(["node", str(scorer), "--module", str(module)],
                             input=json.dumps(scoring_input), text=True, capture_output=True, check=True)
    game = json.loads(scoring.stdout)
    observed = [event["gesture"] for event in events]
    return {"source": "video", "evidenceType": "actual-video-pose-inference", "humanVerified": False,
            "fixture": {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "fps": fps, "decodedFrames": frames},
            "runtime": pose.runtime, "videoMs": round(frames * 1000 / fps, 2),
            "processingSeconds": round(time.perf_counter() - started, 3),
            "inferenceMedianMs": round(statistics.median(elapsed_ms), 3) if elapsed_ms else None,
            "inferenceStatuses": dict(inference), "classifierStatuses": dict(classifications),
            "gateCounts": dict(gates), "armedTransitions": armed_transitions,
            "longestNeutralMs": round(longest_neutral, 2),
            "minimumObservedLandmarkConfidence": round(min(confidence_minima), 4) if confidence_minima else None,
            "previewResponses": preview_count, "events": events, "game": game,
            "acknowledgedSeq": service.ack_seq,
            "gameAcknowledgmentMatches": service.ack_seq == game["lastSeq"],
            "gameScoringMatches": game_scoring_matches(observed, game),
            "expectedGestures": list(expected) if expected is not None else None, "observedGestures": observed,
            "expectedSequencePassed": observed == list(expected) if expected is not None else None,
            "stages": stages, "captureOpens": opened, "physicalCameraOpens": 0,
            "previewCacheCleared": service.latest_preview is None,
            "savedOutputFrames": 0, "uploadedFrames": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--expected", type=Path, help="JSON containing expectedGestures; never generated from inference")
    parser.add_argument("--output", type=Path, required=True, help="Scalar JSON report only")
    parser.add_argument("--score-script", type=Path)
    parser.add_argument("--motion-module", type=Path)
    args = parser.parse_args()
    if not 0 < args.seconds <= 30:
        parser.error("Video test bound must be greater than zero and at most30seconds")
    expected = None
    if args.expected:
        manifest = json.loads(args.expected.read_text())
        expected = manifest.get("expectedGestures", manifest.get("expectedSemanticGestures"))
        if not isinstance(expected, list) or any(item not in ("left-raise", "right-raise") for item in expected):
            parser.error("Expected manifest must contain an explicit gesture list")
    report = verify(args.video, args.seconds, expected, args.score_script, args.motion_module)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("source", "evidenceType", "fixture", "observedGestures",
                                                 "expectedGestures", "expectedSequencePassed", "game",
                                                 "gameScoringMatches", "gameAcknowledgmentMatches",
                                                 "armedTransitions", "previewResponses", "physicalCameraOpens")}))
    # Fixtures cover one game goal (at most six scored events). Extra service
    # events beyond a completed goal remain an ACK mismatch, not a silent pass.
    if (not report["gameScoringMatches"] or not report["gameAcknowledgmentMatches"]
            or (args.expected and not report["expectedSequencePassed"])):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
