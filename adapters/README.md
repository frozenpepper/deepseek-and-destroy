# Harness adapter templates

These files are reference templates. The preferred path is to run
`scripts/install_compaction_adapter.py`, which merges project-local configuration
and copies the checkpoint helper into the project.

- `codex/hooks.json` — Codex lifecycle hooks.
- `codex/config.fragment.toml` — optional threshold settings when the model
  context window is known.
- `claude/settings.fragment.json` — Claude Code hook fragment.
- `opencode/dsd-compaction.ts` — OpenCode V2 pre-compaction plugin.
- `kilo/dsd-compaction.ts` — Kilo Code pre-compaction plugin. **Experimental
  and unverified** — see HARNESS.md's capability matrix before relying on it.
- `kilo/agents/dsd-mutating-worker.md`, `kilo/agents/dsd-readonly-worker.md` —
  role-separated Kilo worker subagent templates (`{{MODEL}}` placeholder).
  Install with `scripts/install_kilo_agents.py`, which resolves and verifies
  the model before writing them — do not copy these by hand.
