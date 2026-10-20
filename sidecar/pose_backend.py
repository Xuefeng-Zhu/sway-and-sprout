"""Lazy, explicit pose selection; default behavior retains the pinned Zoo backend."""
from inference import OpenCVPose

BACKENDS = ("opencv", "mediapipe-full")


def create_pose(backend="opencv"):
    if backend == "opencv":
        return OpenCVPose()
    if backend == "mediapipe-full":
        from mediapipe_full import MediaPipeFullPose
        return MediaPipeFullPose()
    raise ValueError(f"Unknown pose backend: {backend}")


def close_pose(pose):
    close = getattr(pose, "close", None)
    if close is not None:
        close()
