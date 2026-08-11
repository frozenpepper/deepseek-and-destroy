# DeepSeek and Destroy — Claude Code Orchestrator Adapter

Use this only when the **premium orchestrator** runs in Claude Code. The default
technical worker remains the external OpenCode CLI DeepSeek process documented in
`OPENCODE.md`.

## External OpenCode worker: hook-driven re-wake

Claude's native subagent hooks do **not** observe DSD's normal worker because that
worker is an external `opencode run` process. DSD instead uses Claude Code's
project hooks around the Bash launch boundary.

Install/verify the project adapter:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py \
  --harness claude-code \
  --project-root <project-root>
```

Besides the compaction hooks below, this installs
`DeepSeekAndDestroy/tools/claude_worker_rewake.py` and a `PostToolUse` hook for
`Bash` with `asyncRewake: true`.

Normal launch:

```bash
python3 <skill-root>/scripts/run_worker.py \
  --project-root <absolute-project-root> \
  --run-root <absolute-run-root> \
  --task-id <id> --role <role> --attempt <n> \
  --prompt-file <absolute-attempt>/launch-prompt.txt \
  --task-contract <absolute-task-root>/contracts/rNNNN.md \
  --worker-rules <absolute-run-root>/worker-rules/rNNNN/WORKER_RULES.md \
  --scope-baseline <absolute-attempt>/scope-baseline.json \
  --report <absolute-report> \
  --event-dir <absolute-attempt> \
  --log <absolute-attempt>/worker.log \
  --db <absolute-external-run-db> \
  --detach
```

`run_worker.py --detach` returns a tiny JSON launch result immediately. The Claude
`PostToolUse:Bash` hook sees that result, starts a cheap background waiter for the
exact DSD `terminal.json`, and otherwise exits immediately for ordinary Bash calls.
When the external OpenCode worker reaches terminal process state, the waiter exits
with Claude's documented `asyncRewake` signal and supplies only the terminal-event
path/status as a system reminder. Claude can therefore remain idle while the worker
runs; no model turn is spent polling it.

On re-wake:

1. read the named `terminal.json`;
2. classify completed vs process/transport error and update `state.json` once;
3. run the mechanical evidence gate **only for a successful completed exit**;
4. otherwise enter suspect-change/recovery or availability handling as appropriate;
5. route Clerk/review/repair/next action normally.

Do **not** read reports/logs, sample CPU, rewrite state, or narrate merely to prove
liveness while the waiter is active.

### Fallback when hooks are unavailable

Managed policy or local configuration may disable project hooks. In that case use
the portable fallback: detached `run_worker.py` plus `wait_worker.py --event-dir
<attempt-dir>` using its long default blocking wait. A host/tool timeout is a
**non-event**: do no repository/report inspection and immediately issue the same
wait again.

Claude background Bash tasks are also available, but their normal async output is
only guaranteed to be delivered on a later conversation turn. DSD therefore
prefers `asyncRewake` when project hooks are available because it explicitly wakes
an idle Claude on the terminal event.

Claude's `SubagentStart`/`SubagentStop` hooks remain relevant only for
**Claude-native subagents** and are not the DSD external-worker lifecycle contract.

Official references:

- hook lifecycle / `asyncRewake`: https://code.claude.com/docs/en/hooks
- background Bash fallback: https://code.claude.com/docs/en/interactive-mode

## Compaction / continuity hooks

The same adapter installs `PreCompact`, `PostCompact`, and `SessionStart` hooks:

- `PreCompact` prepares the immutable DSD checkpoint; failure blocks compaction;
- `PostCompact` marks rehydration required and stores native summary when exposed;
- `SessionStart` for compact/resume injects the exact rehydration instruction.

When exact context use is exposed, prepare around 65% and compact at a safe boundary
before ~75%. Otherwise rely on hooks + periodic safe-boundary fallback from
`COMPACTION.md`.

After compaction/restart, reload governing authority/skill/run files as required,
run `verify-resume`, then execute persisted `next_action`.
