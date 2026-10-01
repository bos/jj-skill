# Focused ownership evaluation

These three fixtures extend the original battery with a separate, continuing writer process:

- Disjoint files: commit the task file while user notes and another file's edits stay pending.
  A shared checkout with a scoped commit is a valid solution.
- Overlapping file edits: commit only the task's line while another process changes a different
  line of that file. The required base is an unpublished mutable dependency, not `main`.
- Cleanup: retire only the session-created finished workspace, snapshot its tracked notes, and
  retain the whole directory through recoverable trash, including ignored cache data and `.jj`.
  Another workspace's writer must successfully continue afterward.

Pipe acknowledgments order a real subprocess write after setup and another write after the
tested commands. There are no timing sleeps. This tests those particular interleavings, not all
possible concurrency. The writer changes physical files only; it does not run simultaneous jj
history operations. These are command plans, not complete interactive agent sessions.

Safety and completion are separate outcomes. A deferral or preserved parked directory can be
safe without completing the task. Commands that fail while leaving other work intact likewise
do not count as first-try success. The cleanup transport in the model fixtures is a deterministic
shim with native macOS argument syntax and recoverability receipts. Native OS behavior is checked
separately by `smoke.py`; Linux and Windows are not runtime-tested here.

## Run without model calls

Use exact jj 0.45.1. The tests isolate jj configuration and create disposable repositories.
The replay example assumes the named plan has been generated locally; results are ignored.

```bash
python3 evals/ownership/canaries.py --jj /opt/homebrew/bin/jj --output /tmp/jj-owned-canaries
python3 evals/ownership/smoke.py --jj /opt/homebrew/bin/jj --output /tmp/jj-owned-smoke.json
python3 evals/ownership/replay.py --jj /opt/homebrew/bin/jj \
  --plans evals/results/2026-09-30-ownership/plans/codex-corrected.json \
  --output /tmp/jj-owned-replay.json
```

`smoke.py` verifies an unpublished mutable base, its external rewrite, the resulting stale
workspace, and recovery of a previously snapshotted task edit. It also checks the rejected
`--ignore-working-copy workspace add` combination. On macOS with native `/usr/bin/trash`, it
trashes and restores one self-created workspace and verifies every file's bytes, including hidden
and ignored files. It never empties Trash or moves any existing user directory.

## Generate fresh plans

The cases, contract, judge, and canaries were frozen before inference; `freeze.json` records
their hashes. The six-file freeze also preserves the original orchestration and GLM adapter.
`run_pairs.py` is the recorded driver using the original adapter filenames; use direct runner
calls with repository adapters for new experiments:

```bash
python3 evals/ownership/focused_runner.py run \
  --engine codex --condition new --skill skills/jj --adapter evals/adapters/codex.py \
  --jj /opt/homebrew/bin/jj --output /tmp/jj-owned-codex-new
```

Substitute Claude's adapter, or the frozen macOS `glm_adapter_300.py`. The latter uses ZCode's
installed GLM-5.3 engine with no tools, maximum reasoning, and a 300-second client watchdog.
Authentication stays in process memory. The driver defaults to macOS executable locations.
Run the same tasks with both skill versions and preserve failed attempts; do not retry a model
with execution feedback. Store generated plans, comparisons, and provenance under the ignored
`evals/results/` directory.
