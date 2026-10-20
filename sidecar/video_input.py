"""Local video-file input for testing. This module never opens a camera device."""

import math
from pathlib import Path
import time


def open_video(path, cv):
    """Only an existing local file and the explicit FFmpeg backend are accepted."""
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file() or not 0 < path.stat().st_size <= 512 * 1024 * 1024:
        raise ValueError("Video fixture must be a local file of at most 512 MiB")
    capture = cv.VideoCapture(str(path), cv.CAP_FFMPEG)
    if not capture.isOpened():
        capture.release()
        raise ValueError("FFmpeg could not decode the local video fixture")
    fps = float(capture.get(cv.CAP_PROP_FPS))
    if not math.isfinite(fps) or not 1 <= fps <= 120:
        capture.release()
        raise ValueError("Video fixture needs a finite 1–120 fps time base")
    return capture, fps


def wrist_gates(observation, config):
    """Return scalar categories, never coordinates or a claim about human motion."""
    if observation is None:
        return "no-pose"
    ls, rs, lw, rw = (observation.left_shoulder, observation.right_shoulder,
                      observation.left_wrist, observation.right_wrist)
    confidences = [observation.confidence] + [point.confidence for point in (ls, rs, lw, rw)]
    if (any(not math.isfinite(value) or not config.min_confidence <= value <= 1 for value in confidences)
            or any(not math.isfinite(value) for point in (ls, rs, lw, rw) for value in (point.x, point.y))):
        return "low-confidence"
    width = math.hypot(ls.x - rs.x, ls.y - rs.y)
    if width <= .00001:
        return "degenerate-shoulders"

    def phase(wrist, shoulder):
        return ("up" if wrist.y < shoulder.y - width * config.raise_margin else
                "down" if wrist.y > shoulder.y + width * config.neutral_margin else "transition")

    return f"left-{phase(lw, ls)}/right-{phase(rw, rs)}"


def video_worker(service, pose, stop, path):
    """Replay at file cadence while active, through the same inference/preview APIs."""
    capture = None
    round_id = None
    frame_index = 0
    ended = False
    had_active = False
    next_frame_at = 0
    try:
        while not stop.is_set():
            token = service.token()
            if token is None:
                if capture is not None:
                    capture.release()
                    capture = None
                if had_active:
                    service.idle()
                had_active = False
                stop.wait(.05)
                continue
            had_active = True
            if token[1] != round_id:
                if capture is not None:
                    capture.release()
                    capture = None
                round_id, frame_index, ended = token[1], 0, False
            if ended:
                stop.wait(.05)
                continue
            if capture is None:
                capture, fps = open_video(path, pose.cv)
                if frame_index:
                    capture.set(pose.cv.CAP_PROP_POS_FRAMES, frame_index)
                next_frame_at = time.monotonic()
                service.message = "VIDEO REPLAY · NO CAMERA. Fixture input does not verify real-user motion."
            wait = next_frame_at - time.monotonic()
            if wait > 0 and stop.wait(min(wait, .05)):
                break
            if time.monotonic() < next_frame_at:
                continue
            ok, frame = capture.read()
            if not ok or frame is None:
                capture.release()
                capture = None
                ended = True
                service.idle()
                service.message = "Video replay complete. No camera was opened."
                continue
            frame_index += 1
            captured_at = service.clock()
            try:
                observation, status, elapsed = pose.infer(frame)
                service.observe(token, observation, status, elapsed, fps)
                image = pose.preview(frame, observation, status)
                service.publish_preview(token, image, captured_at)
                del image
            finally:
                del frame
            # No frame skipping. Slow inference is visible as slower replay, not
            # silently relabelled as successful real-time performance.
            next_frame_at = max(next_frame_at + 1 / fps, time.monotonic())
    except Exception as exc:
        service.camera_error(f"Local video replay failed: {type(exc).__name__}: {exc}")
    finally:
        if capture is not None:
            capture.release()
        service.close()
