---
name: jj
license: Apache-2.0
description: >
  Use jj safely and translate Git workflows into Jujutsu commands. Use for source-control
  tasks in jj repositories, including commits, history edits, bookmarks, workspaces,
  and remote synchronization.
---

# jj (Jujutsu) workflow skill

Use this skill for source-control operations in Jujutsu repositories. The `jj` command-line
tool must be installed.

## Repository detection

Reuse a repository type already confirmed by project instructions or the current session.
Otherwise, before the first source-control operation, run once from the working directory:

```bash
jj --ignore-working-copy root 2>/dev/null
```

On success, remember the returned repository root as `jj` for the session and use this skill
for that root and its subdirectories. Do not repeat the probe for a confirmed repository.
On failure, this skill does not apply; use the project's normal source-control tooling.
Repository initialization explicitly requested by the user is a separate operation.

It guides you through concepts, commits, diffs, log exploration, bookmark management, and remote
pushes using `jj` idioms—never git fallbacks.

## Activation cues

- The repository has been confirmed as Jujutsu by project instructions or `jj root`.
- Need to run `status`, `commit`, `rebase`, `bookmark`, or `push` flows while staying inside jj.
- Preparing to script multi-command workflows that manipulate history or remotes.

Announce that you are loading the jj skill, then follow the checklists and command recipes
described below.

## Core capabilities

- Provide first-try command patterns for committing, squashing, and describing changes.
- Map status, diff, and fileset selection tasks to `jj` syntax and constraints.
- Explain template usage for logs and other formatted outputs.
- Offer bookmark, revset, and remote push recipes that avoid git-only flags.
- Highlight workspace recovery steps and file inspection commands.
- Explain when isolated parallel work should use a separate `jj` workspace instead of sharing
  the current working copy.
- Explain when `jj run` can apply a command across selected revisions using private working
  copies.

## Reference shortcuts

If you can't find what you need in this file or one of the files it references, run one or more
of the following commands:

- `jj help -k bookmarks` — bookmark concepts and conflict handling
- `jj help -k config` — configuration layout, aliases, defaults
- `jj help -k filesets` — valid file selectors and operators
- `jj help -k glossary` — terminology (visible commits, change IDs, etc.)
- `jj help -k revsets` — revset operators, functions, and examples
- `jj help -k templates` — full template language reference
- `jj help -k tutorial` — guided walkthrough for new jj users
- `jj help converge` — reconcile divergent revisions of the same change
- `jj help run` — run a command across selected revisions with private working copies
- `jj help workspace` — workspace subcommands and defaults

## Core concepts (git → jj)

- **Working copy is a commit; no staging area.** You operate on the current change (`@`). Every
  `jj` command snapshots the working tree into `@`, so edits become tracked immediately. Create a
  fresh child with `jj new` (with optional `-m`), record it with `jj commit -m`, and update the
  message via `jj describe -m`.
- **Change IDs vs commit IDs.** Each logical change has a stable `change_id()` that survives
  rewriting. Concrete commits have `commit_id()` values that change when rewritten. Prefer
  `change_id` for references you plan to reuse.
- **Operation log enables recovery.** Every command records an operation. Inspect with `jj op
  log`; avoid repo-wide undo or restore while other workspaces may be active.
- **Bookmarks map to Git branches.** Bookmarks are local pointers. Pushing maps them to Git
  branches (`jj git push --bookmark main`). There is no "checked-out branch"; the working copy is
  independent.
- **Conflicts are first-class.** Conflicts live inside commits and propagate until resolved. You
  create merges by making a change with multiple parents (`jj new`), resolving, then committing.
- **Workspaces isolate filesystems, not history.** Before rewriting history shared with another
  workspace, follow [parallel-workspaces.md](references/parallel-workspaces.md).

### Mental model mappings

- Git "branch" → jj bookmark (local pointer mapped to a Git branch on push).
- Git "index/staging" → no equivalent; pass filesets to commands that support them.
- Git "HEAD" → jj working copy `@`; parent is `@-`.
- Git "reflog" → jj operation log (`jj op log`, `jj undo`, `jj redo`).
- Git "rebase -i" → jj squash/split/rebase commands with automatic descendant handling.

## Minimal workflow checklist

1. Run `jj status` or `jj diff -s`; record existing edits and which changes belong to this task.
2. Create or focus the change you want (`jj new` for an empty child if needed).
3. Make edits, then record with `jj commit -m "message"`; if you need to fold new edits into the
   parent, run `jj squash --into @- -m "message"`.
4. Review history with `jj log`.
5. Synchronize bookmarks with `jj git push --remote origin --bookmark <name>`.
6. If you rewrite history, review `jj op log`.
7. When syntax is unclear, read the relevant help panel (`jj help -k …`) before guessing.

Mark each step as done before moving on.

## Do not

- Do not invoke Git commands inside jj-enabled repos; stick to jj equivalents.
- Do not skip announcing this skill when `.jj` is present.
- Do not rely on staged changes or `git add`; pass files or filesets directly to jj commands.
- Do not push blindly—name the bookmark.
- Do not use Git worktrees for isolated parallel work in jj repos. Use jj workspaces instead.

## Git muscle memory → jj translation

- `git status` → `jj status` or `jj diff -s`
- `git commit -am` → `jj commit -m "message"` (pass filesets positionally)
- `git commit --amend` → `jj squash --into @- -m "message"`
- `git restore <path>` → `jj restore '<fileset>'`
- `git reset --hard` → `jj restore` (discards all working copy changes)
- `git revert <commit>` → `jj revert -r '<revset>' -d @`
  (creates a new change that undoes the target without rewriting history)
- `git log --oneline` →
  `jj log -T 'change_id.short() ++ " " ++ commit_id.short() ++ " " ++ description.first_line()'`
- `git bisect run <command>` → `jj bisect run --range '<good>..<bad>' -- <command>`
- `git branch` → `jj bookmark list`
- `git switch -c feature` → `jj new main` (pass the parent revsets directly after the command)
- `git rebase origin/main` → `jj rebase -s @ -d main@origin`
- `git push origin main` → `jj git push --remote origin --bookmark main`

## Common command patterns

### Commit and describe

- Review the full diff before committing, squashing, or restoring. A file appearing in the diff
  does not establish ownership. Preserve edits from the user or other agents.
- In a shared or already dirty working copy, pass owned filesets to `jj commit` or `jj squash`.
  If ownership overlaps within a file, use interactive selection or isolate the work; selecting
  the whole file also selects the other person's edits.
- Snapshot the working copy as a new change (no editor):
  `jj commit -m "Message"`
- After `jj commit`, if you need to report what you created to the user, query the parent with a
  change-first template such as
  `jj log -r @- -T 'change_id.short() ++ " " ++ description.first_line() ++ "\n"'`.
  If the exact immutable snapshot matters, include `commit_id` second and label it explicitly.
- Fold the working copy back into its parent (git amend equivalent):
  `jj squash --into @- -m "Updated message"`.
- Keep the parent's description while folding in edits:
  `jj squash --into @- --use-destination-message`.
  Plain squash can open an editor when both descriptions are nonempty. Choose the message policy
  explicitly for unattended commands. A full squash usually abandons the source and creates an
  empty `@`; to describe the amended parent afterward, use `jj describe -r @- -m "Updated message"`.
- Update only the description without creating a new change:
  `jj describe -m "Better message"`
- If a message begins with `--`, pass `--` before it:
  `jj commit -m -- "--looks like a flag"`

### status, diff, filesets

- Short status-like summary:
  `jj diff -s` (optionally scope with a fileset, e.g., `jj diff -s 'root:"src/"'`)
- Show the working-copy change: `jj diff` (equivalent to `jj diff -r @`).
- Compare two trees: `jj diff --from @- --to @`.
  Repeated `-r` values combine change patches; they do not name comparison endpoints. Do not
  combine `-r` with `--from` or `--to`.
- Show one revision's patch for selected files: `jj diff -r @- --git src/`.
  `jj show` accepts revisions, not filesets; use `jj diff -r REV FILESETS` for a scoped patch or
  `jj file show -r REV PATH` for file contents.
- For filename lists, use `jj diff --name-only`. Choose one format: do not combine `--stat`,
  `--summary`, or `--name-only`, or combine them with `jj show --no-patch`.
- `jj diff` has no Git-style `--check`; use the project's formatter or whitespace checker.
- Agents can mistake jj's default diff format for Git's. Use `jj diff --git` when you need a
  Git-compatible patch.
- Limit operations to paths/filesets by passing them positionally:
  `jj commit src/lib.rs tests/` (there is no `--paths`).
  `-R` selects a workspace without changing the current directory; use `root:` filesets or run
  from that workspace. All options must precede `--`, which ends option parsing.
  See [filesets.md](references/filesets.md) for filesets.

### Splitting and merging changes

- Split the current change without invoking the diff editor:
  `jj split 'root:"src/"'` moves `src/` into the first commit; the rest stays in the second.
- Split interactively with the built-in diff editor when hunk selection is the clearest path:
  `jj split -i -m "refactor: extract core logic"` or
  `jj commit -i -m "picked hunks"`.
  Expand files with right arrow, use space to select sections or lines, `c` to confirm, and `q`
  to cancel.
- Combine selectors or set the first commit message inline:
  `jj split -m "refactor: extract core logic" 'glob:"*.rs"' 'glob:"*.toml"'`.
- Create an explicit merge change (no special "merge" command):
  `jj new` with multiple parents (e.g., resolve conflicts, then commit).

### Converging divergent changes

- When one change ID has multiple visible revisions and both may matter, reconcile them with
  `jj converge`.
- Select every variant explicitly:
  `jj converge -r 'change_id(<change-id>)' --no-interactive`.
  Passing a divergent change ID directly is ambiguous. Omit `--no-interactive` only when you can
  respond to prompts.
- With `--no-interactive`, jj exits without changing the divergence if its heuristics cannot
  choose a description, parents, or author. Rerun without the flag and answer the prompts when
  you can provide interactive input. A successful result may still contain file or description
  conflicts.
- Review the convergence with `jj op show -p`. If it is unsatisfactory and still the latest
  operation, run `jj undo`.

### Restoring and abandoning changes

- Pull content from another revision:
  `jj restore --from main --into @ 'glob:"*.toml"'` copies TOML files in from `main`.

Use `--from` and `--into` (alias `--to`) to shuttle content between arbitrary revisions. For
example `jj restore --from @- --into @-- 'root:"src/"'`.

- Abandon a revision, moving its descendants to its parent:
  `jj abandon @` removes the working copy commit and rebases children onto `@-`. The working copy
  gets a new empty commit.
- Abandon a specific revision:
  `jj abandon <revset>` removes that commit and rebases its descendants (use when you want to
  delete a commit but keep its changes in descendants).
- Abandon without moving bookmarks:
  `jj abandon --retain-bookmarks <revset>` moves bookmarks to the parent instead of deleting them.


### rebasing (moving changes)

- Rebase the current change onto `main`:
  `jj rebase -s @ -d main`
- Rebase a stack:
  `jj rebase -b @ -d main` (rebases the current branch/stack relative to `main`)
- Reorder or abandon commits interactively in the arrange TUI:
  `jj arrange`
  Use `j`/`k` to move, `J`/`K` to swap, `a` to abandon, `p` to keep, `c` to confirm, and `q`
  to cancel.

### Bookmarks (branch-like pointers)

- List bookmarks:
  `jj bookmark list`
- Advance the nearest bookmarks to a target revision:
  `jj bookmark advance --to @`
  (prefer this over custom `bookmark move --from ... --to ...` recipes when you want bookmarks to
  follow a rewritten change)
- Move a bookmark to a specific revision (always pass the target):
  `jj bookmark move main --to @-`
- Move via revset:
  `jj bookmark move --from 'heads(::@- & bookmarks())' --to @-`
- Track a remote bookmark so it imports automatically:
  `jj bookmark track <bookmark> --remote <remote>`
- Resolve a conflicted bookmark by moving it to the intended target:
  `jj bookmark move main --to <revset>`

### Working with git remotes

- Configure a remote:
  `jj git remote set-url origin git@github.com:org/repo.git`
- Push a bookmark (maps to a Git branch):
  `jj git push --remote origin --bookmark main`
- Fetch then import bookmarks:
  `jj git fetch --remote origin`
  (colocated repos import automatically.)
- After fetching, run `jj status` or `jj log` before rebasing or pushing. Remote rewrites can
  change bookmark state, and `jj undo` can recover an unexpected fetch.

### Finding the change that introduced a regression

Consider `jj bisect run` for broad history ranges or costly builds/tests; a small, cheap search
may be faster by direct inspection. Read `jj help bisect run` for syntax.

Save the full starting commit ID for range endpoints and restoration (`jj edit <commit-id>`).
Leaving an empty working-copy change can abandon it, making its change ID unresolvable.

### Running a fixer across revisions

- Use `jj run` for deterministic formatters/fixers that should amend selected mutable changes:
  `jj run -r '<revset>' -- <command> [args...]`
- It runs each selected revision in an isolated working copy, amends that revision, and rebases
  descendants. Add `--restore-descendants` when descendants' final file content should stay
  unchanged.
- Add `-j N` only when the command is parallel-safe. For manual or exploratory work, use a
  `jj workspace` instead.

### Bookmark hygiene

- `jj log` marks bookmarks needing push with `name*` and conflicted bookmarks with `name??`.
  Fix conflicts before pushing; otherwise `jj git push` refuses to move them.
- Use `<bookmark>@<remote>` for remote bookmark symbols, e.g. `main@origin`. Do not use Git ref
  paths such as `refs/heads/main` where jj expects a revision or bookmark.
- Remote bookmarks are immutable unless tracked. Run
  `jj bookmark track <bookmark> --remote <remote>` once so later fetches keep the local pointer
  in sync.
- Pushing a bookmark with `jj git push --bookmark <name>` tracks that remote bookmark
  automatically if it was not already tracked.
- `jj git push` performs force-with-lease checks automatically. If it refuses to push, fetch,
  resolve any conflicts, then retry the push.

### Workspace housekeeping

- Keep local-only files ignored: since every jj command snapshots `@`, new files start being
  tracked right away. Add build outputs, secrets, and other local files to `.gitignore` (or
  excludes) and run `jj file untrack <path>` if you find that they have been tracked. For
  non-snapshotting runs, add `--ignore-working-copy`.
- When jj warns “working copy is stale”, resync with `jj workspace update-stale`
  to rebuild the working-copy commit before continuing.
- Show tracked files or content at a revision:
  `jj file list` / `jj file show -r @- -- path/to/file`

### Parallel isolated work

- Share the current workspace when file ownership is clear; use a `jj` workspace, not a Git
  worktree, when filesystem isolation matters.
- Record the names and paths of workspaces this session creates. Only forget or delete those
  workspaces during cleanup; registration in `jj workspace list` does not establish ownership.
- Prefer an immutable change as the base for independent parallel work.
- Before rewriting, inspect `working_copies() & ROOTS::`, where `ROOTS` includes every root the
  operation can rewrite.
- If a sibling appears and may be active, avoid tree-changing rewrites of the shared target.
  Keep the fix in its own child change. Description-only changes are usually lower risk.
- Read [parallel workspace guidance](references/parallel-workspaces.md) before creating a parallel
  workspace; it also covers preflight, shared-history fallbacks, and recovery.

### Templating quick start

- Show a one-line log with IDs and first-line description:
  `jj log -T 'change_id.short() ++ " " ++ commit_id.short() ++ " " ++ description.first_line()'`
- For user-facing summaries, prefer a change-only template:
  `jj log -T 'change_id.short() ++ " " ++ description.first_line()'`
- Use helper methods (e.g., `self.bookmarks().map(|b| b.name()).join(" ")` for bookmark names).
  Templates have command-specific contexts; `evolog`, `file annotate`, and `op log` do not expose
  the same keywords as `log`. See [templates.md](references/templates.md) for tested examples.

## Helpful habits

- Quote revset and fileset expressions passed via the shell to avoid unintended expansion.
- When history editing (squash, split, bookmark move, rebase), print the target revset with
  `jj log -r '<revset>'` so you know exactly which changes will move.
- Skim `jj op log` after larger adjustments; it keeps the undo stack fresh in your mind.
- Use template aliases for commonly viewed logs to shorten the commands you reach for.

### Interactive commands

- Interactive jj commands are available when they are the clearest path. Built-in TUIs such as
  `jj arrange`, `jj commit -i`, `jj split -i`, `jj restore -i`, and `jj diffedit` all work.
- For deterministic automation, prefer explicit filesets plus `-m` or `--stdin`; use interactive
  flows when you need hunk selection, reordering, or visual review.
- Conflict handling can stay text-oriented (`jj resolve --list`, edit markers manually), but merge
  and diff tools are no longer off-limits when they fit the task.

## Cross-references

- See [conflicts.md](references/conflicts.md) for file/bookmark conflict resolution patterns.
- See [filesets.md](references/filesets.md) for fileset selectors.
- See [parallel workspace guidance](references/parallel-workspaces.md) for isolated workflows.
- See [revsets.md](references/revsets.md) for revset primers.
- See [templates.md](references/templates.md) for the templating language.
- Official docs: `https://docs.jj-vcs.dev/`; upstream repo: `https://github.com/jj-vcs/jj`.
