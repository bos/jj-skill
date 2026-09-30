# Parallel workspaces in jj

Workspaces isolate checked-out files, not history.

## Choosing a base

Create a workspace at the revision the task needs:

```bash
jj workspace add --name NAME -r BASE PATH
```

`BASE` can be an unpublished mutable dependency; it need not be `main` or immutable. Specify it
explicitly: without `-r`, the new workspace starts from the current working copy's parents.
Rewriting a mutable base also rebases descendants and can make your workspace stale. Run
`jj workspace update-stale` in your own workspace when jj reports this, then use `jj status` and
`jj log` to inspect conflicts and divergent changes as described under [recovery](#recovery).

## Ownership and cleanup

Record the names and paths of workspaces your session creates. A sibling appearing in
`jj workspace list` may belong to another session; its presence is not permission to clean it up.
Retire only a workspace recorded as created by this session, after the task and every command
or agent you launched there have finished. If you handed it to another session or find unexpected
edits, leave it in place and report it. A clean diff does not account for ignored files or
processes using the directory.

## Sharing a checkout

Pre-existing edits and edits arriving during the task both need protection. Status and diff show
current contents, not who made them or who will write next. Treat unattributed edits as belonging
to someone else; do not claim a whole file because it was clean at the start.

Disjoint-file edits can stay in the current checkout with task-scoped commits. For overlapping
concurrent file edits, or when switching revisions would disrupt another writer, use a separate
workspace. A fileset or interactive hunk selection cannot prevent a later write to the same file
from being included when your command snapshots it. Do not copy the entire shared pending diff
into your workspace; it may contain unrelated edits.

## Before rewriting shared history

Find registered working copies below any root the operation may rewrite:

```bash
jj --ignore-working-copy log -r 'ROOTS:: & working_copies()'
```

`ROOTS` must include all rewrite roots. For example, use `(S | D)` for
`squash --from S --into D`; experiments showed that descendants on both sides can be rewritten.

This checks affected ancestry, not visibility: visible commits are repository-wide. It is also
only a point-in-time check; it cannot prevent another process from targeting the same change,
sharing the same workspace, or acting afterward.

A description-only rewrite normally preserves sibling checkouts, even with unsnapshotted edits,
but can still diverge if another process rewrites the same change concurrently. Tree or parent
changes can make sibling working copies stale, displace unsnapshotted edits into divergent
commits, or create rebase conflicts.

If a tree-changing rewrite would affect another session's workspace, keep the fix in its own
child change instead of squashing it into shared history. Do not snapshot or run
`workspace update-stale` in another session's workspace. Repeat the check before later squashing.

## Recovery

After `workspace update-stale`, check for conflicts and divergent changes. The command preserves
unsnapshotted contents, but may put them in a divergent commit while checking out another
successor. Inspect the commits before folding displaced edits into the intended change.
