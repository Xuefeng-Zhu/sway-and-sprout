#!/usr/bin/env python3
"""Explicit opt-in restoration of the hash-pinned official Google Full task.

Never called by inference. This is separate from the existing OpenCV Zoo lock.
"""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"


def restore(root=ROOT):
    pin = json.loads((root / "mediapipe-full.lock.json").read_text())["model"]
    if pin["path"] != "models/pose_landmarker_full.task" or pin["url"] != MODEL_URL:
        raise ValueError("Unexpected official model location")
    target = root / pin["path"]
    if target.is_symlink():
        raise ValueError("Model destination must not be a symbolic link")
    if target.exists():
        data = target.read_bytes()
        if len(data) == pin["bytes"] and hashlib.sha256(data).hexdigest() == pin["sha256"]:
            print("Pinned official Full model already present")
            return
        raise ValueError("Existing model differs from the pin; refusing to overwrite it")
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(pin["url"], timeout=45) as response:
        if response.geturl() != MODEL_URL:
            raise ValueError("Unexpected model redirect")
        data = response.read(pin["bytes"] + 1)
    if len(data) != pin["bytes"] or hashlib.sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError("Official download does not match the pinned bytes and SHA256; no model installed")
    # Exclusive create prevents a concurrent restore from replacing a file.
    with target.open("xb") as stream:
        stream.write(data)
    print(json.dumps({"model": pin["path"], "bytes": len(data), "sha256": pin["sha256"]}))


if __name__ == "__main__":
    restore()
