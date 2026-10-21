#!/usr/bin/env python3
"""Compile Android sources and host checks with explicit existing local caches.

No Gradle dependency resolution, APK, emulator, inference, media or downloads.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True, text=True).stdout.strip()


def verify(java_home, android_jar, cache_root):
    lock = json.loads((ROOT / "android/native-video-assets.lock.json").read_text())
    artifacts = [pin for pin in lock["artifacts"] if pin["role"] in ("core", "api", "image-reference-api")]
    checked = []
    for pin in artifacts:
        artifact = cache_root / pin["target"]
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError("Existing regular pinned AAR required: " + str(artifact))
        data = artifact.read_bytes()
        if len(data) != pin["bytes"] or hashlib.sha256(data).hexdigest() != pin["sha256"]:
            raise ValueError("Existing AAR does not match its frozen pin: " + str(artifact))
        checked.append({"file":artifact.name, "sha256":pin["sha256"], "bytes":len(data)})
    build_config = cache_root / "android/app/build/generated/source/buildConfig/debug/com/togethermove/tv/BuildConfig.java"
    if not android_jar.is_file() or not build_config.is_file():
        raise ValueError("Existing Android SDK jar and generated debug BuildConfig required")
    with tempfile.TemporaryDirectory(prefix="sway-native-source-") as directory:
        temporary = Path(directory)
        jars = [android_jar]
        for pin in artifacts:
            with zipfile.ZipFile(cache_root / pin["target"]) as archive:
                target = temporary / (Path(pin["target"]).name + ".jar")
                target.write_bytes(archive.read("classes.jar"))
                jars.append(target)
        sources = sorted((ROOT / "android/app/src/main/java").rglob("*.java"))
        sources += sorted((ROOT / "android/app/src/debug/java").rglob("*.java"))
        sources.append(build_config)
        run([java_home / "bin/javac", "--release", "17", "-cp", os.pathsep.join(map(str,jars)),
             "-d", temporary / "debug", *sources])
        base = ROOT / "android/app/src/main/java/com/togethermove/tv"
        debug_base = ROOT / "android/app/src/debug/java/com/togethermove/tv"
        tests = ROOT / "android/tests/com/togethermove/tv"
        classes = ["PoseGestureMachine", "PoseCoordinates", "MoveNetCrop", "ActivityMachine", "ReplayFrameGuard", "MotionQuery"]
        debug_classes = ["NativeVideoCase", "ReplayAttemptTiming"]
        checks = ["NativePoseMathTest", "MoveNetCropTest", "MotionQueryTest", "ReplayFrameGuardTest",
                  "NativeVideoCaseTest", "ReplayAttemptTimingTest"]
        run([java_home / "bin/javac", "--release", "17", "-d", temporary / "host",
             *[base / (name + ".java") for name in classes],
             *[debug_base / (name + ".java") for name in debug_classes],
             *[tests / (name + ".java") for name in checks]])
        outputs = {name:run([java_home / "bin/java", "-cp", temporary / "host", "com.togethermove.tv." + name])
                   for name in checks}
    return {"passed":True, "scope":"Compile-only Android sources and synthetic/fake-clock host Java checks",
            "sourceCount":len(sources), "aarPins":checked, "hostChecks":outputs,
            "apkBuilt":False, "emulatorUsed":False, "cameraUsed":False, "mediaProcessed":False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--android-jar", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True, help="Existing checkout containing pinned AARs/BuildConfig")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.java_home, args.android_jar, args.cache_root)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
