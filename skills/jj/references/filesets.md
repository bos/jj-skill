# filesets in jj

Many `jj` commands accept positional **fileset** selectors.

If you can't find what you need below, run `jj help -k filesets` for the authoritative
reference on filesets.

## Core patterns

- Pass filesets positionally:
  `jj commit src/ tests/` / `jj split 'root:"src/"' 'glob:"*.rs"'`
- Path filters: `root:"dir/"`, `glob:"*.md"`, `glob-i:"*.md"` for case-insensitive matches,
  negate with `~glob:"*.lock"`.
- Use `--` before pathnames that could be parsed as flags:
  `jj file show -r @- -- path/to/file`.
  Put every option before `--`; afterward, `--git` and other flags are treated as paths.

## Repository and directory context

`-R` / `--repository` selects a workspace without changing the process's working directory.
Bare paths still resolve from that directory, and path output remains relative to it. For scripts,
run from the target workspace; for fileset inputs from outside it, use `root:` selectors:

```bash
jj -R ../other file show -r @- 'root:"src/lib.rs"'
```

## Quoting cues

- Shell-quote expressions that contain spaces or operators:
  `jj diff '"Foo Bar"'`.
- `cwd:"path"` filters relative to the current directory; `root:"path"` filters from the
  workspace root.
- Combine selectors with `&`, `|`, and `~`, or use the functional form (`all()`, `none()`)
  when it reads clearer.

## Examples

- Diff everything except lockfiles:
  `jj diff '~glob:"**/*.lock"'`
- List files in `src/` excluding Rust sources:
  `jj file list 'root:"src/" ~ glob:"**/*.rs"'`
