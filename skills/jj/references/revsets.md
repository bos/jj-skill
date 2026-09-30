# revsets in jj

Most `jj` commands accept `-r REVSET` (or `--revision`). Keep these quick cues handy.

If you can't find what you need below, run `jj help -k revsets` for the authoritative list of
keywords, methods, and helper functions.

## Common symbols and operators

- `@`: Working copy. `@-`: Parent of the working copy.
- `A..B`: Commits reachable from `B` but not from `A` (shorthand for `ancestors(B) ~
  ancestors(A)`).
- `::X`: Ancestors of `X` (including `X`). `X::`: Descendants of `X` (including `X`).
- Use `roots(X)` and `heads(X)` to bound larger revsets.
- Functions: `ancestors()`, `descendants()`, `author()`, `description()`, `tags()`,
  `bookmarks()`, `remote_bookmarks()`.
- Quote complex expressions when passing through the shell:
  `jj log -r 'author(me) & description(fix)'`.

## Visibility and safety cues

- Symbol resolution prefers tags, then bookmarks, and finally commit or change IDs. Remote
  bookmarks and tags use `<name>@<remote>`, such as `main@origin`.
- Git-like refs such as `refs/heads/main` are not revision symbols. Use a bookmark, tag,
  `<name>@<remote>`, or explicit ID instead.
- If you must force matching by ID, wrap with `commit_id("abc123")`.
- Change IDs can be ambiguous when a change is divergent or hidden. Use change offsets such as
  `abcxyz/0` and `abcxyz/1` to name a specific version of a change.
- History-editing commands differ in whether an option expects one revision or several. Check
  `jj help <command>` before passing a broad revset, and prefer quoted revsets in the shell.

## Common idioms

- Filter by touched files with `files("path")`.
  Example: `jj log -r '::@ & files("skills/jj/SKILL.md")'`.
- Use `parents(x)` or the shorthand `x-` to reach parents; Git-style `x^` is unsupported.
  Example: `jj log -r 'parents("ymvvlnwz")'`.
- Use `visible()`, `hidden()`, and `divergent()` when inspecting unusual history states.
  Example: `jj log -r 'divergent() | hidden()'`.

## Examples

- Show commits not on any remote bookmark:
  `jj log -r 'remote_bookmarks()..'`
- Show only visible heads:
  `jj log -r 'heads(visible())'`
- Rebase the current stack onto `main`:
  `jj rebase -b @ -d main`.
  `descendants(@) ~ @` selects only children and later descendants, excluding the current change
  and its ancestors; it does not select the stack leading to `@`.
