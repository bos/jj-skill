"""Codex CLI adapter preserving auth, with user/project skill injection disabled."""

import json
from pathlib import Path
import subprocess
import tempfile
import time


def generate(system_prompt, user_prompt, output_dir):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    final = output_dir / "final.json"
    cmd = [
        "codex",
        "--no-daemon",
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--disable",
        "shell_tool",
        "--disable",
        "unified_exec",
        "--disable",
        "code_mode",
        "--disable",
        "code_mode_only",
        "--disable",
        "apply_patch_freeform",
        "--disable",
        "multi_agent_v2",
        "--disable",
        "plugins",
        "--disable",
        "memories",
        "-c",
        "skills.include_instructions=false",
        "-c",
        "skills.bundled.enabled=false",
        "-c",
        "project_doc_max_bytes=0",
        "-c",
        'web_search="disabled"',
        "-c",
        "memories.use_memories=false",
        "-c",
        "memories.generate_memories=false",
        "--color",
        "never",
        "--output-last-message",
        str(final),
        "-",
    ]
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="jj-codex-planner-") as cwd:
        r = subprocess.run(
            cmd,
            input=system_prompt + "\n\n<tasks>\n" + user_prompt + "\n</tasks>",
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=240,
        )
    (output_dir / "events.jsonl").write_text(r.stdout)
    (output_dir / "stderr.txt").write_text(r.stderr)
    events = []
    for line in r.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    usage = [e.get("usage") for e in events if e.get("usage")]
    tool_events = [
        e
        for e in events
        if e.get("item", {}).get("type") not in [None, "reasoning", "agent_message", "error"]
    ]
    if "\nexec\n" in r.stderr:
        tool_events.append({"type": "unexpected_exec"})
    model = None
    for line in r.stderr.splitlines():
        if line.startswith("model:"):
            model = line.partition(":")[2].strip()
    result = dict(
        raw_text=final.read_text() if final.exists() else "",
        engine="codex",
        model=model,
        elapsed_seconds=time.monotonic() - started,
        usage=usage,
        exit_code=r.returncode,
        isolation=dict(
            ignore_user_config=True,
            ephemeral=True,
            project_doc_max_bytes=0,
            skills_instructions=False,
            bundled_skills=False,
            plugins=False,
            model_tool_events=tool_events,
        ),
    )
    if r.returncode != 0:
        result["engine_error"] = "Codex CLI failed: " + r.stderr[-2000:]
    elif tool_events:
        result["engine_error"] = "Unexpected model tool execution in command-choice evaluation"
    return result


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--system-file", required=True)
    p.add_argument("--prompt-file", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    out = Path(a.output)
    r = generate(
        Path(a.system_file).read_text(), Path(a.prompt_file).read_text(), out.parent / "engine"
    )
    out.write_text(json.dumps(r, indent=2))
