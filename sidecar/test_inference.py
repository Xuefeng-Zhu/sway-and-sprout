"""Actual OpenCV5 DNN forwards + SYNTHETIC positive tensors; never a camera."""

import base64
import unittest

from inference import OpenCVPose


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = OpenCVPose()

    def test_actual_locked_runtime_and_blank_detector_forward(self):
        pipeline = self.pipeline
        self.assertEqual(pipeline.runtime["opencv"].split(".")[0], "5")
        self.assertTrue(pipeline.runtime["verified"])
        blank = pipeline.np.zeros((480, 640, 3), pipeline.np.uint8)
        observation, status, elapsed = pipeline.infer(blank)
        self.assertIsNone(observation)
        self.assertEqual(status, "no-person")
        self.assertGreater(elapsed, 0)

    def test_actual_blank_inference_has_decodable_local_preview(self):
        pipeline = self.pipeline
        frame = pipeline.np.zeros((480, 640, 3), pipeline.np.uint8)
        observation, status, _ = pipeline.infer(frame)
        preview = pipeline.preview(frame, observation, status)
        raw = base64.b64decode(preview["jpeg"].split(",", 1)[1], validate=True)
        decoded = pipeline.cv.imdecode(pipeline.np.frombuffer(raw, pipeline.np.uint8),
                                       pipeline.cv.IMREAD_COLOR)
        self.assertEqual(status, "no-person")
        self.assertEqual(decoded.shape, (240, 320, 3))
        self.assertFalse(any(preview["visibility"].values()))
        self.assertEqual(preview["confidence"], 0)

    def test_synthetic_detector_positive_tensors_in_reverse_order(self):
        pipeline, np = self.pipeline, self.pipeline.np
        boxes = np.zeros((1, 2254, 12), np.float32)
        scores = np.full((1, 2254, 1), -100, np.float32)
        scores[0, 1000, 0] = 10
        boxes[0, 1000, :4] = [0, 0, 20, 40]
        result = pipeline.detector._postprocess([scores, boxes], np.array([640, 480]), np.array([0, 80]))
        self.assertEqual(result.shape, (1, 13))

    def test_synthetic_pose_positive_confidence_exercises_full_postprocess(self):
        pipeline, np = self.pipeline, self.pipeline.np
        blank = np.zeros((480, 640, 3), np.uint8)
        fixture = np.array([220, 120, 420, 400, 320, 300, 320, 100,
                            320, 200, 320, 140, 1.0], np.float32)
        blob, *args = pipeline.pose._preprocess(blank, fixture)
        pipeline.pose.model.setInput(blob)
        outputs = list(pipeline.pose.model.forward(pipeline.pose.model.getUnconnectedOutLayersNames()))
        # Override confidence for postprocessing coverage ONLY. Not a person detection.
        outputs = [np.ones_like(o) if o.shape == (1, 1) else o for o in outputs]
        result = pipeline.pose._postprocess(list(reversed(outputs)), *args, np.array([640, 480]))
        self.assertEqual(result[1].shape, (39, 5))
        self.assertEqual(result[3].shape, (480, 640))

    def test_unknown_model_output_shapes_fail_closed(self):
        pipeline, np = self.pipeline, self.pipeline.np
        with self.assertRaises(RuntimeError):
            pipeline.detector._postprocess([np.zeros((1, 1))], np.array([640, 480]), np.array([0, 0]))
        with self.assertRaises(RuntimeError):
            pipeline.pose._postprocess([np.zeros((1, 1))])


if __name__ == "__main__":
    unittest.main()
