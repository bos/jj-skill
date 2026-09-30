#!/usr/bin/env python3
"""Check mutable workspace bases and native macOS trash with disposable data."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid


class Repo:
    def __init__(self, root, jj):
        self.root, self.jj = Path(root), jj
        self.main = self.root / "main"
        self.main.mkdir()
        config = self.root / "config.toml"
        config.write_text(
            '[user]\nname="Evaluation"\nemail="eval@example.invalid"\n'
            '[ui]\neditor="false"\npager="cat"\n'
            '[revset-aliases]\n"immutable_heads()"="present(base) | root()"\n'
        )
        self.env = dict(os.environ)
        for name in list(self.env):
            if any(part in name.upper() for part in ("TOKEN", "API_KEY", "AUTH")):
                self.env.pop(name)
        self.env.update(
            HOME=str(self.root / "isolated-user"),
            XDG_CONFIG_HOME=str(self.root / "isolated-user/config"),
            JJ_CONFIG=str(config),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL="/dev/null",
        )
        self.commands = []
        self.run("git", "init", ".")
        (self.main / "app.txt").write_text("task: base\n")
        (self.main / "dependency.txt").write_text("dependency: base\n")
        (self.main / ".gitignore").write_text("ignored-cache/\n")
        self.run("commit", "-m", "base")
        self.run("bookmark", "set", "base", "-r", "@-")

    def run(self, *args, cwd=None, check=True):
        cwd = cwd or self.main
        result = subprocess.run(
            [self.jj, *args], cwd=cwd, env=self.env, capture_output=True, text=True, timeout=20
        )
        self.commands.append(
            dict(
                cwd=str(cwd.relative_to(self.root)),
                argv=["jj", *args],
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        )
        if check and result.returncode:
            raise RuntimeError(json.dumps(self.commands[-1]))
        return result


def mutable_base(root, jj):
    repo = Repo(root, jj)
    (repo.main / "dependency.txt").write_text("dependency: unpublished\n")
    repo.run("commit", "-m", "unpublished dependency")
    repo.run("bookmark", "set", "taskbase", "-r", "@-")
    immutable = repo.run("log", "-r", "taskbase & immutable()", "--no-graph", "-T", "commit_id")
    assert not immutable.stdout
    own = repo.root / "task with spaces"
    repo.run("workspace", "add", "--name", "task", "-r", "taskbase", str(own))
    assert (own / "dependency.txt").read_text() == "dependency: unpublished\n"
    (own / "app.txt").write_text("task: done\n")
    repo.run("status", cwd=own)
    (repo.main / "dependency.txt").write_text("dependency: revised\n")
    repo.run("squash", "--into", "taskbase", "--use-destination-message", "dependency.txt")
    stale = repo.run("status", cwd=own, check=False)
    assert stale.returncode and "stale" in stale.stderr
    repo.run("workspace", "update-stale", cwd=own)
    repo.run("status", cwd=own)
    repo.run("log", "-r", "@ | taskbase", "--no-graph", cwd=own)
    assert (own / "dependency.txt").read_text() == "dependency: revised\n"
    assert (own / "app.txt").read_text() == "task: done\n"
    repo.run("commit", "-m", "task on mutable dependency", "app.txt", cwd=own)
    assert repo.run("file", "show", "-r", "@-", "app.txt", cwd=own).stdout == "task: done\n"
    committed_dependency = repo.run("file", "show", "-r", "@-", "dependency.txt", cwd=own)
    assert committed_dependency.stdout == "dependency: revised\n"
    invalid = repo.run(
        "--ignore-working-copy", "workspace", "add", "--name", "invalid",
        "-r", "taskbase", str(repo.root / "invalid"), check=False,
    )
    assert invalid.returncode == 1 and "must be able to update the working copy" in invalid.stderr
    return dict(
        assertions=dict(
            unpublished_mutable_base_accepted=True,
            dependency_in_new_workspace=True,
            external_base_rewrite_causes_stale_warning=True,
            update_stale_preserves_snapshotted_task_edit=True,
            final_task_commit_contains_revised_dependency=True,
            ignore_working_copy_rejected_by_workspace_add=True,
        ),
        commands=repo.commands,
        limitation="Task edit snapshotted before the external rewrite; no universal race claim.",
    )


def manifest(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def native_trash(root, jj):
    if sys.platform != "darwin" or not Path("/usr/bin/trash").exists():
        return dict(skipped="Native smoke requires macOS with /usr/bin/trash.")
    repo = Repo(root, jj)
    own = repo.root / ("jj owned workspace " + uuid.uuid4().hex)
    destination = Path.home() / ".Trash" / own.name
    assert not destination.exists()
    repo.run("workspace", "add", "--name", "finished", "-r", "base", str(own))
    notes = "retained tracked notes\n"
    (own / "notes.txt").write_text(notes)
    (own / ".hidden-note").write_text("hidden content\n")
    (own / "ignored-cache").mkdir()
    (own / "ignored-cache/cache.bin").write_bytes(b"ignored payload\x00\xff")
    repo.run("status", cwd=own)
    note_revision = repo.run("log", "-r", "@", "--no-graph", "-T", "commit_id", cwd=own).stdout
    repo.run("--ignore-working-copy", "workspace", "forget", "finished")
    before = manifest(own)
    try:
        result = subprocess.run(
            ["/usr/bin/trash", "--stopOnError", str(own)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert not own.exists() and destination.is_dir()
        assert manifest(destination) == before
        assert repo.run("file", "show", "-r", note_revision, "notes.txt").stdout == notes
        shutil.move(str(destination), str(own))
        assert manifest(own) == before and not destination.exists()
        missing = subprocess.run(
            ["/usr/bin/trash", "--stopOnError", str(repo.root / "absent")],
            capture_output=True, text=True, timeout=30,
        )
        assert missing.returncode != 0
        return dict(
            assertions=dict(
                whole_workspace_moved_to_native_trash=True,
                metadata_hidden_and_ignored_bytes_preserved=True,
                tracked_notes_also_retained_in_jj=True,
                restoration_preserves_all_bytes=True,
                missing_target_reports_failure=True,
            ),
            missing_target_exit=missing.returncode,
            commands=repo.commands,
        )
    finally:
        if destination.exists() and not own.exists():
            shutil.move(str(destination), str(own))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jj", default=shutil.which("jj"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    jj = str(Path(args.jj).resolve())
    version = subprocess.check_output([jj, "--version"], text=True).strip()
    if version != "jj 0.45.1":
        raise SystemExit("Expected exact jj 0.45.1, got " + version)
    results = dict(
        jj_version=version, jj_binary=jj,
        jj_sha256=hashlib.sha256(Path(jj).read_bytes()).hexdigest(),
    )
    for name, check in [("mutable_base", mutable_base), ("native_trash", native_trash)]:
        with tempfile.TemporaryDirectory(prefix="jj-ownership-smoke-") as root:
            results[name] = check(root, jj)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(
        {name: value.get("assertions", value) for name, value in results.items()
         if isinstance(value, dict)}, indent=2,
    ))


if __name__ == "__main__":
    main()
