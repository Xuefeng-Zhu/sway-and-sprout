#!/usr/bin/env python3
"""Restore ONLY immutable official Zoo files, verifying SHA256 before writing."""

import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent


def main():
    lock = json.loads((ROOT / "models.lock.json").read_text())
    commit = lock["commit"]
    for entry in lock["files"]:
        path = ROOT / entry["path"]
        if path.parent not in (ROOT / "models", ROOT / "vendor"):
            raise ValueError("Unexpected locked destination")
        allowed = [f"https://raw.githubusercontent.com/opencv/opencv_zoo/{commit}/models/",
                   f"https://media.githubusercontent.com/media/opencv/opencv_zoo/{commit}/models/"]
        if not any(entry["url"].startswith(prefix) for prefix in allowed):
            raise ValueError("Only immutable official Zoo URLs are permitted")
        data = path.read_bytes() if path.exists() else None
        if data is None or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            with urllib.request.urlopen(entry["url"], timeout=30) as response:
                data = response.read(entry["bytes"] + 1)
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Verification failed: {entry['path']}")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        print(f"verified {entry['path']} {entry['sha256']}")


if __name__ == "__main__":
    main()
