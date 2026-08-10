# DeepSeek and Destroy Harness Selection

DSD has **two independent harness choices**:

1. **worker harness** — executes cheap technical workers. Default:
   `OpenCode CLI` + `opencode-go/deepseek-v4-flash`.
2. **orchestrator harness** — the premium parent environment (Claude Code, Codex,
   OpenCode, other). It determines the cheapest native way to wait/wake and how
   context compaction is checkpointed.

Never infer that a Claude/Codex native subagent lifecycle event describes the
default external OpenCode CLI worker.

## Orchestrator adapter selection

1. explicit `DSD_ORCHESTRATOR_HARNESS`/config;
2. current session identity;
3. `scripts/detect_harness.py` as conservative hint;
4. ambiguous → generic fallback, or ask only if the harness-specific capability is
   necessary and cannot be safely inferred.

## External-worker wait strategy

| Orchestrator | Normal OpenCode-worker wait | Routine polling? | Adapter |
|---|---|---|---|
| Claude Code | detached wrapper + project `PostToolUse:Bash` `asyncRewake` waiter keyed to `terminal.json`; portable long-wait fallback if hooks unavailable | **No** | `CLAUDE.md` |
| Codex | foreground wrapper when the shell tool can wait safely; otherwise detached wrapper + one longest-safe `wait_worker.py` call, repeated only after non-event timeout | **No model-level polling** | `CODEX.md` |
| OpenCode | detached/foreground wrapper + long blocking `wait_worker.py`; process exit is terminal evidence | **No model-level polling** | `OPENCODE.md` |
| Other | detached wrapper + long blocking `wait_worker.py`; timeout is a non-event | **No model-level polling** | this file + `OPENCODE.md` transport |

Process/CPU/log-growth polling is **recovery diagnostics only** after a real
wait/tool inconsistency. It is no longer the normal scheduler.

The one-second check inside `wait_worker.py` is deliberately mechanical and consumes
no orchestrator turns.

## Why not OpenCode `session.idle` as the core completion primitive?

Current OpenCode plugins expose `session.idle`, `session.error`, and
`session.status`, and the official plugin example uses `session.idle` for session
completion. DSD nevertheless uses the wrapper's **actual process exit** as its
portable durable terminal event because, together with DSD's enforced
no-background-writer contract, it is the simplest no-more-task-writes boundary and
requires no additional project plugin. Discovery of a lingering writer invalidates
that boundary and enters recovery. An OpenCode event plugin may be added later only
if it materially improves a real harness path.

Official OpenCode plugin reference: https://opencode.ai/docs/plugins/

## Context checkpoint / compaction

This is separate from worker waiting.

| Orchestrator | Native checkpoint integration | Adapter |
|---|---|---|
| Claude Code | `PreCompact` / `PostCompact` / `SessionStart` hooks | `CLAUDE.md` |
| Codex | project-local compaction/session hooks + config where supported | `CODEX.md` |
| OpenCode | project plugin pre-compaction hook + DSD rehydration invariant | `OPENCODE.md` |
| Other | manual/fresh-session protocol | `COMPACTION.md` |

Install only the selected orchestrator harness adapter:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py \
  --project-root <project-root> \
  --harness <codex|claude-code|opencode>
```

The installer remains project-local and does not silently modify user-global
configuration.

## Optional contributed adapters

Optional contributed integrations live under `contrib/`. They are **inactive**
unless explicitly selected and are outside core detection, installation, defaults,
and routing.
