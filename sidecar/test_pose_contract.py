"""Synthetic tensors/blank arrays only: no camera, person image or HTTP service.

Exercise the pinned Zoo decoder and the application's extraction together.
The camera-result logs are evidence of a different, human-input test.
"""

import itertools
import math
from unittest import mock
import unittest

from inference import OpenCVPose
from motion import GestureMachine


class PoseContractOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = OpenCVPose()

    def setUp(self):
        self.np = self.pipeline.np
        self.frame = self.np.zeros((480, 640, 3), self.np.uint8)

    def decode(self, coordinates, full_body=(320, 100), visibility=.92, presence=.86):
        np, pipeline = self.np, self.pipeline
        person = np.array([220, 120, 420, 400, 320, 300, *full_body,
                           320, 200, 320, 140, .99], np.float32)
        _, box, angle, matrix, padding = pipeline.pose._preprocess(self.frame, person.copy())
        landmarks = np.zeros((39, 5), np.float32)
        landmarks[:, :2] = [128, 128]
        landmarks[:, 3] = math.log(visibility / (1 - visibility))
        landmarks[:, 4] = math.log(presence / (1 - presence))
        for index, point in coordinates.items():
            # Independent forward transform from frame pixels into model input.
            rotated = matrix @ np.r_[np.array(point) - padding, 1]
            landmarks[index, :2] = rotated * 256 / (box[1] - box[0])
        outputs = [landmarks.reshape(1, 195), np.array([[.97]], np.float32),
                   np.zeros((1, 256, 256, 1), np.float32),
                   np.zeros((1, 64, 64, 39), np.float32),
                   np.zeros((1, 117), np.float32)]
        result = pipeline.pose._postprocess(list(reversed(outputs)), box, angle, matrix,
                                            padding, np.array([640, 480]))
        with mock.patch.object(pipeline.detector, "infer", return_value=person[None, :]), \
                mock.patch.object(pipeline.pose, "infer", return_value=result):
            observation, status, _ = pipeline.infer(self.frame)
        self.assertEqual(status, "tracking")
        return observation, angle

    @staticmethod
    def coordinates(left_y=350, right_y=350):
        return {11: (390, 220), 12: (250, 220),
                15: (390, left_y), 16: (250, right_y)}

    def test_image_pixels_survive_padding_scale_and_rotation(self):
        coordinates = self.coordinates(140, 350)
        for full_body in ((320, 100), (420, 200), (220, 200), (520, 300)):
            with self.subTest(full_body=full_body):
                observation, _ = self.decode(coordinates, full_body)
                actual = (observation.left_shoulder, observation.right_shoulder,
                          observation.left_wrist, observation.right_wrist)
                for point, index in zip(actual, (11, 12, 15, 16)):
                    self.np.testing.assert_allclose((point.x, point.y), coordinates[index], atol=.0001)
                self.assertAlmostEqual(observation.confidence, .97, places=6)

    def test_visibility_and_presence_sigmoid_are_not_coordinates_or_world_output(self):
        observation, _ = self.decode(self.coordinates(), visibility=.91, presence=.73)
        for point in (observation.left_shoulder, observation.right_shoulder,
                      observation.left_wrist, observation.right_wrist):
            self.assertAlmostEqual(point.confidence, .73, places=6)
            self.assertGreater(point.x, 100)  # Deliberately zero-valued world tensor is unused.

    def test_out_of_image_wrist_is_rejected_without_swapping_anatomical_sides(self):
        coordinates = self.coordinates()
        coordinates[15] = (650, 350)
        observation, _ = self.decode(coordinates)
        self.assertEqual(observation.left_wrist.confidence, 0)
        self.assertGreater(observation.right_wrist.confidence, .65)
        machine = GestureMachine()
        machine.update(observation, 0)
        self.assertEqual(machine.status, "low-confidence")

    def test_resizing_happens_before_detector_and_pose_in_same_coordinate_system(self):
        pipeline, np = self.pipeline, self.np
        frame = np.zeros((960, 1280, 3), np.uint8)
        person = np.array([[220, 120, 420, 400, 320, 300, 320, 100,
                            320, 200, 320, 140, .99]], np.float32)
        points = np.zeros((39, 5), np.float32)
        for index, coordinate in self.coordinates().items():
            points[index, :2] = coordinate
            points[index, 3:] = [.92, .86]
        result = [None, points, None, None, None, .97]
        with mock.patch.object(pipeline.detector, "infer", return_value=person) as detector, \
                mock.patch.object(pipeline.pose, "infer", return_value=result) as pose:
            observation, status, _ = pipeline.infer(frame)
        self.assertEqual(status, "tracking")
        self.assertEqual(detector.call_args.args[0].shape, (480, 640, 3))
        self.assertIs(pose.call_args.args[0], detector.call_args.args[0])
        self.assertEqual(observation.left_shoulder.x, 390)
        self.assertEqual(observation.left_wrist.y, 350)

    def test_every_pose_output_permutation_maps_by_unique_shape(self):
        np, pipeline = self.np, self.pipeline
        box = np.array([[0, 0], [256, 256]], np.int32)
        matrix = np.array([[1., 0., 0.], [0., 1., 0.]])
        landmarks = np.zeros((1, 195), np.float32)
        landmarks.reshape(39, 5)[:, :2] = [128, 128]
        outputs = [landmarks, np.array([[.99]], np.float32),
                   np.zeros((1, 256, 256, 1), np.float32),
                   np.zeros((1, 64, 64, 39), np.float32),
                   np.zeros((1, 117), np.float32)]
        for order in itertools.permutations(range(5)):
            tensors = [outputs[i].copy() for i in order]
            result = pipeline.pose._postprocess(tensors, box, 0, matrix,
                                                np.array([0, 0]), np.array([256, 256]))
            self.np.testing.assert_allclose(result[1][11, :2], [128, 128])
            self.assertAlmostEqual(float(result[-1]), .99, places=5)

    def test_decoded_pixel_poses_produce_left_then_right_after_neutral(self):
        machine, now, emitted, seen = GestureMachine(), 0, [], set()
        # Shoulder width140px => wrists down require y>248; up require y<178.
        stages = [(350, 350, 500), (235, 350, 150), (205, 350, 150),
                  (140, 350, 500), (350, 350, 550), (350, 235, 150),
                  (350, 205, 150), (350, 140, 500)]
        for left_y, right_y, duration in stages:
            observation, _ = self.decode(self.coordinates(left_y, right_y))
            for _ in range(duration // 50):
                event = machine.update(observation, now)
                now += 50
                seen.add(machine.status)
                if event:
                    emitted.append(event["gesture"])
        self.assertEqual(emitted, ["left-raise", "right-raise"])
        self.assertIn("tracking", seen)
        self.assertIn("hold", seen)


if __name__ == "__main__":
    unittest.main()
