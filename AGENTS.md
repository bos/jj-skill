# Jujutsu skills repository

The canonical skill lives in `skills/jj/`. Keep its instructions and references self-contained;
do not introduce dependencies on files outside this repository or agent-specific global
instructions.

Preserve the portable Agent Skills format. Put Codex presentation metadata in
`skills/jj/agents/openai.yaml`. Keep plugin identity, version, description, and license consistent
across `plugin.json`, `.codex-plugin/plugin.json`, and `.claude-plugin/plugin.json`.

The Codex and Claude marketplace catalogs both expose the root plugin as `jj@jj-skill`.
Package files must stay inside the repository and must not be external symlinks.

Follow `CONTRIBUTING.md`. Keep lines within 96–98 columns where practical. Run the manifest and
validation commands in `README.md` after packaging changes, and test changed jj command
examples in a temporary repository before committing them.
