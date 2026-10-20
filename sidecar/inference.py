"""Pinned OpenCV 5 DNN person + pose inference. Frames remain in process memory."""

import base64
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from motion import Landmark, Observation
from service import MAX_PREVIEW_JPEG_BYTES

ROOT = Path(__file__).resolve().parent


class OpenCVPose:
    def __init__(self):
        import cv2 as cv
        import numpy as np

        if cv.__version__.split(".")[0] != "5":
            raise RuntimeError(f"OpenCV 5 required; loaded {cv.__version__}")
        self.cv, self.np = cv, np
        cv.setNumThreads(2)
        lock = json.loads((ROOT / "models.lock.json").read_text())
        for entry in lock["files"]:
            data = (ROOT / entry["path"]).read_bytes()
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise RuntimeError(f"Locked Zoo file hash mismatch: {entry['path']}")
        sys.path.insert(0, str(ROOT / "vendor"))
        from mp_persondet import MPPersonDet
        from mp_pose import MPPose

        class OpenCV5PersonDet(MPPersonDet):
            def _postprocess(self, outputs, original_shape, pad_bias):
                # OpenCV 5 graph engine returns Identity_1 before Identity here.
                # The unchanged Zoo wrapper assumes boxes then scores. Match the
                # model's UNIQUE output shapes instead of relying on ordering.
                boxes = [o for o in outputs if o.shape == (1, 2254, 12)]
                scores = [o for o in outputs if o.shape == (1, 2254, 1)]
                if len(boxes) != 1 or len(scores) != 1 or len(outputs) != 2:
                    raise RuntimeError("Unexpected locked person model outputs")
                return super()._postprocess([boxes[0], scores[0]], original_shape, pad_bias)

        class OpenCV5Pose(MPPose):
            def _postprocess(self, outputs, *args):
                shapes = [(1, 195), (1, 1), (1, 256, 256, 1), (1, 64, 64, 39), (1, 117)]
                ordered = []
                for shape in shapes:
                    matches = [o for o in outputs if o.shape == shape]
                    if len(matches) != 1:
                        raise RuntimeError(f"Unexpected locked pose model output: {shape}")
                    ordered.append(matches[0])
                if len(outputs) != len(shapes):
                    raise RuntimeError("Unexpected locked pose model output count")
                return super()._postprocess(ordered, *args)

        self.detector = OpenCV5PersonDet(str(ROOT / "models/person_detection_mediapipe_2023mar.onnx"),
                                    scoreThreshold=0.65,
                                    backendId=cv.dnn.DNN_BACKEND_OPENCV,
                                    targetId=cv.dnn.DNN_TARGET_CPU)
        self.pose = OpenCV5Pose(str(ROOT / "models/pose_estimation_mediapipe_2023mar.onnx"),
                           confThreshold=0.65,
                           backendId=cv.dnn.DNN_BACKEND_OPENCV,
                           targetId=cv.dnn.DNN_TARGET_CPU)
        # Actual forward passes of BOTH models, without photographs or a camera.
        zero = np.zeros((480, 640, 3), dtype=np.uint8)
        started = time.perf_counter()
        self.detector.infer(zero)
        fixture = np.array([220, 120, 420, 400, 320, 300, 320, 100,
                            320, 200, 320, 140, 1.0], dtype=np.float32)
        self.pose.infer(zero, fixture)
        self.runtime = {"opencv": cv.__version__, "verified": True,
                        "numpy": np.__version__, "zooCommit": lock["commit"],
                        "verification": "locked hashes + both zero-image DNN forwards + exact output shapes",
                        "warmupMs": round((time.perf_counter() - started) * 1000, 2)}

    def infer(self, frame):
        started = time.perf_counter()
        frame = self._input_frame(frame)
        people = self.detector.infer(frame)
        if len(people) != 1:
            return None, "no-person" if len(people) == 0 else "low-confidence", self._ms(started)
        result = self.pose.infer(frame, people[0].copy())
        if result is None:
            return None, "low-confidence", self._ms(started)
        points, pose_confidence = result[1], float(result[-1])
        height, width = frame.shape[:2]

        def point(index):
            x, y, _, visibility, presence = map(float, points[index])
            confidence = min(visibility, presence)
            if not 0 <= x < width or not 0 <= y < height:
                confidence = 0.0
            return Landmark(x, y, confidence)

        # MediaPipe anatomical left/right; input is never horizontally flipped.
        observation = Observation(point(11), point(12), point(15), point(16),
                                  min(float(people[0][-1]), pose_confidence))
        return observation, "tracking", self._ms(started)

    def _input_frame(self, frame):
        if frame.shape[1] > 640:
            return self.cv.resize(frame, (640, max(1, int(frame.shape[0] * 640 / frame.shape[1]))))
        return frame

    def preview(self, frame, observation, status):
        """Render the same inferred frame in memory; no camera read or file writes."""
        frame = self._input_frame(frame)
        height, width = frame.shape[:2]
        scale = min(1.0, 320 / width, 640 / height)
        out_width, out_height = max(1, int(width * scale)), max(1, int(height * scale))
        image = self.cv.resize(frame, (out_width, out_height))
        visibility = {key: False for key in ("leftShoulder", "rightShoulder", "leftWrist", "rightWrist")}
        confidences = []
        if observation is not None:
            confidences.append(observation.confidence)
            points = (("leftShoulder", "L shoulder", observation.left_shoulder),
                      ("rightShoulder", "R shoulder", observation.right_shoulder),
                      ("leftWrist", "L wrist", observation.left_wrist),
                      ("rightWrist", "R wrist", observation.right_wrist))
            for key, label, point in points:
                confidences.append(point.confidence)
                in_bounds = (math.isfinite(point.x) and math.isfinite(point.y)
                             and 0 <= point.x < width and 0 <= point.y < height)
                visible = in_bounds and math.isfinite(point.confidence) and .65 <= point.confidence <= 1
                visibility[key] = bool(visible)
                if in_bounds:
                    position = (int(point.x * out_width / width), int(point.y * out_height / height))
                    color = (105, 224, 150) if visible else (44, 164, 255)
                    self.cv.circle(image, position, 4, color, -1, self.cv.LINE_AA)
                    text_position = (max(0, min(out_width - 70, position[0] + 6)), max(12, position[1] - 7))
                    self.cv.putText(image, label, text_position, self.cv.FONT_HERSHEY_SIMPLEX,
                                    .35, color, 1, self.cv.LINE_AA)
        confidence = min(confidences) if confidences else 0.0
        confidence = float(max(0, min(1, confidence))) if math.isfinite(confidence) else 0.0
        ok, encoded = self.cv.imencode(".jpg", image, [self.cv.IMWRITE_JPEG_QUALITY, 65])
        if not ok or encoded.nbytes > MAX_PREVIEW_JPEG_BYTES:
            raise RuntimeError("Local preview JPEG unavailable or exceeds bound")
        return {"jpeg": "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii"),
                "width": out_width, "height": out_height, "visibility": visibility,
                "confidence": round(confidence, 3)}

    @staticmethod
    def _ms(started):
        return round((time.perf_counter() - started) * 1000, 3)
