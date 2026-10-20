"""Optional pinned Google Full IMAGE inference for explicit local-video tests.

No capture, download or temporal pose cache. The existing OpenCV backend remains
the default. Use scripts/run-local-pose.py to block external runtime networking.
"""
import hashlib
import json
import math
from pathlib import Path
import time

from inference import OpenCVPose
from motion import Landmark, Observation

ROOT = Path(__file__).resolve().parent


class MediaPipeFullPose(OpenCVPose):
    def __init__(self):
        # Do not initialize the Zoo graph: only its unchanged image/preview
        # utilities are shared. Optional dependencies are imported on selection.
        pin = json.loads((ROOT / "mediapipe-full.lock.json").read_text())
        model = pin["model"]
        data = (ROOT / model["path"]).read_bytes()
        if len(data) != model["bytes"] or hashlib.sha256(data).hexdigest() != model["sha256"]:
            raise RuntimeError("Pinned official Full model bytes/SHA256 mismatch")
        import cv2 as cv
        import numpy as np
        import mediapipe as mp

        actual = {"mediapipe": mp.__version__, "opencv": cv.__version__, "numpy": np.__version__}
        if actual != pin["packages"]:
            raise RuntimeError(f"Optional Full runtime differs from the separate lock: {actual}")
        if (pin["runningMode"] != "IMAGE" or pin["delegate"] != "CPU"
                or pin["admissionThreshold"] != .65):
            raise RuntimeError("Full backend requires the evaluated CPU/IMAGE/0.65 configuration")
        self.cv, self.np, self.mp = cv, np, mp
        self.threshold = pin["admissionThreshold"]
        cv.setNumThreads(2)
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=data,
                                             delegate=mp.tasks.BaseOptions.Delegate.CPU),
            running_mode=mp.tasks.vision.RunningMode.IMAGE, num_poses=2,
            min_pose_detection_confidence=self.threshold,
            min_pose_presence_confidence=self.threshold,
            min_tracking_confidence=self.threshold, output_segmentation_masks=False)
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.runtime = {**actual, "verified": True, "poseBackend": "mediapipe-full",
                        "runningMode": "IMAGE", "delegate": "CPU", "modelSha256": model["sha256"],
                        "verification": "pinned official task bytes and runtime + initialized CPU IMAGE graph; events require actual inference",
                        "confidenceMeaning": "0.65 is a conservative task-admission lower bound, not an exposed global score; joints use min(visibility,presence)",
                        "networkPolicy": "runtime may emit utilization telemetry; use the loopback-only macOS launcher"}

    def infer(self, frame):
        started = time.perf_counter()
        frame = self._input_frame(frame)
        height, width = frame.shape[:2]
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                              data=self.cv.cvtColor(frame, self.cv.COLOR_BGR2RGB))
        poses = self.landmarker.detect(image).pose_landmarks
        if len(poses) != 1:
            return None, "no-person" if not poses else "low-confidence", self._ms(started)
        points = poses[0]
        if len(points) != 33:
            return None, "low-confidence", self._ms(started)

        def point(index):
            p = points[index]
            values = (p.x, p.y, p.visibility, p.presence)
            valid = (all(type(v) in (int, float) and math.isfinite(v) for v in values)
                     and 0 <= p.x < 1 and 0 <= p.y < 1
                     and 0 <= p.visibility <= 1 and 0 <= p.presence <= 1)
            if not valid:
                return Landmark(0.0, 0.0, 0.0)
            return Landmark(p.x * width, p.y * height, min(p.visibility, p.presence))

        # MediaPipe anatomical indices, top-left origin, no reflection. The task
        # admits poses at .65 but exposes no actual detector/global presence score.
        observation = Observation(point(11), point(12), point(15), point(16), self.threshold)
        return observation, "tracking", self._ms(started)

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None
