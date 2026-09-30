# jj templating language

`jj` supports a typed functional templating language via `-T/--template`.

If you can't find what you need below, run `jj help -k templates` for the authoritative list of
keywords, methods, and helper functions.

## Concepts to remember

- Zero-argument methods on the current commit become keywords (`commit_id` is shorthand for
  `self.commit_id()`). Use method-call syntax when you need arguments or chaining.
- Collections expose iterator helpers such as `.map(|item| ...)` and `.join(" ")`—handy for
  bookmarks, parents, and files.
- High-leverage helpers include `separate(" ", ...)` for optional components and
  `label("role", ...)` for color control.

## Quick patterns

- One line with ids and summary:
  `jj log -T 'commit_id.short() ++ " " ++ change_id.short() ++ " " ++ description.first_line()'`
- Include bookmarks:
  `jj log -T 'commit_id.short() ++ " " ++ self.bookmarks().map(|b| b.name()).join(" ") ++`
  `" " ++ description.first_line()'`
- Use helper methods via method syntax and parentheses. Most day-to-day commands (`jj log`,
  `jj status`, etc.) accept `-T`.

## Tips

- Parenthesize helper calls inside string concatenations:
  `self.bookmarks().map(|b| b.name()).join(" ")`.
- Explore built-in template aliases via `jj config list --include-defaults template-aliases`
  if you need inspiration, but avoid editing configs during a session.

## Common idioms

- Use `++` to concatenate values directly; the template language does not
  understand `{...}` or `{{...}}`. Example:
  `jj log --no-graph -n 5 -T 'change_id.short() ++ " " ++ commit_id.short() ++ " " ++`
  `description.first_line()'`.
- Zero-argument methods become keywords, so you can drop the parentheses:
  `commit_id.short()` / `change_id.short()` instead of `commit_id().short()`.
- Methods that live on the commit need an explicit receiver. To show bookmarks:
  `self.bookmarks().map(|b| b.name()).join(" ")`. To flag conflicts inline:
  `if(self.conflict(), " (conflict)", "")`.

## Examples

- Compact graph with first line:
  `jj log -T 'format_short_commit_header(self)'`
