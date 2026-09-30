# Parallel workspaces in jj

Workspaces isolate checked-out files, not history. Prefer an immutable base for independent work;
rewriting mutable history can also rewrite another workspace's working-copy commit.

Do not use an active workspace's working-copy change as the parent of a parallel workspace;
normal work in the active workspace will keep rewriting that parent.

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

If an affected sibling is known idle, snapshot it before the rewrite and run
`workspace update-stale` there afterward. If it may be active and cannot be contacted, keep the
fix in its own child change instead of squashing it into shared history. Repeat the check before
squashing it later.

## Recovery

After `workspace update-stale`, check for conflicts and divergent changes. The command preserves
unsnapshotted contents, but may put them in a divergent commit while checking out another
successor. Inspect the commits before folding displaced edits into the intended change.
