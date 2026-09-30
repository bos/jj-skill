#!/usr/bin/env python3
"""Six independent actual-engine calls, one old/new pair per installed engine."""

import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapters", type=Path, required=True)
    parser.add_argument("--old-skill", type=Path, required=True)
    parser.add_argument("--new-skill", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jj", required=True)
    parser.add_argument("--parallel", type=int, default=3)
    args = parser.parse_args()
    groups = []
    for engine in ("codex", "claude", "glm"):
        adapter = HERE / "glm_adapter_300.py" if engine == "glm" else (
            args.adapters / (engine + "_adapter.py"))
        conditions = [("old", args.old_skill), ("new", args.new_skill)]
        if engine == "claude":
            conditions.reverse()
        jobs = []
        for condition, skill in conditions:
            output = args.output / (engine + "-" + condition)
            cmd = [sys.executable, str(HERE / "focused_runner.py"), "run",
                   "--engine", engine, "--condition", condition, "--skill", str(skill),
                   "--adapter", str(adapter), "--jj", args.jj, "--output", str(output)]
            jobs.append((engine, condition, cmd))
        groups.append(jobs)

    def execute(job):
        engine, condition, cmd = job
        process = subprocess.run(cmd, text=True, capture_output=True)
        return {"engine": engine, "condition": condition, "exit_code": process.returncode,
                "summary_stdout": process.stdout, "stderr": process.stderr}

    def execute_pair(group):
        # Counterbalance ordered calls; old/new never run concurrently on one engine.
        return [execute(job) for job in group]

    args.output.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        results = [result for pair in pool.map(execute_pair, groups) for result in pair]
    (args.output / "transport-summary.json").write_text(json.dumps(results, indent=2) + "\n")
    # Summaries contain scores/transport status only, never raw engine plans.
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
