# Harness adapter templates

Project-local templates used by `scripts/install_compaction_adapter.py` and worker
installers:

- `codex/` — Codex hooks/config fragments;
- `claude/` — Claude Code settings fragment;
- `opencode/dsd-compaction.ts` — OpenCode pre-compaction plugin;
- `kilo/dsd-compaction.ts` — Kilo pre-compaction plugin;
- `kilo/agents/dsd-mutating-worker.md` and `dsd-readonly-worker.md` — Kilo
  subagent templates rendered by `scripts/install_kilo_agents.py`.

Do not hand-edit installed Kilo agents to change models; rerun the installer so the
model ID is validated first.
