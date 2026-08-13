# DSD Context Checkpoint / Resume

Cold reference for long parent sessions, native compaction, crashes, and fresh-session continuation. Durable run evidence—not a harness-generated summary—is authority.

## Principle

`state.json` is the execution-resume authority. Keep `HANDOVER.md` only for **non-state continuity** that would otherwise be easy to lose: user/mission constraints, consequential context not already in the major log, or an important project/harness quirk. Do not duplicate the active task, worker, gate, or `next_action` already present in state.

Routine evidence stays in worker/Clerk reports. Consequential parent decisions belong briefly in `major-findings-and-fixes.md`.

## When to checkpoint

Prefer native PreCompact hooks. Otherwise checkpoint at a safe orchestration boundary when context is becoming constrained, before a large phase decision, after a major plan/remediation change, or after several accepted tasks in a long session. Configured percentage thresholds are hints, not correctness dependencies.

A safe boundary means the current atomic orchestration decision and exact `next_action` are already durable. Do not checkpoint midway through an unrecorded decision.

## Prepare

```bash
python3 DeepSeekAndDestroy/tools/context_checkpoint.py prepare \
  --harness <parent-harness> \
  --reason <reason> \
  [--context-percent <known-percent>]
```

Preparation creates an immutable `compactions/<sequence>/` checkpoint containing the continuity snapshot and resume manifest. Once prepared, compact or switch sessions before starting new project reasoning. A worker may remain live; its mutable lifecycle is revalidated after resume.

Checkpoint states are mechanical lifecycle markers only: `none`, `prepared`, `compacting`, `rehydration-required`, `resumed`, `compaction-failed`.

## Resume

Before new project reasoning:
1. reload `SKILL.md` + the active parent adapter;
2. identify the exact run from explicit binding or minimal candidate state metadata;
3. read the chosen live `state.json` **first**;
4. if a prepared checkpoint exists, run `verify-resume` below;
5. revalidate any live worker if needed, then execute a mechanical `next_action` immediately;
6. only when `next_action` requires parent judgment, read the exact named decision/evidence/authority. Read HANDOVER only if genuinely needed for non-state continuity.

```bash
python3 DeepSeekAndDestroy/tools/context_checkpoint.py \
  --run-root <exact-run-root> verify-resume \
  --sequence <sequence> --harness <parent-harness>
```

`verify-resume` checks recorded governing plan/reference, authority index, effective configuration, and plan-source identity without requiring mutable execution state to remain frozen. Do not read git history, session notes, old contracts/reports, or broad project architecture just because the parent session changed.

## HANDOVER.md is cold continuity only

Keep only context not already represented durably elsewhere: user/mission constraints easy to lose, consequential context not yet captured in the major log, unusual project/harness quirks, or unresolved human facts. Do **not** copy the plan, active task/worker/`next_action`, full reports, raw logs, large artifacts, or routine state.

## Failure / ambiguity

If native compaction fails, preserve the prepared checkpoint; retry once when sensible or start a fresh parent session from it. A fresh session from a verified checkpoint is a valid continuation.

Hooks must not guess among multiple active runs. Use exact `DSD_RUN_ROOT`/session binding; if several candidates remain, require an explicit run root rather than mutating the wrong run.

HANDOVER prose restores continuity, not technical truth. When a resumed consequential decision depends on a technical claim, follow its accepted/governing evidence or delegate the predicate again.
