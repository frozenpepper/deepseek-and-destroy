# Harness adapter templates

Core DSD defaults to **external OpenCode CLI workers**. Orchestrator-specific
adapters exist only for context checkpoint/continuity integration; external worker
launch/wait semantics are documented in `HARNESS.md`, `CLAUDE.md`, `CODEX.md`, and
`OPENCODE.md`.

- `codex/` — Codex project-local compaction/session hook fragments.
- `claude/` — Claude Code project-local compaction/session hook fragments.
- `opencode/` — OpenCode orchestrator pre-compaction plugin.

Optional contributed integrations live under top-level `contrib/`, outside this
core adapter tree. They are not loaded or detected unless explicitly selected.
