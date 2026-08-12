# DSD Context Checkpoint Reference

Load only for compaction/session replacement. Durable checkpoint + live `state.json` are
authoritative; harness summaries are advisory.

## Maintain, then snapshot

Keep `HANDOVER.md` small and update it only for continuity facts a fresh parent could not
recover cheaply from state/evidence: new user directive, adopted plan revision, material
architecture decision/correction, important environment quirk, phase/remediation change,
or easily misunderstood `next_action`. Do not copy task reports/logs/full plans.

Mechanical state belongs in `state.json`; technical evidence stays in attempt artifacts.
`context_checkpoint.py prepare` snapshots state/HANDOVER/plan/authority into an immutable
numbered checkpoint.

## When

If the host exposes exact context use: checkpoint around 65%, compact at the next safe
persisted boundary before ~75%, and start no new broad reasoning near 80%. If no reliable
counter exists, rely on native PreCompact hooks plus checkpoints after major plan/phase
changes or whenever continuity quality is degrading. Percentages are preferences, not
correctness authority.

Checkpoint statuses: `none`, `prepared`, `compacting`, `rehydration-required`, `resumed`,
`compaction-failed`. While prepared/compacting/rehydration-required, do no new project
work.

## Prepare

1. finish/persist the current atomic decision and exact `next_action`;
2. refresh HANDOVER only if continuity materially changed;
3. run state validation;
4. run:

```bash
python3 DeepSeekAndDestroy/tools/context_checkpoint.py prepare \
  --harness <parent-harness> --reason <reason> [--context-percent <known>]
```

5. verify the new immutable checkpoint, then compact or start a fresh parent session.
A technical worker may remain live; record its exact attempt and revalidate liveness after
resume rather than trusting the old snapshot.

## Resume

Before project work:

1. reload `SKILL.md` + the active harness adapter;
2. read live `state.json`, concise `HANDOVER.md`, plan reference, and latest checkpoint
   manifest;
3. run:

```bash
python3 DeepSeekAndDestroy/tools/context_checkpoint.py \
  --run-root <exact-run-root> verify-resume \
  --sequence <n> --harness <parent-harness>
```

4. separately revalidate any live attempt (it may have advanced during compaction);
5. execute live `state.json.next_action` immediately.

If compaction fails, keep the prepared checkpoint immutable; retry once when sensible or
start a fresh session from it. With multiple active runs, hooks must use exact
`DSD_RUN_ROOT` (or another unambiguous binding) and must never guess.

Resume restores continuity, not technical truth: HANDOVER claims remain claims; accepted
immutable evidence and governing authority keep their normal authority.
