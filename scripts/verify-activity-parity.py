#!/usr/bin/env python3
"""Compare synthetic Python/Java activity events and the real JS scoring reducer.

Requires an existing JDK and Node. No models, media, capture, sockets or installs.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sidecar"))
from test_activity import event_times, traces


def verify(java_home):
    package = ROOT / "android/app/src/main/java/com/togethermove/tv"
    driver = ROOT / "android/tests/com/togethermove/tv/ActivityParityTest.java"
    with tempfile.TemporaryDirectory(prefix="sway-activity-java-") as target:
        subprocess.run([str(java_home / "bin/javac"), "-d", target,
                        str(package / "PoseGestureMachine.java"), str(package / "ActivityMachine.java"),
                        str(driver)], check=True, capture_output=True, text=True)
        output = subprocess.run([str(java_home / "bin/java"), "-cp", target,
                                 "com.togethermove.tv.ActivityParityTest",
                                 str(ROOT / "tests/fixtures/activity-traces.csv")],
                                check=True, capture_output=True, text=True).stdout
    java = {}
    for line in output.splitlines():
        name, values = line.split("|", 1)
        java[name] = [int(value) for value in values.split(",") if value]
    python = {name:event_times(rows) for name,rows in traces().items()}
    if java != python:
        raise AssertionError("Java/Python synthetic event timing differs")
    code = """
import fs from 'node:fs';
import {createMotionState,acceptMotionEvent} from './src/motion.js';
const cases=JSON.parse(fs.readFileSync(0,'utf8')), counts={};
for(const [name,times] of Object.entries(cases)){
 let state=createMotionState('synthetic-parity-round','activity');
 for(let i=0;i<times.length;i++){
  const event={seq:i+1,roundId:state.roundId,gesture:'activity',confidence:1,ageMs:0};
  state=acceptMotionEvent(state,event,{active:true});
  const duplicate=acceptMotionEvent(state,event,{active:true});
  if(duplicate!==state)throw Error('Duplicate activity event was consumed twice');
 }
 if(state.count!==Math.min(6,times.length))throw Error('Event/ray mismatch');
 counts[name]=state.count;
}
let bounded=createMotionState('bounded-synthetic-round','activity');
for(let seq=1;seq<=20;seq++)bounded=acceptMotionEvent(bounded,
 {seq,roundId:bounded.roundId,gesture:'activity',confidence:1,ageMs:0},{active:true});
if(bounded.count!==6||!bounded.completed)throw Error('Six-ray bound failed');
process.stdout.write(JSON.stringify({counts,boundedRays:bounded.count}));
"""
    js = json.loads(subprocess.run(["node", "--input-type=module", "-e", code], cwd=ROOT,
                                  input=json.dumps(python), check=True, capture_output=True, text=True).stdout)
    return {"passed":True, "scope":"Synthetic functional parity only; no inference or recognition accuracy claim",
            "cases":{name:{"frames":len(traces()[name]), "eventTimesMs":times,
                            "jsRays":js["counts"][name]} for name,times in python.items()},
            "duplicateEventsCounted":False, "boundedRays":js["boundedRays"],
            "cameraUsed":False, "publicMediaProcessed":False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True, help="Existing JDK; never downloaded")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.java_home)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
