#!/usr/bin/env python3
"""Bounded local-video diagnosis: numeric traces, no camera or saved frames; Python sockets blocked.

An independently authored SHA256-bound expectation or partial annotation is
required. Partial annotations never certify a complete alternating game goal.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import importlib
import json
import math
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest import mock

CLIENT = "12345678-0000-4000-8000-000000000101"
ROUND = "12345678-0000-4000-8000-000000000102"
SOURCES = ("sidecar/inference.py", "sidecar/motion.py", "sidecar/service.py",
           "sidecar/vendor/mp_persondet.py", "sidecar/vendor/mp_pose.py",
           "sidecar/video_input.py", "sidecar/verify_video.py", "src/motion.js",
           "src/calibration.js", "scripts/score-motion-fixture.mjs")


def load_project(project):
    """Import code from the explicitly selected checkout without loading models."""
    sidecar = project / "sidecar"
    sys.path.insert(0, str(sidecar))
    modules = {}
    for name in ("inference", "service", "video_input", "verify_video"):
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != sidecar / (name + ".py"):
            raise ValueError("Another checkout's sidecar modules are already imported; use a fresh process")
        modules[name] = module
    evaluate = getattr(modules["verify_video"], "evaluate_event_windows", None)
    if not callable(evaluate):
        raise ValueError("Selected verifier needs event-window acceptance support; update it before diagnosis")
    return SimpleNamespace(
        OpenCVPose=modules["inference"].OpenCVPose,
        MotionService=modules["service"].MotionService,
        open_video=modules["video_input"].open_video,
        wrist_gates=modules["video_input"].wrist_gates,
        load_manifest=modules["verify_video"].load_manifest,
        game_scoring_matches=modules["verify_video"].game_scoring_matches,
        verification_outcome=modules["verify_video"].verification_outcome,
        evaluate_event_windows=evaluate,
    )


@contextmanager
def restricted_io(cv, video, attempts, opened):
    """Reject every capture constructor except this exact file + FFmpeg backend."""
    original_capture = cv.VideoCapture

    def capture(value, backend=None, *args, **kwargs):
        valid = isinstance(value, str) and not args and not kwargs and backend == cv.CAP_FFMPEG
        if valid:
            try:
                valid = Path(value).resolve(strict=True) == video
            except (OSError, ValueError):
                valid = False
        if not valid:
            attempts["capture"] += 1
            raise AssertionError("Only the manifest-bound local video and CAP_FFMPEG may be opened")
        opened.append({"kind": "local-file", "backend": "CAP_FFMPEG"})
        return original_capture(value, backend)

    def blocked_socket(*args, **kwargs):
        attempts["socket"] += 1
        raise AssertionError("Python sockets are prohibited during local-video diagnosis")

    with mock.patch.object(cv, "VideoCapture", side_effect=capture), \
         mock.patch.object(socket, "socket", side_effect=blocked_socket), \
         mock.patch.object(socket, "create_connection", side_effect=blocked_socket):
        yield


def intervals(rows, predicate, fps):
    """Observed sample span differs from a hypothetical continuous frame coverage."""
    spans, start = [], None
    for index in range(len(rows) + 1):
        match = index < len(rows) and predicate(rows[index])
        if match and start is None:
            start = index
        elif not match and start is not None:
            spans.append({"startFrame": start, "endFrameExclusive": index,
                          "startMs": round(start * 1000 / fps, 3),
                          "lastSampleMs": round((index - 1) * 1000 / fps, 3),
                          "observedSpanMs": round((index - start - 1) * 1000 / fps, 3),
                          "sampledCoverageMs": round((index - start) * 1000 / fps, 3)})
            start = None
    return spans


def finite_min(values):
    return min(values) if values and all(math.isfinite(value) for value in values) else None


def json_safe(value):
    """Keep nonfinite diagnostics explicit as null, never emit nonstandard NaN JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def score_packets(project, packets):
    # Fixed local scorer imports the real reducer; it does not instantiate an
    # HTTP client. Python sockets remain blocked while this subprocess executes.
    result = subprocess.run(
        ["node", str(project / "scripts/score-motion-fixture.mjs"), "--module", str(project / "src/motion.js")],
        input=json.dumps({"source": "video", "roundId": ROUND, "packets": packets}, allow_nan=False),
        text=True, capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)


def analyze_bound_video(project, video, binding, seconds, modules):
    # This import and model construction occur only AFTER load_manifest succeeds.
    import cv2 as cv

    attempts, opened, rows, packets, events = {"capture": 0, "socket": 0}, [], [], [], []
    state, now, capture, service = {}, 0.0, None, None
    started = time.perf_counter()
    with restricted_io(cv, video, attempts, opened):
        pose = modules.OpenCVPose()
        detector, preprocess = pose.detector.infer, pose.pose._preprocess

        def detected(frame):
            people = detector(frame)
            state["detectionCount"] = len(people)
            # Single-person traces are complete. Cap unexpected many-person
            # output to keep the bounded report affordable on the target Mac.
            state["detections"] = [person.tolist() for person in people[:8]]
            state["detectionsTruncated"] = len(people) > 8
            return people

        def preprocessed(frame, person):
            original = person.copy()
            result = preprocess(frame, person)
            _, box, angle, matrix, pad = result
            state["roi"] = {"person": original.tolist(), "angle": float(angle),
                            "padding": pad.tolist(), "box": box.tolist(), "matrix": matrix.tolist()}
            return result

        service = modules.MotionService(pose.runtime, "video", clock=lambda: now)
        control = dict(clientId=CLIENT, roundId=ROUND, revision=0, active=True, mode="standing", after=0)
        service.poll(control)
        try:
            with mock.patch.object(pose.detector, "infer", side_effect=detected), \
                 mock.patch.object(pose.pose, "_preprocess", side_effect=preprocessed):
                capture, fps = modules.open_video(video, cv)
                for index in range(min(3600, int(seconds * fps))):
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        break
                    try:
                        now = index * 1000 / fps
                        service.poll(control)
                        token = service.token()
                        state.clear()
                        before = {"armed": service.machine.armed, "neutralSince": service.machine.neutral_since,
                                  "holdSince": service.machine.hold_since, "lastObserved": service.machine.last_observed}
                        observation, status, duration = pose.infer(frame)
                        service.observe(token, observation, status, duration, fps)
                        packet = service.poll(control)
                        if packet["events"]:
                            events.extend({**event, "frame": index, "atMs": round(now, 3), "atVideoMs": now}
                                          for event in packet["events"])
                            control["after"] = packet["seq"]
                        packets.append(packet)
                        row = {"frame": index, "atMs": round(now, 3), "inferenceStatus": status,
                               "inferenceMs": duration, "gate": modules.wrist_gates(observation, service.machine.config),
                               "status": service.machine.status, "armed": service.machine.armed,
                               "expected": service.machine.expected, "heldMs": service.machine.held_ms,
                               "neutralSince": service.machine.neutral_since, "before": before,
                               "detectionCount": state.get("detectionCount", 0), "detections": state.get("detections", []),
                               "detectionsTruncated": state.get("detectionsTruncated", False), "roi": state.get("roi"),
                               "calibration": packet.get("metrics", {}).get("calibration")}
                        if observation is not None:
                            row["observation"] = asdict(observation)
                            points = (observation.left_shoulder, observation.right_shoulder,
                                      observation.left_wrist, observation.right_wrist)
                            width = math.hypot(points[0].x - points[1].x, points[0].y - points[1].y)
                            row["shoulderWidth"] = width
                            row["minConfidence"] = finite_min([observation.confidence] + [point.confidence for point in points])
                            row["leftQ"] = (points[0].y - points[2].y) / width if width > 0 else None
                            row["rightQ"] = (points[1].y - points[3].y) / width if width > 0 else None
                        rows.append(row)
                    finally:
                        del frame
                service.poll(control)
        finally:
            try:
                if capture is not None:
                    capture.release()
            finally:
                service.close()
        with video.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != binding["fixtureSha256"]:
                raise ValueError("Video fixture changed after manifest validation; no diagnosis can be certified")
        game = score_packets(project, packets)
    if not rows:
        raise ValueError("The selected duration decoded zero video frames")

    observed = [event["gesture"] for event in events]
    expected = binding["expectedGestures"]
    minimums = [row["minConfidence"] for row in rows if row.get("minConfidence") is not None]
    angles = [row["roi"]["angle"] for row in rows if row["roi"] and math.isfinite(row["roi"]["angle"])]
    bottlenecks, failures, joint_minima = Counter(), Counter(), {}
    for row in rows:
        count = row["detectionCount"]
        if row["inferenceStatus"] != "tracking":
            failures["no-detection" if count == 0 else "multiple-detections" if count > 1 else "pose-not-accepted"] += 1
        observation = row.get("observation")
        if observation:
            confidences = {key: point["confidence"] for key, point in observation.items() if isinstance(point, dict)}
            confidences["detectorOrPose"] = observation["confidence"]
            for key, confidence in confidences.items():
                if math.isfinite(confidence):
                    joint_minima[key] = min(joint_minima.get(key, confidence), confidence)
            if row["gate"] == "low-confidence" and all(math.isfinite(value) for value in confidences.values()):
                bottlenecks[min(confidences, key=confidences.get)] += 1
    summary = {
        "source": "video", "evidenceType": "actual-video-inference-scalar-diagnosis", "humanVerified": False,
        "fixture": {"file": video.name, "sha256": binding["fixtureSha256"], "fps": fps, "decodedFrames": len(rows)},
        "expectation": binding, "runtime": pose.runtime, "config": asdict(service.machine.config),
        "requestedSeconds": seconds, "decodedVideoMs": round(len(rows) * 1000 / fps, 3),
        "processingSeconds": round(time.perf_counter() - started, 3),
        "inferenceMedianMs": statistics.median(row["inferenceMs"] for row in rows),
        "maxObservedFrameGapMs": round(max((b["atMs"] - a["atMs"] for a, b in zip(rows, rows[1:])), default=0), 3),
        "clock": "deterministic file timestamps, not a live-camera cadence measurement",
        "gateCounts": dict(Counter(row["gate"] for row in rows)),
        "classifierStatusCounts": dict(Counter(row["status"] for row in rows)),
        "inferenceStatusCounts": dict(Counter(row["inferenceStatus"] for row in rows)),
        "detectionCounts": dict(Counter(row["detectionCount"] for row in rows)),
        "inferenceFailureStageCounts": dict(failures), "lowConfidenceBottleneckCounts": dict(bottlenecks),
        "minimumObservedConfidence": min(minimums) if minimums else None,
        "firstFrameMinimumConfidence": rows[0].get("minConfidence"), "jointConfidenceMinima": joint_minima,
        "gateIntervals": {gate: intervals(rows, lambda row, gate=gate: row["gate"] == gate, fps)
                          for gate in sorted({row["gate"] for row in rows})},
        "lowConfidenceIntervals": intervals(rows, lambda row: row["gate"] == "low-confidence", fps),
        "detectionIntervals": {name: intervals(rows, predicate, fps) for name, predicate in (
            ("none", lambda row: row["detectionCount"] == 0), ("single", lambda row: row["detectionCount"] == 1),
            ("multiple", lambda row: row["detectionCount"] > 1))},
        "armedIntervals": intervals(rows, lambda row: row["armed"], fps),
        "roiAngleRange": [min(angles), max(angles)] if angles else None,
        "events": events, "observedGestures": observed, "expectedGestures": expected,
        "expectedSequencePassed": observed == expected if expected is not None else None,
        "game": game, "acknowledgedSeq": service.ack_seq,
        "gameScoringMatches": modules.game_scoring_matches(observed, game),
        "gameAcknowledgmentMatches": service.ack_seq == game["lastSeq"],
        "blockedApiAttempts": attempts, "captureOpens": opened, "physicalCameraUsed": False,
        "savedOutputFrames": 0, "uploadedFrames": 0, "previewGenerated": False,
        "previewCacheCleared": service.latest_preview is None,
        "traceContains": "numeric detector/ROI/landmark/classifier diagnostics only; no pixels or JPEG",
        "captureGuard": "only the manifest-bound local-file constructor with CAP_FFMPEG; Python socket APIs blocked",
        "detailedDetectionsPerFrameLimit": 8,
        "detectionTraceTruncatedFrames": sum(row["detectionsTruncated"] for row in rows),
        "naturalContinuousMovement": binding.get("naturalContinuousMovement"),
        "framesAreDiagnosticsNotHumanAnnotations": True,
        "implementationSha256": {name: hashlib.sha256((project / name).read_bytes()).hexdigest() for name in SOURCES},
        "diagnosticScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    neutral = summary["gateIntervals"].get("left-down/right-down", [])
    summary["longestNeutralObservedSpanMs"] = max((span["observedSpanMs"] for span in neutral), default=0)
    raised = next((row for row in rows if "up" in row["gate"]), None)
    summary["firstConfidentRaisedGate"] = {key: raised[key] for key in ("frame", "atMs", "gate", "armed", "status")} if raised else None
    windows = binding.get("eventWindows")
    summary["eventTiming"] = modules.evaluate_event_windows(events, windows) if windows is not None else None
    summary["eventTimingPassed"] = summary["eventTiming"]["passed"] if summary["eventTiming"] is not None else None
    summary["verificationOutcome"] = modules.verification_outcome(summary)
    return json_safe({"summary": summary, "frames": rows})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True, help="Explicit canonical repository root")
    parser.add_argument("--video", type=Path, required=True, help="Exact local video pinned by the manifest")
    manifests = parser.add_mutually_exclusive_group(required=True)
    manifests.add_argument("--expected", type=Path, help="SHA256-bound independent expected gesture sequence")
    manifests.add_argument("--annotation", type=Path, help="SHA256-bound partial annotations, no complete goal claim")
    parser.add_argument("--seconds", type=float, default=30, help="Greater than zero, at most30 seconds")
    parser.add_argument("--output", type=Path, required=True, help="Local directory for scalar trace.json/summary.json")
    parser.add_argument("--require-complete-goal", action="store_true")
    args = parser.parse_args(argv)
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 30:
        parser.error("Video diagnosis must be greater than zero and at most30 seconds")
    try:
        project, video = args.project.expanduser().resolve(strict=True), args.video.expanduser().resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Project must be an existing local checkout directory")
        modules = load_project(project)
        manifest = (args.expected or args.annotation).expanduser().resolve(strict=True)
        binding = modules.load_manifest(manifest, video, partial=args.annotation is not None)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    report = analyze_bound_video(project, video, binding, args.seconds, modules)
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (("trace.json", report), ("summary.json", report["summary"])):
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    summary = report["summary"]
    print(json.dumps({key: summary[key] for key in ("fixture", "gateCounts", "minimumObservedConfidence",
        "observedGestures", "game", "gameScoringMatches", "gameAcknowledgmentMatches", "eventTimingPassed", "verificationOutcome",
        "blockedApiAttempts", "physicalCameraUsed", "savedOutputFrames", "uploadedFrames")}))
    outcome = summary["verificationOutcome"]
    if outcome["status"] == "failed" or (args.require_complete_goal and not outcome["completeGoalVerified"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
