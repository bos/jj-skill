# Handling conflicts in jj

Conflicts appear whenever multiple revisions touch the same content or a remote bookmark diverges.
These notes focus on the simplest file-editing workflow, while leaving interactive diff or merge
tools available when they are the better fit.

## Detecting conflicts

- Conflict markers show up in command output:
  - `jj rebase` / `jj merge` report `New conflicts appeared in …`.
  - `jj log` labels conflicting commits with `(conflict)`, and `jj status` lists paths under
    “Warning: There are unresolved conflicts …”.
- List conflicted paths explicitly with `jj resolve -r <conflicted-change> --list`.
- Bookmark conflicts surface as names ending in `??`; use `jj bookmark list` to inspect them.

## Conflict markers in files

File conflicts use structured sections, not Git’s plain `<<<<<<<` syntax. A typical two-way
marker looks like this:

```
<<<<<<< Conflict 1 of 1
++++++ Contents of side #1
right1
%%%%%%% Changes from base to side #2
-line1
+left1
>>>>>>> Conflict 1 of 1 ends
```

- The order of blocks can vary; read the labels to see which parent is presented as a diff and
  which shows literal content.
- `Contents of side #N` shows the exact text from that parent, while
  `Changes from base to side #M` shows the edits that parent made relative to the base.
- For more than two parents, additional `%` sections appear for side #3, #4, etc.

Always edit the file to the desired final content and delete the entire marker block.

## Safe workflow for file conflicts

1. If the conflicted commit is not the working copy, create a throwaway child change to hold the
   resolution: `jj new <conflicted-change> -m "resolve <path>"`. If the conflict already lives in
   `@`, stay on the existing working-copy change.
2. Edit each conflicted file manually until no markers remain.
3. Run `jj status` to verify only normal modifications remain, then `jj resolve --list` to confirm
   the working copy has no conflicts.
   When clean, jj prints “No conflicts found at this revision” and exits with status 2.
   Treat that as success. Pass `-r <rev>` if you need to inspect another commit.
4. Fold the resolution back into the conflicted change:
   `jj squash --into @- --use-destination-message` (or supply `-m "message"` if the description
   must change), then update the description with `jj describe -m "message"` if needed.
5. Re-run `jj resolve -r @- --list`; expect the same “No conflicts found …” message and exit
   status once the resolution is folded back into the conflicted commit.

## Bookmark conflicts

- Identify the divergent bookmark with `jj bookmark list` (look for `bookmark??`).
- Choose the correct target (often the rebased change) and move the bookmark:
  `jj bookmark move bookmark-name -t <target-rev>`.
- If the remote copy differs, fetch first (`jj git fetch --remote origin`), resolve the local
  bookmark, then push with `jj git push --remote origin --bookmark bookmark-name`.

Keep the working copy clean before resolving bookmark conflicts so the move can succeed.
