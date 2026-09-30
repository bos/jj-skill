"""Prove the semantic judge rejects historical wrong first plans, not only exit failures."""

import argparse, json, tempfile
from pathlib import Path
from runner import execute_case

MUTANTS = {
    "c01": [["jj", "commit", "-m", "app: fix output"]],
    "c02": [["jj", "restore"]],
    "c03": [["jj", "workspace", "forget", "scratch", "active"]],
    "c04": [
        ["jj", "squash", "--into", "@-", "--use-destination-message"],
        ["jj", "describe", "-m", "feature: complete"],
    ],
    "c05": [["jj", "commit", "-m", "--", "--cleanup"]],
    "c06": [["jj", "diff", "--git", "-r", "@-", "-r", "@"]],
    "c07": [["jj", "diff", "--stat", "--summary"]],
    "c08": [["jj", "diff", "--check"]],
    "c09": [["jj", "show", "review", "--git", "--", "app.txt"]],
    "c10": [["jj", "-R", "../sibling", "diff", "--git", "docs/readme.txt"]],
    "c11": [
        [
            "jj",
            "evolog",
            "--no-graph",
            "-T",
            'commit_id.short() ++ "\\t" ++ description.first_line() ++ "\\n"',
        ]
    ],
    "c12": [
        [
            "jj",
            "log",
            "--no-graph",
            "-n",
            "2",
            "-T",
            'commit_id.short() ++ "\\t" ++ description ++ "\\n"',
        ]
    ],
    "c13": [
        [
            "jj",
            "file",
            "annotate",
            "-T",
            'change_id.short() ++ "\\t" ++ line_number ++ "\\t" ++ content',
            "app.txt",
        ]
    ],
    "c14": [["jj", "rebase", "-s", "descendants(@) ~ @", "-d", "main"]],
    "c15": [["jj", "abandon", "obsolete"]],
    "c16": [
        [
            "jj",
            "workspace",
            "list",
            "-T",
            'workspace ++ "\\t" ++ change_id.short() ++ "\\t" ++ '
            'description.first_line() ++ "\\n"',
        ]
    ],
}
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--jj", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    rows = []
    for case, commands in MUTANTS.items():
        with tempfile.TemporaryDirectory(prefix="jj-negative-canary-") as root:
            grade = execute_case(case, [dict(cwd="main", argv=v) for v in commands], a.jj, root)
            rows.append(grade)
            print(case, "REJECTED" if not grade["passed"] else "FALSE PASS", flush=True)
    Path(a.output).write_text(json.dumps(rows, indent=2))
    raise SystemExit(int(any(r["passed"] for r in rows)))
