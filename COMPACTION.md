# DSD Context Checkpoint / Resume

Cold reference for long parent sessions, native compaction, crashes, and fresh-session continuation. Durable run evidence—not a harness-generated summary—is authority.

## Principle

Maintain a **small** `HANDOVER.md` during the run; do not create a giant handover from memory when context is already full. Update it only when continuity materially changes: user/plan authority, consequential decision/correction, important project/harness quirk, active phase/task, worker availability, or an exact `next_action` a fresh parent could misunderstand.

Routine task evidence stays in worker reports (and Clerk reports when used). Mechanical state stays in `state.json`.

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

Before new project work:
1. reload `SKILL.md` + the active parent adapter;
2. read live `state.json`, concise `HANDOVER.md`, plan reference, and latest checkpoint manifest;
3. run:

```bash
python3 DeepSeekAndDestroy/tools/context_checkpoint.py \
  --run-root <exact-run-root> verify-resume \
  --sequence <sequence> --harness <parent-harness>
```

4. revalidate any live worker separately (it may legitimately have advanced while the parent compacted);
5. execute the live `next_action` immediately.

`verify-resume` checks recorded governing plan/reference, authority index, effective configuration, and plan-source identity. It deliberately does not require mutable execution state to remain frozen.

## HANDOVER.md contains only continuity

Keep:
- run/plan/worktree identity;
- user/mission constraints easy to lose;
- current phase/task and meaningful remediation state;
- consequential decisions/corrections and major-log references;
- active worker/evidence pointers when relevant;
- unresolved disputed/human facts;
- exact `next_action` and explicit resume prohibitions.

Do **not** copy the plan, full reports, raw logs, large artifacts, or routine state already represented elsewhere.

## Failure / ambiguity

If native compaction fails, preserve the prepared checkpoint; retry once when sensible or start a fresh parent session from it. A fresh session from a verified checkpoint is a valid continuation.

Hooks must not guess among multiple active runs. Use exact `DSD_RUN_ROOT`/session binding; if several candidates remain, require an explicit run root rather than mutating the wrong run.

HANDOVER prose restores continuity, not technical truth. When a resumed consequential decision depends on a technical claim, follow its accepted/governing evidence or delegate the predicate again.
