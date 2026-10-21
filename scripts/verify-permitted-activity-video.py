#!/usr/bin/env python3
"""Bounded, opt-in OpenCV video -> activity -> game/ACK functional evidence.

Only the already frozen CC BY-SA Taco Fleur derivative is accepted. This never
downloads media, opens a camera/socket/browser, or writes real saved progress.
Default invocation verifies pins only. --run is required for actual inference.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import select
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sidecar"))
VIDEO_SHA = "e5d5cecc1d981e6589432add534a6a09fbd4ee692864a3f0ec4603ef5864ef80"
VIDEO_BYTES = 332963
FRAME_COUNT = 136
FRAME_RATE = 30
EXPECTED = ROOT / "sidecar/fixtures/natural-controls/suitcase-both-up-negative.expected.json"
SOURCES = ("sidecar/inference.py", "sidecar/activity.py", "sidecar/service.py", "sidecar/motion.py",
           "sidecar/video_input.py", "sidecar/models.lock.json", "sidecar/requirements-macos-arm64.lock",
           "src/main.js", "src/motion.js", "src/motion-view.js", "src/model.js", "src/calibration.js",
           "src/runtime.js", "src/round-clock.js", "src/garden-view.js",
           "scripts/activity-game-evidence.mjs", "scripts/verify-permitted-activity-video.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_pins():
    return {name: sha(ROOT / name) for name in SOURCES}


def validate_fixture(video, model_root):
    video = video.expanduser().resolve(strict=True)
    if not video.is_file() or video.stat().st_size != VIDEO_BYTES or sha(video) != VIDEO_SHA:
        raise ValueError("Only the exact frozen, permitted 136-frame CC BY-SA fixture is allowed")
    frozen = json.loads(EXPECTED.read_text())
    if frozen["sha256"] != VIDEO_SHA or frozen["bytes"] != VIDEO_BYTES:
        raise ValueError("Historical frozen fixture pin changed")
    source = frozen["source"]
    if source["author"] != "Taco Fleur" or source["license"] != "CC BY-SA 4.0" or not source.get("permissionConfirmation"):
        raise ValueError("Required source attribution/permission metadata missing")
    model_root = model_root.expanduser().resolve(strict=True)
    model_lock = json.loads((ROOT / "sidecar/models.lock.json").read_text())
    if sha(model_root / "models.lock.json") != sha(ROOT / "sidecar/models.lock.json"):
        raise ValueError("Existing asset root uses a different model lock")
    asset_pins = []
    for row in model_lock["files"]:
        name = Path(row["path"])
        if name.is_absolute() or ".." in name.parts:
            raise ValueError("Unsafe model path")
        target = (model_root / name).resolve(strict=True)
        if not target.is_relative_to(model_root) or not target.is_file() or target.stat().st_size != row["bytes"] or sha(target) != row["sha256"]:
            raise ValueError("Pinned model/wrapper asset mismatch: " + row["path"])
        asset_pins.append({"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]})
    return {"video": {"path": str(video), "bytes": VIDEO_BYTES, "sha256": VIDEO_SHA,
                      "frames": FRAME_COUNT, "fps": FRAME_RATE},
            "source": source, "historicalExpectationSha256": sha(EXPECTED),
            "historicalStrictExpectationUnchanged": True,
            "activityExpectationKnown": False,
            "activityExpectationNote": "Functional example containing both-arm movement; no new accuracy label or target count.",
            "modelRoot": str(model_root), "modelAssets": asset_pins, "sourceSha256": source_pins()}


class GameAdapter:
    def __init__(self, node):
        self.process = subprocess.Popen([str(node), str(ROOT / "scripts/activity-game-evidence.mjs")],
                                        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, bufsize=0)
        self.output_buffer = bytearray()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            os.set_blocking(stream.fileno(), False)

    def request(self, value):
        encoded = (json.dumps(value, allow_nan=False) + "\n").encode()
        if len(encoded) > 32768:
            raise ValueError("Outgoing game packet exceeds 32 KiB")
        deadline = time.monotonic() + 3
        pending = memoryview(encoded)
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [self.process.stdin], [], remaining)[1]:
                raise TimeoutError("Game evidence adapter did not respond within three seconds")
            try:
                written = os.write(self.process.stdin.fileno(), pending)
            except BrokenPipeError as error:
                raise RuntimeError("Game evidence adapter closed its input") from error
            pending = pending[written:]
        while b"\n" not in self.output_buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise TimeoutError("Game evidence adapter did not respond within three seconds")
            block = os.read(self.process.stdout.fileno(), 4096)
            if not block:
                # Error collection is bounded too; never wait for stderr EOF.
                tail = b""
                if select.select([self.process.stderr], [], [], 0)[0]:
                    tail = os.read(self.process.stderr.fileno(), 2000)
                raise RuntimeError("Game evidence adapter exited: " + tail.decode(errors="replace"))
            self.output_buffer.extend(block)
            if len(self.output_buffer) > 32768:
                raise ValueError("Game evidence reply exceeds 32 KiB")
        line, _, remaining = self.output_buffer.partition(b"\n")
        self.output_buffer = bytearray(remaining)
        return json.loads(line)

    def close(self):
        if self.process.stdin:
            try:
                self.process.stdin.close()
            except OSError:
                pass  # A failed adapter must still be terminated/reaped below.
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        for stream in (self.process.stdout, self.process.stderr):
            if stream:
                try:
                    stream.close()
                except OSError:
                    pass


class PrivacyGuards:
    """Fail closed for Python sockets and every capture API except the pinned file."""
    def __init__(self, video):
        self.video = Path(video).resolve(strict=True)
        self.python_socket_attempts = 0
        self.allowed_file_capture_calls = 0
        self.blocked_capture_calls = 0
        self.original_socket_apis = None
        self.cv = self.original_capture = None

    def install_sockets(self):
        import socket
        self.original_socket_apis = (socket.socket, socket.create_connection, socket.socketpair)
        guard = self

        def denied(*args, **kwargs):
            guard.python_socket_attempts += 1
            raise PermissionError("Socket creation is forbidden in this offline evidence runner")

        class NoSocket(socket.socket):
            def __new__(cls, *args, **kwargs):
                return denied(*args, **kwargs)

        socket.socket, socket.create_connection, socket.socketpair = NoSocket, denied, denied

    def install_capture(self, cv):
        self.cv, self.original_capture = cv, cv.VideoCapture
        guard = self

        def capture(source, *args, **kwargs):
            allowed = isinstance(source, (str, Path)) and args == (cv.CAP_FFMPEG,) and not kwargs
            if allowed:
                try:
                    candidate = Path(source)
                    allowed = (not candidate.is_symlink() and candidate.resolve(strict=True) == guard.video
                               and candidate.is_file() and candidate.stat().st_size == VIDEO_BYTES and sha(candidate) == VIDEO_SHA)
                except (OSError, ValueError, RuntimeError):
                    allowed = False
            if not allowed:
                guard.blocked_capture_calls += 1
                raise PermissionError("Capture is restricted to the exact pinned regular file and FFmpeg backend")
            guard.allowed_file_capture_calls += 1
            return guard.original_capture(str(guard.video), cv.CAP_FFMPEG)

        cv.VideoCapture = capture

    def restore(self):
        if self.cv is not None:
            self.cv.VideoCapture = self.original_capture
        if self.original_socket_apis is not None:
            import socket
            socket.socket, socket.create_connection, socket.socketpair = self.original_socket_apis

    def snapshot(self):
        return {"pythonSocketAttempts": self.python_socket_attempts,
                "allowedPinnedFileCaptureCalls": self.allowed_file_capture_calls,
                "blockedCaptureCalls": self.blocked_capture_calls,
                "pythonSocketCreationDenied": self.original_socket_apis is not None,
                "captureApiAllowlistInstalled": self.cv is not None,
                "scope": "Python socket/capture APIs guarded; OS network denial supplied by caller; native internal sockets not measured"}


def run(pins, node, wall_seconds):
    # Asset-root redirection reads existing pinned assets; current inference and
    # classifier source are imported from this checkout, not canonical code.
    started = time.monotonic()
    capture = game = service = guard = None
    rows, statuses, inference_times, events = [], {}, [], []
    obs_hash = hashlib.sha256()
    report = {**pins, "kind": "permitted-video-functional-integration", "source": "video", "attribution": pins["source"],
              "inferenceRun": False, "recognitionAccuracyClaim": False, "liveHumanTest": False,
              "physicalFireTvTest": False, "cameraOpened": False, "browserOpened": False,
              "intentionalNetworkOperations": 0, "framesSaved": 0, "framesUploaded": 0,
              "frameInferenceThreads": 1, "productionWarmupThreads": 2,
              "scope": "Actual image inference and service, actual main/reducer/view in VM; no rendered UI or real-time/hardware claim"}
    first_observation = None
    eof = False
    try:
        import inference
        from service import MotionService
        from video_input import open_video
        from activity import ActivityMachine
        from importlib.metadata import version
        packages = {name: version(name) for name in ("opencv-python-headless", "numpy")}
        if packages != {"opencv-python-headless": "5.0.0.93", "numpy": "2.5.4"}:
            raise ValueError("Installed Python wheel versions differ from the recorded locked runtime")
        report["installedPackages"] = packages
        guard = PrivacyGuards(pins["video"]["path"])
        guard.install_sockets()
        import cv2
        guard.install_capture(cv2)
        inference.ROOT = Path(pins["modelRoot"])
        pose = inference.OpenCVPose()
        report["inferenceRun"] = True
        # Production initialization/zero-image warmup uses its existing two threads;
        # the bounded file frames use one thread. No classifier/model tuning.
        pose.cv.setNumThreads(1)
        capture, fps = open_video(Path(pins["video"]["path"]), pose.cv)
        if not math.isclose(fps, FRAME_RATE, abs_tol=.001):
            raise ValueError("Frozen fixture cadence differs")
        service = MotionService(pose.runtime, "video")
        game = GameAdapter(node)
        control = game.request({"op": "context"})["context"]
        next_frame = time.monotonic()
        for index in range(FRAME_COUNT):
            if not control["active"]:
                break  # The game target stops input; do not bypass it for coverage.
            if time.monotonic() - started >= wall_seconds:
                raise TimeoutError("Bounded inference deadline reached; preserve partial result")
            delay = next_frame - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            service.poll(control)
            token = service.token()
            if token is None:
                raise RuntimeError("Active lease unavailable; do not bypass safety controls")
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError("Premature video EOF")
            try:
                observation, status, duration = pose.infer(frame)
            finally:
                del frame
            if index == 0:
                first_observation = observation
            if observation is not None:
                from dataclasses import asdict
                obs_hash.update(json.dumps(asdict(observation), sort_keys=True, allow_nan=False).encode())
            else:
                obs_hash.update(b"null")
            service.observe(token, observation, status, duration, fps)
            packet = service.poll(control)
            state = game.request({"op": "packet", "packet": packet})
            control = state["context"]
            ack_packet = service.poll(control)
            if service.ack_seq != control["after"] or ack_packet["events"]:
                raise AssertionError("Actual game ACK failed to clear received events")
            if state["motion"]["count"] != state["displayedCount"] or state["motion"]["count"] != state["collectedRays"]:
                raise AssertionError("Actual view growth differs from accepted activity credit")
            if not state["storedBytesUnchanged"] or state["storageWrites"]:
                raise AssertionError("Recorded-video input changed saved participation")
            emitted = [e for e in packet["events"] if e["seq"] > (events[-1]["seq"] if events else 0)]
            for event in emitted:
                events.append({"frame": index, "wallMs": round((time.monotonic()-started)*1000, 3), **event})
            statuses[status] = statuses.get(status, 0) + 1
            inference_times.append(duration)
            rows.append({"frame": index, "fileTimeMs": round(index / fps * 1000, 3),
                         "wallMs": round((time.monotonic()-started)*1000, 3), "status": status,
                         "inferenceMs": duration, "serviceSeq": service.seq, "serviceAckSeq": service.ack_seq,
                         "gameRays": state["motion"]["count"], "displayedRays": state["displayedCount"],
                         "growth": state["growth"]})
            next_frame = max(next_frame + 1 / fps, time.monotonic())
        if len(rows) == FRAME_COUNT:
            extra, extra_frame = capture.read()
            if extra:
                del extra_frame
                raise RuntimeError("Unexpected extra decoded frame")
            eof = True
        final = game.request({"op": "finish"})
        static = ActivityMachine()
        static_events = sum(static.update(first_observation, i / fps * 1000) is not None for i in range(FRAME_COUNT))
        if static_events:
            raise AssertionError("Fixed first inferred observation produced activity")
        report.update(status="complete", runtime=pose.runtime, decodedFrames=len(rows), eof=eof,
                      fullFrameCoverage=len(rows)==FRAME_COUNT, stopReason="eof" if eof else "game-target-stopped-input",
                      activityEvents=events, gameRays=rows[-1]["gameRays"], ackSeq=service.ack_seq,
                      motionToGardenCreditObserved=bool(events) and rows[-1]["gameRays"] > 0,
                      savedParticipationUnchanged=final["storedBytesUnchanged"] and final["storageWrites"]==0,
                      gameAdapter=final, fixedInferredObservationControl={"events": static_events,
                          "firstObservationAvailable": first_observation is not None,
                          "scope": "Same first inferred observation repeated; classifier-only control, not static-image vision accuracy"})
    except Exception as error:
        report.update(status="failed", errorType=type(error).__name__, error=str(error), decodedFrames=len(rows), eof=False)
    finally:
        if capture is not None:
            capture.release()
        if service is not None:
            service.close()
        if game is not None:
            game.close()
        if guard is not None:
            report["privacyGuards"] = guard.snapshot()
            guard.restore()
        report.update(wallMs=round((time.monotonic()-started)*1000, 3), frames=rows, statuses=statuses,
                      observationSequenceSha256=obs_hash.hexdigest(),
                      inferenceMedianMs=statistics.median(inference_times) if inference_times else None,
                      inferenceMaxMs=max(inference_times) if inference_times else None,
                      sourceUnchanged=source_pins()==pins["sourceSha256"], videoUnchanged=sha(Path(pins["video"]["path"]))==VIDEO_SHA,
                      captureReleased=capture is None or not capture.isOpened(), serviceClosed=service is None or service.stopped,
                      gameAdapterStopped=game is None or game.process.poll() is not None)
    if not report["sourceUnchanged"] or not report["videoUnchanged"]:
        report.update(status="failed", error="Source/input changed during verification")
    if not all(report[name] for name in ("captureReleased", "serviceClosed", "gameAdapterStopped")):
        report.update(status="failed", error="Task resource cleanup did not complete")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--wall-seconds", type=float, default=30)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run", action="store_true", help="Explicitly execute existing OpenCV models; default verifies local pins only")
    args = parser.parse_args()
    if not 1 <= args.wall_seconds <= 60:
        parser.error("Wall budget must be 1–60 seconds")
    if not args.node.is_file():
        parser.error("An existing Node executable is required")
    if args.run and (args.output is None or args.output.exists()):
        parser.error("Actual run requires a new output file; prior evidence cannot be overwritten")
    pins = validate_fixture(args.video, args.model_root)
    result = run(pins, args.node, args.wall_seconds) if args.run else {**pins,"status":"pins-verified-not-run","inferenceRun":False}
    encoded = json.dumps(result, indent=2, allow_nan=False)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as output:
            output.write(encoded)
    print(json.dumps({k:v for k,v in result.items() if k not in ("frames","source","modelAssets","sourceSha256","gameAdapter")},indent=2))
    return 0 if result["status"] in ("complete","pins-verified-not-run") else 1


if __name__ == "__main__":
    raise SystemExit(main())
