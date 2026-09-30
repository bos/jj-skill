# First-plan jj evaluation

This battery checks sixteen mistakes drawn from observed agent use. Each engine receives the
complete skill and references, then returns commands without execution feedback or retries.
The runner executes each plan once in a fresh repository and checks its resulting history,
files, descriptions, workspace registrations, or printed output.

This measures command selection with the skill already supplied. It does not measure skill
discovery, success across entire coding tasks, or future production success rates. Two repeats
of sixteen selected scenarios give a small, correlated sample, rather than independent trials.

See [the recorded comparison](results/2026-09-30/README.md) for models, source revisions,
results, and evaluation corrections. Saved plans can be replayed without another model call.

The original c01/c02 fixtures contain static pre-existing edits, not a continuing writer.
Original c03 checks workspace ownership and tracked notes in history; it does not check ignored
files or recoverable trash. Its frozen replay allowance for removing the task's own directory
belongs to that historical battery. Use the [focused ownership checks](ownership/README.md) for
live writers, mutable dependencies, and the current recoverable-cleanup policy.

## Verify the fixtures

Use jj 0.45.1. `JJ_EVAL_JJ` can name an installed binary when the default `jj` is a version
manager shim. All Python files use the standard library.

```bash
python3 evals/runner.py canary --output /tmp/jj-canary.json
python3 evals/canary_negative.py --jj jj --output /tmp/jj-negative-canary.json
```

The positive canaries demonstrate successful plans. The negative canaries reproduce historical
mistakes and must all be rejected, including commands that exit successfully with wrong results.
Execution uses temporary repositories and isolated jj configuration. The executable restrictions
are targeted to this battery; they do not provide an operating-system sandbox for arbitrary
untrusted plans.

## Replay a recorded plan

```bash
python3 evals/runner.py replay \
  --plans evals/results/2026-09-30/plans/codex-final-1.json \
  --output /tmp/jj-replay.json
```

Commit IDs vary between fixtures; the grader checks identities and relationships within each
fixture. The replay report records the jj version and binary hash.

## Generate new plans

The adapters use existing authentication and disable tools, project instructions, skill
auto-loading, and session history. Codex and Claude use their installed command-line clients.
GLM uses ZCode's bundled `workspace/generateText` interface with GLM-5.3 and maximum reasoning,
matching the model used in the GUI. It supplies exactly the evaluation messages and an empty
tools list. This checks the GLM engine through ZCode, rather than automating the GUI.

The GLM adapter defaults to the macOS ZCode installation. `JJ_EVAL_ZCODE_BUNDLE` and
`JJ_EVAL_NODE` override its executable locations. Its transport setup uses an operation ID and
a 64,000-token output budget so maximum reasoning can finish without the default 60-second
cancellation.

```bash
python3 evals/runner.py freeze
python3 evals/runner.py evaluate \
  --adapter evals/adapters/codex.py --skill skills/jj \
  --condition with_skill --repeat 1 --output evals/runs/codex/new-1
```

Substitute `claude.py` or `glm.py` for the adapter. Run both skill versions with the same engine
settings and tasks. Keep baseline and revised skill directories separate, and counterbalance
the order across repeats. Freeze the evaluator before generating plans. The report stores
prompt hashes and the adapter hash; record model IDs and source revisions alongside results.

Generated engine logs remain under the ignored `runs/` directory. The checked-in comparison
contains synthetic plans and summarized grades, without provider configuration, authentication,
session databases, or personal conversation logs.
