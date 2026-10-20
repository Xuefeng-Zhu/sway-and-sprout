#!/usr/bin/env python3
"""Run the optional Full model on an explicit file with loopback-only networking.

No model download, dependency install, camera mode, or arbitrary command forwarding.
"""
import argparse
import os
from pathlib import Path
import shutil
import sys


def command(argv=None, *, root=None):
    root = root or Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "replay"))
    parser.add_argument("video", type=Path)
    manifests = parser.add_mutually_exclusive_group()
    manifests.add_argument("--expected", type=Path)
    manifests.add_argument("--annotation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete-goal", action="store_true")
    parser.add_argument("--seconds", type=float, help="verify only: decode at most30 seconds (default30)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if sys.platform != "darwin" or shutil.which("sandbox-exec") is None:
        parser.error("This launcher requires macOS sandbox-exec; refusing an unsandboxed fallback")
    if (args.seconds is not None and not 0 < args.seconds <= 30) or not 1024 <= args.port <= 65535:
        parser.error("Duration must be greater than zero and at most30 seconds; port1024–65535")
    try:
        video = args.video.expanduser().resolve(strict=True)
    except OSError as exc:
        parser.error(str(exc))
    if not video.is_file() or not 0 < video.stat().st_size <= 512 * 1024 * 1024:
        parser.error("Select an existing local video file of at most512 MiB")
    python = root / ".toolchain/mediapipe-venv/bin/python"
    if not python.is_file():
        parser.error("Restore the separately pinned optional environment first; see docs/MEDIAPIPE-FULL-VERIFICATION.md")
    prefix = [shutil.which("sandbox-exec"), "-f", str(root / "sidecar/local-model.sb"), str(python), "-B"]
    if args.mode == "verify":
        if args.output is None:
            parser.error("verify requires --output for its scalar JSON report")
        cmd = prefix + [str(root / "sidecar/verify_video.py"), str(video),
                        "--pose-backend", "mediapipe-full", "--seconds", str(args.seconds if args.seconds is not None else 30),
                        "--output", str(args.output.expanduser().resolve())]
        if args.expected or args.annotation:
            cmd += ["--expected" if args.expected else "--annotation",
                    str((args.expected or args.annotation).expanduser().resolve(strict=True))]
        if args.require_complete_goal:
            cmd += ["--require-complete-goal"]
    else:
        if args.expected or args.annotation or args.output or args.require_complete_goal or args.seconds is not None:
            parser.error("Expectation, duration and report options apply to verify only; replay uses the selected file cadence")
        cmd = prefix + [str(root / "sidecar/run.py"), "--video", str(video),
                        "--pose-backend", "mediapipe-full", "--port", str(args.port)]
    return root, cmd


def main():
    root, cmd = command()
    cache = root / ".toolchain/mediapipe-cache"
    cache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MPLCONFIGDIR=str(cache / "matplotlib"), XDG_CACHE_HOME=str(cache))
    os.execve(cmd[0], cmd, env)


if __name__ == "__main__":
    main()
