# DeepSeek and Destroy — Claude Code Orchestrator Adapter

Use this file when the **main orchestrator** is Claude Code. Worker agents may use
another configured harness.

## Supported mechanism

Claude Code supports `PreCompact`, `PostCompact`, and `SessionStart` hooks.
`SessionStart` with matcher `compact` runs after automatic or manual compaction and
can add context back to Claude.

## Install

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --harness claude-code \
  --project-root <project-root>
```

This merges project-local hooks into `.claude/settings.json` and installs the
checkpoint helper under `DeepSeekAndDestroy/tools/`.

## Threshold

Claude Code does not expose a portable project setting equivalent to “compact at
65% of the context window.” Therefore:

- when the current client exposes context usage, prepare at 65% and invoke
  `/compact` at the next safe boundary;
- otherwise maintain HANDOVER incrementally and rely on PreCompact to create the
  checkpoint before native automatic compaction;
- also use the periodic safe-boundary fallback from `COMPACTION.md`.

## Hook behavior

- `PreCompact`: prepares the checkpoint. If preparation fails, it blocks
  compaction so the run is not compressed without durable continuity.
- `PostCompact`: stores the native compact summary when available and marks the
  run `rehydration-required`.
- `SessionStart` matching `compact|resume`: injects the exact rehydration steps.

After injection, Claude must reload the skill and live run files, run
`verify-resume`, and immediately execute `next_action`.

## Manual path

Without hooks:

1. run checkpoint preparation;
2. use `/compact` with a short reminder to preserve the active DSD run path;
3. reload the skill and checkpoint after compaction;
4. verify continuity and continue.

## Official references

- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/hooks-guide
