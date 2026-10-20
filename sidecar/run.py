#!/usr/bin/env python3
"""Start local motion service. Camera use requires explicit CLI selection."""

import argparse
import json
import signal
import statistics
import threading
import time
from pathlib import Path

from inference import OpenCVPose
from motion import synthetic_observation
from service import MotionService, make_server
from video_input import video_worker


def camera_worker(service, pose, stop, camera):
    cap = None
    last_token = None
    retry_at = 0
    last_frame = None
    while not stop.is_set():
        token = service.token()
        if token is None:
            if cap is not None:
                cap.release()
                cap = None
            if last_token is not None:
                service.idle()
            last_token = None
            stop.wait(0.05)
            continue
        last_token = token
        if cap is None:
            if time.monotonic() < retry_at:
                stop.wait(0.1)
                continue
            cap = pose.cv.VideoCapture(camera, pose.cv.CAP_AVFOUNDATION)
            if not cap.isOpened():
                cap.release()
                cap = None
                retry_at = time.monotonic() + 5
                service.camera_error("Mac camera unavailable. Unlock the Mac and allow camera access for this terminal, or use manual play.")
                continue
            cap.set(pose.cv.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(pose.cv.CAP_PROP_FRAME_HEIGHT, 480)
            service.message = "Local camera and in-app preview; frames stay in memory and are never recorded or uploaded"
        ok, frame = cap.read()
        if not ok or frame is None:
            service.camera_error("Camera did not return a frame; manual controls remain available")
            cap.release()
            cap = None
            retry_at = time.monotonic() + 5
            continue
        try:
            captured_at = service.clock()
            observation, status, elapsed = pose.infer(frame)
            now = time.monotonic()
            fps = 0.0 if last_frame is None else 1 / max(now - last_frame, 0.001)
            last_frame = now
            service.observe(token, observation, status, elapsed, min(fps, 120))
            # A bounded JPEG comes from this same frame and observation, never a
            # second capture. Token/age checks reject a pause during inference.
            image = pose.preview(frame, observation, status)
            service.publish_preview(token, image, captured_at)
            del image
        except Exception as exc:
            service.camera_error(f"Local OpenCV inference failed: {type(exc).__name__}: {exc}")
            stop.wait(0.1)
        finally:
            del frame  # No disk, screenshots, streaming or external inference.
        stop.wait(0.01)
    if cap is not None:
        cap.release()
    service.close()


def synthetic_worker(service, stop):
    """Synthetic landmark fixtures pass through the same gesture machine."""
    last_token = None
    stage_started = 0
    stage = "neutral"
    while not stop.is_set():
        token = service.token()
        now = time.monotonic()
        if token is None:
            if last_token is not None:
                service.idle()
            last_token = None
        else:
            if token != last_token:
                stage, stage_started = "neutral", now
            if now - stage_started >= 0.75:
                stage = service.machine.expected if stage == "neutral" else "neutral"
                stage_started = now
            service.observe(token, synthetic_observation(stage), "tracking", 0.0, 20.0)
            last_token = token
        stop.wait(0.05)


def camera_smoke(pose, camera, seconds):
    """Bounded, explicit capture test. Emits only aggregate JSON, never frames."""
    cap = pose.cv.VideoCapture(camera, pose.cv.CAP_AVFOUNDATION)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Mac camera failed to open; check lock state and camera permission")
    cap.set(pose.cv.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(pose.cv.CAP_PROP_FRAME_HEIGHT, 480)
    started = time.monotonic()
    durations, statuses = [], {}
    dimensions = None
    try:
        while time.monotonic() - started < seconds:
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Mac camera opened but returned no frame")
            dimensions = [int(frame.shape[1]), int(frame.shape[0])]
            _, status, duration = pose.infer(frame)
            durations.append(duration)
            statuses[status] = statuses.get(status, 0) + 1
            del frame
    finally:
        cap.release()
    elapsed = time.monotonic() - started
    return {"source": "camera", "runtime": pose.runtime, "frames": len(durations),
            "seconds": round(elapsed, 3), "fps": round(len(durations) / elapsed, 2),
            "inferenceMedianMs": round(statistics.median(durations), 2) if durations else None,
            "inferenceMaxMs": round(max(durations), 2) if durations else None,
            "dimensions": dimensions, "statuses": statuses,
            "humanGestureVerified": False, "savedFrames": 0, "uploadedFrames": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--verify", action="store_true", help="Verify OpenCV 5, hashes, and both DNN forwards without camera")
    choice.add_argument("--synthetic", action="store_true", help="Run clearly labelled SYNTHETIC landmark fixtures; no camera")
    choice.add_argument("--video", type=Path, help="Explicit local video fixture; FFmpeg file backend only, never a camera")
    choice.add_argument("--camera", type=int, choices=range(0, 8), metavar="INDEX", help="Explicitly allow local camera, opened only while game active")
    choice.add_argument("--camera-smoke", type=int, choices=range(0, 8), metavar="INDEX", help="Explicit bounded camera + DNN check, no HTTP service")
    parser.add_argument("--seconds", type=float, default=5, help="Smoke duration 1–30 seconds")
    parser.add_argument("--port", type=int, default=8765, help="Loopback port, default8765")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 30 or not 1024 <= args.port <= 65535:
        parser.error("Duration must be1–30 and port1024–65535")
    try:
        pose = OpenCVPose()
        if args.verify:
            print(json.dumps(pose.runtime, indent=2))
            return
        if args.camera_smoke is not None:
            print(json.dumps(camera_smoke(pose, args.camera_smoke, args.seconds), indent=2))
            return
        if args.video is not None:
            args.video = args.video.expanduser().resolve(strict=True)
            if not args.video.is_file():
                raise ValueError("Video fixture must be an existing local file")
        source = "synthetic" if args.synthetic else "video" if args.video is not None else "camera"
        service = MotionService(pose.runtime, source)
        stop = threading.Event()
        server = make_server(service, args.port)
        if args.synthetic:
            worker_target, worker_args = synthetic_worker, (service, stop)
        elif args.video is not None:
            worker_target, worker_args = video_worker, (service, pose, stop, args.video)
        else:
            worker_target, worker_args = camera_worker, (service, pose, stop, args.camera)
        worker = threading.Thread(target=worker_target, args=worker_args, daemon=True)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        worker.start()
        print(json.dumps({"listening": f"http://127.0.0.1:{args.port}/motion/events",
                          "source": source, "runtime": pose.runtime,
                          "cameraStartsOnlyWhenActive": source == "camera"}), flush=True)
        try:
            server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            service.close()
            server.server_close()
            worker.join(timeout=3)
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}",
                          "verified": False, "cameraFramesSaved": 0}), flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
