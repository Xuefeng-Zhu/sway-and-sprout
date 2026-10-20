#!/usr/bin/env python3
"""Run actual synthetic tensor/blank-array decoder tests without camera/socket."""
import argparse
import importlib
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(args.project.resolve()/'sidecar'))
    import cv2
    with mock.patch.object(cv2,'VideoCapture',side_effect=AssertionError('No camera or file capture in tensor tests')) as capture, \
            mock.patch.object(socket,'socket',side_effect=AssertionError('No sockets in tensor tests')) as sockets:
        module=importlib.import_module('test_pose_contract')
        suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        result=unittest.TextTestRunner(verbosity=1).run(suite)
    report=dict(testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
                evidenceType='synthetic decoder tensors and blank arrays; no person-image inference',
                cameraAndSocketBlocked=True,captureAttempts=capture.call_count,socketAttempts=sockets.call_count,
                coverage=['pixel recovery through padding/scale/rotation','visibility/presence versus coordinates/world outputs',
                          'anatomical indices11/12/15/16','consistent resized coordinate system','all120 output permutations',
                          'decoded known pixel poses emit left then right'])
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    raise SystemExit(main())
