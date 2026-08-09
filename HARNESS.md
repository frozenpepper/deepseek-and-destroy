# DeepSeek and Destroy — Orchestrator Harness Selection

Worker harness and main-orchestrator harness are independent. Resolve the
orchestrator harness from explicit configuration/current session before using
heuristics.

## Selection

1. Explicit `DSD_ORCHESTRATOR_HARNESS`/configuration wins.
2. Otherwise use current session/system identity.
3. `scripts/detect_harness.py` may provide a conservative hint.
4. Ambiguous detection must not silently select an adapter.

Supported adapters:

| Harness | DSD adapter | Native/project hook status |
|---|---|---|
| Codex | `CODEX.md` | pre/post/session resume hooks |
| Claude Code | `CLAUDE.md` | pre/post/session resume hooks |
| OpenCode | `OPENCODE.md` | pre-compaction plugin + DSD rehydration invariant |
| Kilo Code | `KILOCODE.md` | project plugin; live compaction acceptance recommended |
| Other | `COMPACTION.md` | manual/fresh-session fallback |

## Install

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --project-root <project-root> \
  --harness <codex|claude-code|opencode|kilo>
```

The installer is project-local, copies `context_checkpoint.py` and `check_state.py`
into `DeepSeekAndDestroy/tools/`, backs up modified JSON settings where applicable,
and writes an installation report. It does not silently modify user-global harness
configuration.

Regardless of harness, the external DSD checkpoint is the continuity authority;
native summaries are advisory. After compaction/session replacement, execute
`verify-resume` before project work.
