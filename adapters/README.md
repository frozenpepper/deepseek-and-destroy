# Harness adapter assets

Checked-in files under this tree are the **canonical adapter assets** consumed by
`scripts/install_harness_adapter.py`; the installer must not maintain hidden second
copies of their hook/plugin bodies.

- `codex/` — Codex project-local compaction/session hook fragments; optional TOML
  tuning example remains manual because it depends on the actual context window.
- `claude/` — Claude Code project-local hook fragment.
- `opencode/` — OpenCode orchestrator pre-compaction plugin.
- `kilo/` — Kilo project-local pre-compaction plugin and optional native-worker
  subagent templates.

The default DSD worker backend remains external OpenCode CLI. Harness adapters
primarily govern the premium orchestrator's continuity behavior; selecting
Kilo-native workers is an explicit, separate choice documented in `KILO.md`.
