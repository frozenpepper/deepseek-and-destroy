# Harness adapter templates

These files are reference templates. The preferred path is to run
`scripts/install_compaction_adapter.py`, which merges project-local configuration
and copies the checkpoint helper into the project.

- `codex/hooks.json` — Codex lifecycle hooks.
- `codex/config.fragment.toml` — optional threshold settings when the model
  context window is known.
- `claude/settings.fragment.json` — Claude Code hook fragment.
- `opencode/dsd-compaction.ts` — OpenCode V2 pre-compaction plugin.
