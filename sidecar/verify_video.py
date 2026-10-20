#!/usr/bin/env python3
"""Actual file decode → detector → pose → classifier → event → JS game verification.

The clock is deterministic file time. No camera is opened; JPEG preview is
exercised in memory and never written into the evidence report.
"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
from unittest import mock

from inference import OpenCVPose
from pose_backend import BACKENDS, close_pose, create_pose
from service import MotionService
from video_input import open_video, wrist_gates

PROJECT = Path(__file__).resolve().parent.parent
CLIENT = "12345678-0000-4000-8000-000000000101"
ROUND = "12345678-0000-4000-8000-000000000102"
GOAL_SEQUENCE = ["left-raise", "right-raise"] * 3
MAX_VIDEO_MS = 30000


def load_event_windows(manifest, expected):
    """Validate authored optional event timing before any model or media decode."""
    if "eventWindows" not in manifest:
        return None
    windows = manifest["eventWindows"]
    if expected is None:
        raise ValueError("Event windows require an explicit expected gesture list")
    if not isinstance(windows, list) or len(windows) != len(expected):
        raise ValueError("Event windows must contain one window per expected gesture")
    frozen = []
    for gesture, window in zip(expected, windows):
        if not isinstance(window, dict) or set(window) != {"gesture", "startMs", "endMs"}:
            raise ValueError("Each event window requires exactly gesture, startMs and endMs")
        if window["gesture"] != gesture:
            raise ValueError("Event window gesture order must match expected gestures")
        start, end = window["startMs"], window["endMs"]
        # Check the range first so arbitrarily large JSON integers never reach
        # math.isfinite's implicit float conversion. Booleans are not times.
        if any(type(value) not in (int, float) or not 0 <= value <= MAX_VIDEO_MS
               or not math.isfinite(value) for value in (start, end)) or start > end:
            raise ValueError("Event window times must be finite, ordered and within0..30000ms")
        frozen.append({"gesture": gesture, "startMs": start, "endMs": end})
    return frozen


def evaluate_event_windows(events, windows):
    """Match every observed event to its authored inclusive file-time window."""
    checks = []
    for index in range(max(len(events), len(windows))):
        expected = windows[index] if index < len(windows) else None
        observed = events[index] if index < len(events) else None
        observed = observed if isinstance(observed, dict) else {}
        gesture, at_ms = observed.get("gesture"), observed.get("atVideoMs")
        if expected is None:
            reason = "unexpected-event"
        elif index >= len(events):
            reason = "missing-event"
        elif gesture != expected["gesture"]:
            reason = "gesture-mismatch"
        elif (type(at_ms) not in (int, float) or not 0 <= at_ms <= MAX_VIDEO_MS
              or not math.isfinite(at_ms)):
            reason = "invalid-timestamp"
        elif at_ms < expected["startMs"]:
            reason = "early"
        elif at_ms > expected["endMs"]:
            reason = "late"
        else:
            reason = "within-window"
        # Invalid timestamps are evidence of failure, never NaN/Infinity JSON.
        safe_time = (at_ms if type(at_ms) in (int, float) and 0 <= at_ms <= MAX_VIDEO_MS
                     and math.isfinite(at_ms) else None)
        checks.append({"index": index, "expectedGesture": expected["gesture"] if expected else None,
                       "startMs": expected["startMs"] if expected else None,
                       "endMs": expected["endMs"] if expected else None,
                       "observedGesture": gesture, "atVideoMs": safe_time,
                       "passed": reason == "within-window", "reason": reason})
    return {"passed": all(check["passed"] for check in checks), "boundaryRule": "inclusive",
            "timestampMeaning": "event emission in unrounded deterministic file milliseconds",
            "expectedEventCount": len(windows), "observedEventCount": len(events), "checks": checks}


def load_manifest(manifest_path, video_path, *, partial=False):
    """Bind external expectations to exact local fixture bytes before inference.

    Partial annotations describe reviewed pose windows without inventing a full
    gesture sequence. They cannot establish a complete game-goal result.
    """
    manifest_path, video_path = Path(manifest_path), Path(video_path).resolve(strict=True)
    if not video_path.is_file() or not 0 < video_path.stat().st_size <= 512 * 1024 * 1024:
        raise ValueError("Video fixture must be a local file of at most 512 MiB")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON object")
    digest = manifest.get("sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
        raise ValueError("Manifest must pin the fixture's SHA256")
    with video_path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != digest.lower():
        raise ValueError("Manifest SHA256 does not match the selected video fixture")
    expected = manifest.get("expectedGestures", manifest.get("expectedSemanticGestures"))
    if partial:
        if expected is not None:
            raise ValueError("Partial annotation must not declare a full expected gesture list; use --expected")
    elif (not isinstance(expected, list)
          or any(item not in ("left-raise", "right-raise") for item in expected)):
        raise ValueError("Expected manifest must contain an explicit gesture list")
    windows = load_event_windows(manifest, expected)
    return {"file": manifest_path.name, "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "fixtureSha256": actual, "kind": "partial-annotation" if partial else "sequence-expectation",
            "naturalContinuousMovement": manifest.get("naturalContinuousMovement"),
            "expectedGestures": expected, "eventWindows": windows}


def verification_outcome(report):
    """Pipeline consistency alone does not verify a recognition/game goal."""
    pipeline = report["gameScoringMatches"] and report["gameAcknowledgmentMatches"]
    expected = report["expectedGestures"]
    matched = report["expectedSequencePassed"] if expected is not None else None
    timing = report.get("eventTimingPassed")
    complete = bool(pipeline and matched is True and timing is not False and expected == GOAL_SEQUENCE
                    and report["game"].get("count") == 6 and report["game"].get("completed") is True)
    status = ("failed" if not pipeline or matched is False or timing is False else
              "complete-goal-verified" if complete else
              "partial-expectation-matched" if expected else
              "negative-control-matched" if expected == [] else "observed-only")
    return {"status": status, "pipelineConsistent": bool(pipeline),
            "sequenceExpectationPresent": expected is not None,
            "expectedSequenceMatched": matched, "eventTimingExpectationPresent": timing is not None,
            "eventTimingMatched": timing, "completeGoalVerified": complete,
            "scope": "selected local fixture only", "liveUserVerified": False}


def game_scoring_matches(observed, game):
    """One game goal: compare accepted rays, not only delivered event sequences."""
    target = 6
    return (game.get("target") == target
            and game.get("acceptedGestures") == observed[:target]
            and game.get("count") == min(len(observed), target)
            and game.get("completed") is (len(observed) >= target))


def verify(path, seconds=30, expected=None, score_script=None, motion_module=None, *,
           pose_backend="opencv", pose_factory=None):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file() or not 0 < path.stat().st_size <= 512 * 1024 * 1024:
        raise ValueError("Video fixture must be a local file of at most512 MiB")
    # Preserve the existing default hook and dependency-free default tests.
    factory = pose_factory or (OpenCVPose if pose_backend == "opencv" else
                               lambda: create_pose(pose_backend))
    pose = factory()
    try:
        return _verify_with_pose(pose, path, seconds, expected, score_script, motion_module)
    finally:
        close_pose(pose)


def _verify_with_pose(pose, path, seconds, expected, score_script, motion_module):
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
                                   "atVideoMs": now, "confidence": event["confidence"]}
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
    manifests = parser.add_mutually_exclusive_group()
    manifests.add_argument("--expected", type=Path,
                           help="SHA256-bound JSON containing expectedGestures; never generated from inference")
    manifests.add_argument("--annotation", type=Path,
                           help="SHA256-bound partial pose annotations; does not certify a complete sequence")
    parser.add_argument("--require-complete-goal", action="store_true",
                        help="Exit 1 unless an independently expected six-gesture goal is verified")
    parser.add_argument("--output", type=Path, required=True, help="Scalar JSON report only")
    parser.add_argument("--score-script", type=Path)
    parser.add_argument("--motion-module", type=Path)
    parser.add_argument("--pose-backend", choices=BACKENDS, default="opencv",
                        help="Optional Full CPU IMAGE backend; explicit local videos only")
    args = parser.parse_args()
    if not 0 < args.seconds <= 30:
        parser.error("Video test bound must be greater than zero and at most30seconds")
    expectation = None
    if args.expected or args.annotation:
        try:
            expectation = load_manifest(args.expected or args.annotation, args.video,
                                        partial=args.annotation is not None)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    expected = expectation["expectedGestures"] if expectation else None
    report = verify(args.video, args.seconds, expected, args.score_script, args.motion_module,
                    pose_backend=args.pose_backend)
    report["expectation"] = expectation
    windows = expectation["eventWindows"] if expectation else None
    report["eventTiming"] = evaluate_event_windows(report["events"], windows) if windows is not None else None
    report["eventTimingPassed"] = report["eventTiming"]["passed"] if windows is not None else None
    report["verificationOutcome"] = verification_outcome(report)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("source", "evidenceType", "fixture", "observedGestures",
                                                 "expectedGestures", "expectedSequencePassed", "eventTimingPassed", "game",
                                                 "gameScoringMatches", "gameAcknowledgmentMatches",
                                                 "armedTransitions", "previewResponses", "physicalCameraOpens",
                                                 "verificationOutcome")}))
    # Fixtures cover one game goal (at most six scored events). Extra service
    # events beyond a completed goal remain an ACK mismatch, not a silent pass.
    if (not report["gameScoringMatches"] or not report["gameAcknowledgmentMatches"]
            or (args.expected and not report["expectedSequencePassed"])
            or report["eventTimingPassed"] is False
            or (args.require_complete_goal and not report["verificationOutcome"]["completeGoalVerified"])):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
