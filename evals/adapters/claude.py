"""One tool-free, isolated Claude Code inference per generate() call."""

import argparse
import json
import pathlib
import subprocess
import time


def generate(system_prompt: str, user_prompt: str, output_dir: pathlib.Path) -> dict:
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cwd = output_dir / "empty-cwd"
    cwd.mkdir(exist_ok=True)
    args = [
        "claude",
        "-p",
        "--safe-mode",
        "--tools",
        "",
        "--disable-slash-commands",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--no-session-persistence",
        "--output-format",
        "stream-json",
        "--verbose",
        "--system-prompt",
        system_prompt,
    ]
    # Existing normal OAuth/keychain auth stays available. --safe-mode disables
    # custom context/hooks/plugins. Never use --bare, which disables OAuth.
    start = time.monotonic()
    try:
        process = subprocess.run(
            args,
            input=user_prompt,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "raw_text": "",
            "engine": "Claude Code",
            "adapter_compatibility_version": "2.1.285",
            "model": "",
            "elapsed_seconds": time.monotonic() - start,
            "engine_error": "Inference exceeded 600 seconds; no retry performed.",
        }
    (output_dir / "stream.jsonl").write_text(process.stdout)
    (output_dir / "stderr.txt").write_text(process.stderr)
    result = {
        "raw_text": "",
        "engine": "Claude Code",
        "adapter_compatibility_version": "2.1.285",
        "model": "",
        "elapsed_seconds": time.monotonic() - start,
        "exit_code": process.returncode,
    }
    texts = []
    for line in process.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            result["isolation"] = {
                key: event.get(key)
                for key in (
                    "tools",
                    "mcp_servers",
                    "skills",
                    "plugins",
                    "agents",
                    "slash_commands",
                )
            }
            result["model"] = event.get("model", "")
        elif event.get("type") == "assistant":
            message = event.get("message", {})
            result["model"] = message.get("model") or result["model"]
            for block in message.get("content", []):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    result["engine_error"] = "Unexpected tool use in tool-free inference."
        elif event.get("type") == "result":
            result["raw_text"] = event.get("result") or "\n".join(texts)
            result["usage"] = event.get("usage")
            result["model_usage"] = event.get("modelUsage")
            result["num_turns"] = event.get("num_turns")
            result["stop_reason"] = event.get("stop_reason")
            if event.get("is_error"):
                result["engine_error"] = event.get("subtype", "Claude inference error")
    if not result["raw_text"]:
        result["raw_text"] = "\n".join(texts)
    if process.returncode and "engine_error" not in result:
        result["engine_error"] = (
            f"Claude exited with status {process.returncode}; no retry performed."
        )
    (output_dir / "generation.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-file", type=pathlib.Path, required=True)
    parser.add_argument("--prompt-file", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = generate(
        args.system_file.read_text(), args.prompt_file.read_text(), args.output.parent
    )
    args.output.write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                key: result.get(key)
                for key in ("engine", "model", "elapsed_seconds", "exit_code", "engine_error")
            }
        )
    )
