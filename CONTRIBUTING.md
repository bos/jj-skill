# Contributing

This directory collects quick-reference material that informs an agent about how jj works and
differs from git, and keeps our agent from repeating the most common Jujutsu mistakes. The goal
is to provide short, actionable reminders, not a full copy of `jj help`.

## Philosophy

- **Keep it tactical.** Each file should capture guidance that fixes or prevents real errors we
  have already seen. If a section reads like a textbook, trim it.
- **Prefer correctness over completeness.** Every example must run as written.  When adding
  commands, templates, functions, or syntax snippets, test them in a real repo before
  committing. If a command fails or the syntax is ambiguous, fix or delete it.
- **Point to the source docs.** When deeper knowledge is required, link to `jj help -k …` or
  upstream documentation instead of duplicating it here.
- **Optimize for agents.** These files are meant to be read under token and time pressure. Use
  concise prose, highlight “do / do not” guidance, and keep line lengths within repository
  conventions.

## What belongs here

- Mandatory workflows or guardrails (e.g., “never use git commands when `.jj` exists”).
- **Tested** command patterns that agents routinely need.
- Cross-references to official jj help commands or repo docs.
- Notes that resolve recurring confusion (bookmark conflicts, fileset syntax,
  template pitfalls, diff-format gotchas like agents needing `jj diff --git`, etc.).

## What does not belong here

- Exhaustive API or keyword listings duplicated from `jj help`.
- Speculative advice that has not addressed an observed issue.
- Long narrative tutorials or historical commentary.
