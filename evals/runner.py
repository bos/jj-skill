#!/usr/bin/env python3
"""Paired, first-plan jj command-choice evaluation. Python standard library only."""

import argparse
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
DEFAULT_JJ = os.environ.get("JJ_EVAL_JJ") or shutil.which("jj") or "jj"
PREFIX = """You are choosing commands to perform independent tasks in disposable jj repositories.
Only the supplied jj skill and reference files apply. Do not inspect files, call tools, browse,
or ask questions. Return your first complete command plan for each task, without execution
feedback. Do not include guessed fallback/retry commands: every command must be part of the
intended successful workflow. The runner executes argv directly, with no shell expansion.
All tasks use jj 0.45.1, no terminal editor, no pager, no network or remotes. Commands must
operate only in the indicated disposable fixtures. Existing dirty files have the stated owners.
Use short deterministic plans; inspection/help calls cannot provide you feedback in this test.
Return ONLY JSON with shape {"cases":[{"id":"c01","commands":[{"cwd":"main",
"argv":["jj","status"]}]}]}. Each command has cwd and argv, and optional string stdin.
Valid cwd aliases: main, sibling, scratch, active (only where the task provides them).
Use 'jj' as the executable; the runner maps it to the pinned binary. Python 3 is available
for the supplied repository check script. Shell operators, substitutions, and scripts are not
expanded. Supply all sixteen case IDs once, with at least one command each.

<supplied-jj-skill>
"""
SUFFIX = "\n</supplied-jj-skill>\n"


def jj_provenance(jj):
    version = subprocess.check_output([jj, "--version"], text=True).strip()
    if not version.startswith("jj 0.45.1"):
        raise RuntimeError("Expected jj 0.45.1, got " + version)
    binary = Path(shutil.which(jj) or jj).resolve()
    return dict(version=version, sha256=hashlib.sha256(binary.read_bytes()).hexdigest())


def bundle_skill(path):
    path = Path(path)
    files = [path / "SKILL.md"] + sorted((path / "references").glob("*.md"))
    return "\n\n".join(f"--- {p.relative_to(path)} ---\n{p.read_text()}" for p in files)


def prompts(skill):
    cases = json.loads((HERE / "cases.json").read_text())
    return PREFIX + bundle_skill(skill) + SUFFIX, json.dumps({"tasks": cases}, indent=2)


class Fixture:
    def __init__(self, case, jj, root):
        self.case, self.jj, self.root = case, jj, Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.paths = {a: self.root / a for a in ["main", "sibling", "scratch", "active"]}
        self.home = self.root / "isolated-user"
        self.home.mkdir()
        config = self.root / "jj-config.toml"
        config.write_text(
            '[user]\nname="Evaluation"\nemail="eval@example.invalid"\n'
            '[ui]\neditor="false"\npager="cat"\n'
            '[revset-aliases]\n"trunk()"="main"\n'
        )
        self.env = dict(
            os.environ,
            HOME=str(self.home),
            XDG_CONFIG_HOME=str(self.home / "config"),
            XDG_CACHE_HOME=str(self.home / "cache"),
            JJ_CONFIG=str(config),
            JJ_EDITOR="false",
            EDITOR="false",
            VISUAL="false",
            TERM="dumb",
            NO_COLOR="1",
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL="/dev/null",
        )
        for key in list(self.env):
            if any(s in key.upper() for s in ["TOKEN", "API_KEY", "AUTH_TOKEN"]):
                self.env.pop(key, None)
        self.seed()
        self.before = self.fingerprint()
        self.active_change = self.log("active@", "change_id") if case == "c03" else None

    def run(self, argv, cwd="main", stdin=None, timeout=12, checked=False):
        argv = list(argv)
        if argv[0] == "jj":
            argv[0] = self.jj
        started = time.monotonic()
        try:
            r = subprocess.run(
                argv,
                cwd=self.paths[cwd],
                env=self.env,
                input=stdin,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            result = dict(
                argv=argv,
                cwd=cwd,
                returncode=r.returncode,
                stdout=r.stdout,
                stderr=r.stderr,
                elapsed_seconds=time.monotonic() - started,
            )
        except subprocess.TimeoutExpired as exc:
            result = dict(
                argv=argv,
                cwd=cwd,
                returncode=None,
                stdout=str(exc.stdout or ""),
                stderr="TIMEOUT",
                elapsed_seconds=time.monotonic() - started,
            )
        if checked and result["returncode"] != 0:
            raise RuntimeError(json.dumps(result))
        return result

    def jjrun(self, *args, cwd="main"):
        return self.run(["jj", *args], cwd=cwd, checked=True)["stdout"]

    def write(self, path, value, cwd="main"):
        p = self.paths[cwd] / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)

    def commit(self, desc, changes):
        for p, s in changes.items():
            self.write(p, s)
        self.jjrun("commit", "-m", desc)

    def bookmark(self, name, rev="@-"):
        self.jjrun("bookmark", "set", name, "-r", rev)

    def init(self, alias="main"):
        self.paths[alias].mkdir()
        self.run(["jj", "git", "init", "."], cwd=alias, checked=True)
        self.write("app.txt", "alpha\n", alias)
        self.write("notes.txt", "original\n", alias)
        self.jjrun("commit", "-m", "base", cwd=alias)
        self.jjrun("bookmark", "set", "main", "-r", "@-", cwd=alias)

    def seed(self):
        self.init()
        c = self.case
        if c in ["c01", "c02"]:
            self.write("app.txt", "beta\n")
            self.write("notes.txt", "user draft\n")
        elif c == "c03":
            for alias in ["scratch", "active"]:
                self.jjrun(
                    "workspace", "add", "--name", alias, "-r", "main", str(self.paths[alias])
                )
            self.write("scratch-notes.txt", "saved notes\n", "scratch")
            self.write("active-work.txt", "in progress\n", "active")
        elif c == "c04":
            self.commit("feature: initial", {"app.txt": "beta\n"})
            self.write("app.txt", "gamma\n")
            self.jjrun("describe", "-m", "follow-up: polish")
        elif c in ["c05", "c07"]:
            self.write("app.txt", "beta\n")
        elif c == "c06":
            self.commit("parent addition", {"parent-only.txt": "already included\n"})
            self.write("app.txt", "beta\n")
        elif c == "c08":
            self.write(
                "check_whitespace.py",
                "from pathlib import Path\nimport sys\nbad=False\n"
                'for n,line in enumerate(Path("app.txt").read_text().splitlines(),1):\n'
                " if line.rstrip()!=line:\n"
                '  print(f"app.txt:{n}: trailing whitespace"); bad=True\n'
                "sys.exit(int(bad))\n",
            )
            self.jjrun("commit", "-m", "add whitespace check")
            self.write("app.txt", "alpha\ntrailing   \n")
        elif c == "c09":
            self.commit("review change", {"app.txt": "beta\n", "notes.txt": "private note\n"})
            self.bookmark("review")
        elif c == "c10":
            self.init("sibling")
            self.write("docs/readme.txt", "old docs\n", "sibling")
            self.write("other.txt", "old\n", "sibling")
            self.jjrun("commit", "-m", "sibling base", cwd="sibling")
            self.write("docs/readme.txt", "new docs\n", "sibling")
            self.write("other.txt", "new\n", "sibling")
        elif c == "c11":
            self.write("app.txt", "beta\n")
            self.jjrun("describe", "-m", "draft one")
            self.write("app.txt", "gamma\n")
            self.jjrun("describe", "-m", "draft two")
        elif c == "c13":
            self.commit("two lines", {"app.txt": "alpha\nbeta\n"})
        elif c == "c14":
            self.commit("feature bottom", {"bottom.txt": "bottom\n"})
            self.commit("feature top", {"top.txt": "top\n"})
            self.bookmark("feature")
            self.jjrun("new", "main")
            self.commit("new trunk", {"trunk.txt": "trunk\n"})
            self.jjrun("bookmark", "set", "main", "-r", "@-")
            self.jjrun("new", "feature")
        elif c == "c15":
            self.commit("obsolete", {"legacy.txt": "legacy\n"})
            self.bookmark("obsolete")
            self.commit("keep", {"keep.txt": "keep\n"})
            self.bookmark("keep")
        elif c == "c16":
            self.jjrun("workspace", "rename", "main")
            self.jjrun("describe", "-m", "main task")
            self.jjrun(
                "workspace",
                "add",
                "--name",
                "sibling",
                "-r",
                "main",
                str(self.paths["sibling"]),
            )
            self.jjrun("describe", "-m", "sibling task", cwd="sibling")
        self.jjrun("status")

    def log(self, rev, template):
        return self.jjrun(
            "--ignore-working-copy", "log", "-r", rev, "--no-graph", "-T", template
        )

    def file(self, rev, path):
        r = self.run(["jj", "--ignore-working-copy", "file", "show", "-r", rev, "--", path])
        return r["stdout"] if r["returncode"] == 0 else None

    def fingerprint(self):
        trees = {}
        for alias, p in self.paths.items():
            if not p.exists():
                continue
            trees[alias] = {
                str(f.relative_to(p)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in p.rglob("*")
                if f.is_file() and ".jj" not in f.parts and ".git" not in f.parts
            }
        commits = self.log("all()", 'commit_id ++ "\\n"')
        return dict(files=trees, commits=commits)

    def grade(self, results):
        c = self.case
        checks = []
        out = "\n".join(r["stdout"] for r in results)

        def check(text, passed, evidence):
            checks.append(dict(text=text, passed=bool(passed), evidence=evidence))

        allowed = {0, 1} if c == "c08" else {0}
        check(
            "Every first-plan command completed without an unexpected error or timeout",
            bool(results) and all(r["returncode"] in allowed for r in results),
            [
                dict(argv=r["argv"], returncode=r["returncode"], stderr=r["stderr"][-400:])
                for r in results
            ],
        )
        if c == "c01":
            check(
                "Owned edit committed alone with requested description",
                self.file("@-", "app.txt") == "beta\n"
                and self.file("@-", "notes.txt") == "original\n"
                and self.log("@-", "description") == "app: fix output\n",
                self.log("@-", "description"),
            )
            check(
                "User draft remains in working copy",
                self.file("@", "notes.txt") == "user draft\n",
                self.file("@", "notes.txt"),
            )
        elif c == "c02":
            check(
                "Only own experiment discarded",
                self.file("@", "app.txt") == "alpha\n"
                and self.file("@", "notes.txt") == "user draft\n"
                and self.file("@-", "notes.txt") == "original\n",
                self.file("@", "notes.txt"),
            )
        elif c == "c03":
            ws = self.jjrun("--ignore-working-copy", "workspace", "list")
            preserved = self.run(
                [
                    "jj",
                    "--ignore-working-copy",
                    "log",
                    "-r",
                    'files("scratch-notes.txt")',
                    "--no-graph",
                    "-T",
                    'commit_id ++ "\\n"',
                ]
            )
            check(
                "Scratch registration retired and pending notes saved in history",
                not re.search(r"^scratch:", ws, re.M)
                and any(
                    self.file(r, "scratch-notes.txt") == "saved notes\n"
                    for r in preserved["stdout"].split()
                ),
                ws + preserved["stdout"],
            )
            check(
                "Active pending edits and main files preserved",
                self.paths["active"].joinpath("active-work.txt").read_text() == "in progress\n"
                and re.search(r"^active:", ws, re.M)
                and re.search(r"^default:", ws, re.M)
                and self.log("active@", "change_id") == self.active_change
                and self.fingerprint()["files"]["active"] == self.before["files"]["active"]
                and self.file("@", "app.txt") == "alpha\n",
                "active file and main app inspected",
            )
        elif c == "c04":
            desc = self.log("@-", "description")
            empty = self.log("@", 'empty ++ " " ++ description')
            check(
                "Squash describes changed parent and leaves undescribed empty child",
                desc == "feature: complete\n"
                and self.file("@-", "app.txt") == "gamma\n"
                and empty == "true ",
                dict(parent_description=desc, current=empty),
            )
        elif c == "c05":
            check(
                "Exact leading-dash message belongs to committed edit",
                self.log("@-", "description") == "--cleanup\n"
                and self.file("@-", "app.txt") == "beta\n"
                and self.log("@", "empty") == "true",
                self.log("@-", "description"),
            )
        elif c in ["c06", "c09", "c10"]:
            name = "docs/readme.txt" if c == "c10" else "app.txt"
            forbidden = (
                "parent-only.txt" if c == "c06" else "notes.txt" if c == "c09" else "other.txt"
            )
            check(
                "Requested Git patch includes only requested file/delta",
                (
                    f"diff --git a/{name} b/{name}" in out and "+beta" in out
                    if c != "c10"
                    else f"diff --git a/{name} b/{name}" in out and "+new docs" in out
                ),
                out[:1500],
            )
            check(
                "Unrequested patch absent", f"diff --git a/{forbidden}" not in out, out[:1500]
            )
        elif c == "c07":
            check(
                "File and insertion/deletion counts printed without patch",
                "app.txt" in out
                and "insertion" in out
                and "deletion" in out
                and "diff --git" not in out,
                out[:1200],
            )
        elif c == "c08":
            check(
                "Whitespace violation identified with path and line",
                "app.txt:2:" in out and "whitespace" in out,
                out[:1200],
            )
        elif c == "c11":
            expected = self.jjrun(
                "--ignore-working-copy",
                "evolog",
                "-r",
                "@",
                "--no-graph",
                "-T",
                'commit.commit_id() ++ "\\t" ++ commit.description().first_line() ++ "\\n"',
            ).splitlines()
            rows = [l for l in out.splitlines() if re.fullmatch(r"[0-9a-f]{4,40}\t[^\t]*", l)]
            check(
                "Historical commit versions and descriptions printed in requested rows",
                any(l.endswith("\tdraft one") for l in rows)
                and any(l.endswith("\tdraft two") for l in rows)
                and len(rows) == len(expected)
                and len(rows) == len([l for l in out.splitlines() if l.strip()])
                and all(
                    any(
                        e.split("\t")[0].startswith(r.split("\t")[0])
                        and e.split("\t", 1)[1] == r.split("\t", 1)[1]
                        for e in expected
                    )
                    for r in rows
                ),
                rows,
            )
        elif c == "c12":
            rows = [l for l in out.splitlines() if re.fullmatch(r"[0-9a-f]{4,128}\t[^\t]+", l)]
            expected = self.jjrun(
                "--ignore-working-copy",
                "op",
                "log",
                "-n",
                "2",
                "--no-graph",
                "-T",
                'id ++ "\\t" ++ description ++ "\\n"',
            ).splitlines()
            valid = len(rows) == 2 and len(rows) == len(
                [l for l in out.splitlines() if l.strip()]
            )
            valid = valid and all(
                e.split("\t")[0].startswith(r.split("\t")[0])
                and e.split("\t", 1)[1] == r.split("\t", 1)[1]
                for e, r in zip(expected, rows)
            )
            check(
                "Two operation-ID/description rows printed",
                valid,
                dict(expected=expected, actual=rows),
            )
        elif c == "c13":
            expected = self.jjrun(
                "--ignore-working-copy",
                "file",
                "annotate",
                "-T",
                'commit.change_id() ++ "\\t" ++ line_number ++ "\\t" ++ content',
                "app.txt",
            ).splitlines()
            rows = [l for l in out.splitlines() if re.fullmatch(r"[k-z]{4,32}\t\d+\t.*", l)]
            check(
                "Every annotated line includes change ID, number and content",
                len(rows) == 2
                and len(rows) == len([l for l in out.splitlines() if l.strip()])
                and rows[0].endswith("\t1\talpha")
                and rows[1].endswith("\t2\tbeta")
                and all(
                    e.split("\t")[0].startswith(r.split("\t")[0])
                    and e.split("\t", 1)[1] == r.split("\t", 1)[1]
                    for e, r in zip(expected, rows)
                ),
                dict(expected=expected, actual=rows),
            )
        elif c == "c14":
            matches = self.log(
                'main:: & ancestors(feature) & description(substring:"feature")',
                'description.first_line() ++ "\\n"',
            )
            check(
                "Both feature changes rebased onto main with their contents preserved",
                "feature bottom" in matches
                and "feature top" in matches
                and self.file("feature", "bottom.txt") == "bottom\n"
                and self.file("feature", "top.txt") == "top\n"
                and self.file("feature", "trunk.txt") == "trunk\n"
                and self.log("@", "empty") == "true"
                and self.log("@-", "change_id") == self.log("feature", "change_id"),
                matches,
            )
        elif c == "c15":
            obsolete = self.log('ancestors(keep) & description(exact:"obsolete")', "commit_id")
            check(
                "Obsolete ancestor gone; surviving exact tree and description retained",
                not obsolete
                and self.file("keep", "legacy.txt") == "legacy\n"
                and self.file("keep", "keep.txt") == "keep\n"
                and self.log("keep", "description") == "keep\n"
                and self.log("@", "empty") == "true"
                and self.log("@-", "change_id") == self.log("keep", "change_id"),
                dict(obsolete_ancestor=obsolete, legacy=self.file("keep", "legacy.txt")),
            )
        elif c == "c16":
            rows = [
                l
                for l in out.splitlines()
                if re.fullmatch(r"(?:main|sibling)\t[k-z]{4,32}\t[^\t]+", l)
            ]
            check(
                "Workspace names, change IDs and descriptions printed",
                len(rows) == 2
                and len(rows) == len([l for l in out.splitlines() if l.strip()])
                and any(l.startswith("main\t") and l.endswith("\tmain task") for l in rows)
                and any(
                    l.startswith("sibling\t") and l.endswith("\tsibling task") for l in rows
                )
                and all(
                    self.log(row.split("\t")[0] + "@", "change_id").startswith(
                        row.split("\t")[1]
                    )
                    for row in rows
                ),
                rows,
            )
        if c in ["c06", "c07", "c08", "c09", "c10", "c11", "c12", "c13", "c16"]:
            after = self.fingerprint()
            check(
                "Read-only task preserved files and commit history",
                after == self.before,
                "before/after tree hashes and commit IDs",
            )
        passed = all(q["passed"] for q in checks)
        return dict(case_id=c, passed=passed, expectations=checks)


GOLDEN = {
    "c01": [["jj", "commit", "app.txt", "-m", "app: fix output"]],
    "c02": [["jj", "restore", "app.txt"]],
    "c03": [["jj", "-R", "../scratch", "status"], ["jj", "workspace", "forget", "scratch"]],
    "c04": [["jj", "squash", "--into", "@-", "-m", "feature: complete"]],
    "c05": [["jj", "commit", "-m=--cleanup"]],
    "c06": [["jj", "diff", "--git", "--from", "@-", "--to", "@"]],
    "c07": [["jj", "diff", "--stat"]],
    "c08": [["python3", "check_whitespace.py"]],
    "c09": [["jj", "diff", "-r", "review", "--git", "app.txt"]],
    "c10": [["jj", "-R", "../sibling", "diff", "--git", 'root:"docs/readme.txt"']],
    "c11": [
        [
            "jj",
            "evolog",
            "--no-graph",
            "-T",
            'commit.commit_id().short() ++ "\\t" ++ commit.description().first_line() ++ "\\n"',
        ]
    ],
    "c12": [
        [
            "jj",
            "op",
            "log",
            "-n",
            "2",
            "--no-graph",
            "-T",
            'id.short() ++ "\\t" ++ description ++ "\\n"',
        ]
    ],
    "c13": [
        [
            "jj",
            "file",
            "annotate",
            "-T",
            'commit.change_id().short() ++ "\\t" ++ line_number ++ "\\t" ++ content',
            "app.txt",
        ]
    ],
    "c14": [["jj", "rebase", "-b", "@", "-d", "main"]],
    "c15": [["jj", "abandon", "--restore-descendants", "obsolete"]],
    "c16": [
        [
            "jj",
            "workspace",
            "list",
            "-T",
            'name ++ "\\t" ++ target.change_id().short() ++ "\\t" ++ '
            'target.description().first_line() ++ "\\n"',
        ]
    ],
}


def execute_case(case_id, commands, jj, work):
    fixture = Fixture(case_id, jj, work)
    results = []
    for cmd in commands:
        if (
            not isinstance(cmd, dict)
            or not isinstance(cmd.get("argv"), list)
            or not cmd["argv"]
        ):
            return dict(case_id=case_id, passed=False, invalid_plan="Malformed command")
        argv = cmd["argv"]
        alias = cmd.get("cwd", "main")
        if (
            not all(isinstance(a, str) for a in argv)
            or alias not in fixture.paths
            or not fixture.paths[alias].exists()
        ):
            return dict(case_id=case_id, passed=False, invalid_plan="Invalid argv or cwd alias")
        checker = case_id == "c08" and argv in [
            ["python3", "check_whitespace.py"],
            ["python3", "check_whitespace.py", "app.txt"],
        ]
        own_cleanup = (
            case_id == "c03"
            and alias == "main"
            and argv == ["python3", "-c", "import shutil; shutil.rmtree('../scratch')"]
        )
        if argv[0] != "jj" and not (checker or own_cleanup):
            return dict(
                case_id=case_id,
                passed=False,
                invalid_plan="Executable outside permitted jj/project checker interface",
            )
        r = fixture.run(argv, alias, cmd.get("stdin"))
        results.append(r)
        if r["returncode"] != 0 and not (case_id == "c08" and r["returncode"] == 1):
            break
    grade = fixture.grade(results)
    grade["commands"] = results
    return grade


def canary(jj, output):
    version = subprocess.check_output([jj, "--version"], text=True).strip()
    if not version.startswith("jj 0.45.1"):
        raise RuntimeError("Expected jj 0.45.1, got " + version)
    grades = []
    for c, cs in GOLDEN.items():
        with tempfile.TemporaryDirectory(prefix="jj-fixture-canary-") as root:
            grade = execute_case(c, [dict(cwd="main", argv=v) for v in cs], jj, root)
            grades.append(grade)
            print(c, "PASS" if grade["passed"] else "FAIL", flush=True)
    Path(output).write_text(json.dumps(dict(jj_version=version, grades=grades), indent=2))
    return all(g["passed"] for g in grades)


def freeze():
    files = ["cases.json", "runner.py", "canary_negative.py"] + [
        str(p.relative_to(HERE))
        for p in sorted((HERE / "adapters").glob("*.py"))
    ]
    manifest = {p: hashlib.sha256((HERE / p).read_bytes()).hexdigest() for p in files}
    (HERE / "frozen.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def parse_plans(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    value = json.loads(raw)
    cases = value.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Missing cases list")
    ids = [c.get("id") for c in cases if isinstance(c, dict)]
    expected = {c["id"] for c in json.loads((HERE / "cases.json").read_text())}
    if len(ids) != len(expected) or set(ids) != expected:
        raise ValueError("Case IDs missing, duplicated or unknown")
    return {c["id"]: c["commands"] for c in cases}


def evaluate(adapter_file, skill, condition, repeat, jj, output):
    provenance = jj_provenance(jj)
    manifest = json.loads((HERE / "frozen.json").read_text())
    for name, digest in manifest.items():
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Frozen evaluator changed: " + name)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("engine_adapter", adapter_file)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    system, user = prompts(skill)
    (output / "adapter-sha256.txt").write_text(
        hashlib.sha256(Path(adapter_file).read_bytes()).hexdigest() + "\n"
    )
    (output / "prompt-hashes.json").write_text(
        json.dumps(
            dict(
                system=hashlib.sha256(system.encode()).hexdigest(),
                user=hashlib.sha256(user.encode()).hexdigest(),
            ),
            indent=2,
        )
    )
    response = adapter.generate(system, user, output / "engine")
    (output / "engine-response.json").write_text(json.dumps(response, indent=2))
    result = dict(
        jj=provenance,
        condition=condition,
        repeat=repeat,
        engine=response.get("engine"),
        model=response.get("model"),
        elapsed_seconds=response.get("elapsed_seconds"),
        usage=response.get("usage"),
        case_results=[],
    )
    try:
        if response.get("engine_error"):
            raise ValueError(response["engine_error"])
        plans = parse_plans(response["raw_text"])
    except (ValueError, KeyError, TypeError) as exc:
        result["invalid_engine_output"] = str(exc)
    else:
        for case_id, commands in plans.items():
            with tempfile.TemporaryDirectory(prefix="jj-first-plan-") as root:
                try:
                    grade = execute_case(case_id, commands, jj, root)
                except Exception as exc:
                    grade = dict(case_id=case_id, passed=False, harness_error=str(exc))
                result["case_results"].append(grade)
        result["passed"] = sum(c["passed"] for c in result["case_results"])
        result["total"] = len(result["case_results"])
    (output / "results.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps({k: v for k, v in result.items() if k != "case_results"}, indent=2),
        flush=True,
    )
    return result


def replay(plans_file, jj, output):
    """Execute saved first plans against fresh fixtures without another model call."""
    provenance = jj_provenance(jj)
    plans = parse_plans(Path(plans_file).read_text())
    grades = []
    for case_id, commands in plans.items():
        with tempfile.TemporaryDirectory(prefix="jj-replay-") as root:
            grade = execute_case(case_id, commands, jj, root)
            grades.append(grade)
    result = dict(
        jj=provenance,
        judge_version=3,
        passed=sum(g["passed"] for g in grades),
        total=len(grades),
        case_results=grades,
    )
    Path(output).write_text(json.dumps(result, indent=2))
    print(f"{result['passed']}/{result['total']}")
    return result


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    c = sub.add_parser("canary")
    c.add_argument("--jj", default=DEFAULT_JJ)
    c.add_argument("--output", default=str(HERE / "canary.json"))
    sub.add_parser("freeze")
    e = sub.add_parser("evaluate")
    e.add_argument("--adapter", required=True)
    e.add_argument("--skill", required=True)
    e.add_argument("--condition", required=True)
    e.add_argument("--repeat", type=int, required=True)
    e.add_argument("--jj", default=DEFAULT_JJ)
    e.add_argument("--output", required=True)
    r = sub.add_parser("replay")
    r.add_argument("--plans", required=True)
    r.add_argument("--jj", default=DEFAULT_JJ)
    r.add_argument("--output", required=True)
    args = p.parse_args()
    if args.action == "canary":
        sys.exit(0 if canary(args.jj, args.output) else 1)
    if args.action == "freeze":
        print(json.dumps(freeze(), indent=2))
    if args.action == "replay":
        replay(args.plans, args.jj, args.output)
    if args.action == "evaluate":
        evaluate(args.adapter, args.skill, args.condition, args.repeat, args.jj, args.output)


if __name__ == "__main__":
    main()
