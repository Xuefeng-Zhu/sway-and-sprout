"""Build a reviewable inline CloudFormation template locally; never calls AWS."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_template():
    source = (ROOT / "garden_backup.py").read_text()
    template = json.loads((ROOT / "garden-backup.resources.json").read_text())
    template["Resources"]["GardenFunction"]["Properties"]["Code"] = {"ZipFile": source}
    template["Metadata"] = {"Status": "Proposed only; no deployment approval",
                            "SourceSha256": hashlib.sha256(source.encode()).hexdigest()}
    result = json.dumps(template, indent=2) + "\n"
    # Direct CloudFormation template bodies must fit within 51,200 bytes.
    if len(result.encode()) > 51200:
        raise ValueError("Template exceeds direct-body limit; inspect rather than upload")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New local JSON path, normally outside source")
    args = parser.parse_args()
    body = build_template()
    with args.output.open("x") as output:
        output.write(body)
    print(json.dumps({"path": str(args.output.resolve()), "bytes": len(body.encode()),
                      "sha256": hashlib.sha256(body.encode()).hexdigest(), "awsCalled": False}))


if __name__ == "__main__":
    main()
