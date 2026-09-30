# Jujutsu skill

Agent Skills for working with [Jujutsu](https://docs.jj-vcs.dev/) (`jj`). The `jj` skill covers
commits, diffs, history edits, bookmarks, conflicts, workspaces, and remote synchronization.

## Tested versions

**Last tested: 2026-09-30 on macOS.**

| Tool | Version |
| --- | --- |
| Jujutsu (`jj`) | `0.45.1` |
| Claude Code | `2.1.285` |
| Codex CLI | `0.159.2` |

Checks cover basic jj command workflows, strict Claude Code plugin manifest validation, and
Codex marketplace discovery.

The same skill files are packaged for Codex and Claude Code. They require `jj` on `PATH`.
Repository detection uses `jj --ignore-working-copy root` when the repository type has not
already been confirmed.

## Install in Codex

```bash
codex plugin marketplace add bos/jj-skill
codex plugin add jj@jj-skill
```

Start a new session after installation. The plugin is named `jj` in the `jj-skill` marketplace.

## Install in Claude Code

Run these commands inside Claude Code:

```text
/plugin marketplace add bos/jj-skill
/plugin install jj@jj-skill
```

Start a new session after installation.

## Install as a standalone skill

For agents supported by the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add bos/jj-skill --skill jj -g -a codex -a claude-code
```

Use one installation method per agent to avoid duplicate skill entries.

## Local development

```bash
git clone https://github.com/bos/jj-skill.git
cd jj-skill
claude --plugin-dir .
```

To test the Codex marketplace from this checkout:

```bash
codex plugin marketplace add .
codex plugin add jj@jj-skill
```

## Package layout

- `skills/jj/SKILL.md`: portable instructions and metadata.
- `skills/jj/references/`: focused reference material loaded when needed.
- `skills/jj/agents/openai.yaml`: Codex skill presentation metadata.
- `plugin.json`: portable Agent Plugins manifest.
- `.codex-plugin/plugin.json`: Codex compatibility manifest and plugin presentation metadata.
- `.agents/plugins/marketplace.json`: Codex marketplace catalog.
- `.claude-plugin/plugin.json`: Claude Code plugin manifest.
- `.claude-plugin/marketplace.json`: Claude Code marketplace catalog.

All plugin content is inside this repository; the package contains no symlinks to external files.

## Validation and contributing

Validate the Claude manifests before publishing:

```bash
claude plugin validate --strict .claude-plugin/plugin.json
claude plugin validate --strict .claude-plugin/marketplace.json
```

Keep the name, version, license, and description consistent across the plugin manifests.
For command examples, follow [the contributing guidance](CONTRIBUTING.md) and test them against
the installed `jj` version. Keep files within 96–98 columns where practical.
Update the tested versions and date near the top of this README after revalidating a release.

Copyright 2026 Bryan O'Sullivan. Licensed under [Apache-2.0](LICENSE).
