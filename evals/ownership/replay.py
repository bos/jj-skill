#!/usr/bin/env python3
"""Replay recorded focused plans without calling an engine."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from focused_runner import dump, evaluate_plan, freeze


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jj", default=shutil.which("jj"))
    args = parser.parse_args()
    freeze()
    jj = str(Path(args.jj).resolve())
    version = subprocess.check_output([jj, "--version"], text=True).strip()
    if version != "jj 0.45.1":
        raise SystemExit("Expected exact jj 0.45.1, got " + version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plans = json.loads(args.plans.read_text())["plans"]
    results = [evaluate_plan(plan, plan["case_id"], jj, args.output.parent) for plan in plans]
    dump(args.output, dict(
        jj_version=version, jj_binary=jj,
        jj_sha256=hashlib.sha256(Path(jj).read_bytes()).hexdigest(), cases=results,
    ))
    print(json.dumps([
        {key: result[key] for key in ["case_id", "safety_pass", "first_try_task_success"]}
        for result in results
    ], indent=2))


if __name__ == "__main__":
    main()
