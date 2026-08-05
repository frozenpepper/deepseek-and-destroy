# DeepSeek and Destroy — Codex Orchestrator Adapter

Use this file when the **main orchestrator** is Codex. Worker agents may still use
OpenCode, Claude Code, Codex subagents, or any configured backend.

## Supported mechanism

Codex supports project-local `hooks.json` or inline hook configuration,
`PreCompact`, `PostCompact`, and `SessionStart` hooks. After compaction,
`SessionStart` with source `compact` runs before the next model request and can
inject developer context.

## Install

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --harness codex \
  --project-root <project-root>
```

This installs:

- `<project>/.codex/hooks.json` entries;
- `<project>/DeepSeekAndDestroy/tools/context_checkpoint.py`.

Then open `/hooks` in Codex and review/trust the new project-local hooks. Codex
skips untrusted changed hooks.

## Threshold

When the active model context window is known, Codex can set:

```toml
model_context_window = <model-context-tokens>
model_auto_compact_token_limit = <65-percent-of-window>
model_auto_compact_token_limit_scope = "total"
```

Do not invent the context-window value. If it is unavailable, leave the native
threshold unchanged and rely on the PreCompact checkpoint hook plus the periodic
safe-boundary fallback in `COMPACTION.md`.

## Hook behavior

- `PreCompact`: creates an immutable DSD checkpoint. If checkpoint preparation
  fails, it stops compaction rather than allowing an uncheckpointed transition.
- `PostCompact`: records that rehydration is required.
- `SessionStart` matching `compact|resume`: injects a concise instruction with the
  exact run, checkpoint, state, and verify-resume command.

Keep injected context short. The authoritative content stays on disk.

## Manual path

If hooks are unavailable or disabled:

1. prepare the checkpoint with `context_checkpoint.py`;
2. invoke Codex compaction using the current client command/UI;
3. after continuation, reload the skill and run `verify-resume`;
4. execute the persisted `next_action`.

## Important limitation

Project-local hooks require a trusted project and may be disabled by managed
policy. When hooks cannot run, use the generic manual or fresh-session protocol.

## Official references

- https://developers.openai.com/codex/hooks
- https://developers.openai.com/codex/config-reference
