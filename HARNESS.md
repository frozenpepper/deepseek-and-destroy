# DeepSeek and Destroy — Harness Routing

DSD separates two runtimes:

- **worker harness** — cheap technical execution; default OpenCode CLI + DeepSeek;
- **parent harness** — premium orchestrator; controls launch/wake/checkpoint plumbing.

The worker lifecycle is not a native Codex/Claude subagent lifecycle unless a
non-default native worker backend is explicitly selected.

## Select the parent adapter

Prefer explicit config (`DSD_ORCHESTRATOR_HARNESS`), then current session identity,
then `detect_harness.py` as a conservative hint. If ambiguous, use generic behavior
unless a harness-specific capability is actually required.

Load exactly one adapter (`CODEX.md`, `CLAUDE.md`, `OPENCODE.md`, `KILO.md`, or the generic fallback). This file
states routing only; adapter files own host-specific mechanics.

## Universal wait invariant

Normal waiting is quiescent. External workers use the exact `terminal.json` emitted
after wrapper process exit; the one-second check inside `wait_worker.py` is mechanical
and consumes no model turns. A host/tool timeout with no terminal event is a
**non-event**: wait again without logs, CPU checks, state narration, or repository
inspection. Those are recovery diagnostics only after an actual inconsistency.

A supported native backend uses its native Task return as the terminal boundary and
then immediately finalizes the same DSD `terminal.json`; see that adapter. Semantic
PASS/FAIL is never inferred from transport completion.

## Checkpoint routing

Compaction/checkpoint integration is separate from worker waiting. Load the active
adapter and `COMPACTION.md` only when checkpoint/resume behavior is relevant.

Install only the selected project-local adapter:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py \
  --project-root <project-root> \
  --harness <codex|claude-code|opencode|kilo>
```



## Kilo Code

When the premium parent runs in Kilo, use `KILO.md`. Install the project-local
continuity plugin with `install_harness_adapter.py --harness kilo`. The default
worker remains external OpenCode unless the run explicitly selects the Kilo-native
backend; Kilo-native subagents use `native_worker_attempt.py` so they enter the
same immutable launch/evidence/scope lifecycle.
