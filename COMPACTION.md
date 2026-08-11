# DeepSeek and Destroy Context Checkpoint Protocol

This protocol keeps very long orchestrator runs reliable across native context
compaction, full session replacement, crashes, and deliberate handoff.

The durable checkpoint—not the harness-generated summary—is authoritative.

## Design goals

- Preserve project intent, user directives, learned quirks, current task state,
  and the exact next action.
- Avoid making the orchestrator rewrite mechanical state or reread the whole run.
- Keep checkpoint preparation cheap enough to use repeatedly.
- Support multiple active orchestrators without guessing the wrong run.
- Use native harness hooks where available, but remain functional without them.

## The key optimization: maintain, then snapshot

Do **not** wait until the context is nearly full and then ask the orchestrator to
write a giant handover from memory.

`HANDOVER.md` is a compact, incrementally maintained continuity file. Update it
only when durable continuity changes materially:

- a new user instruction changes execution;
- a plan revision is adopted;
- a phase or remediation cycle changes;
- a major architectural decision or correction is made;
- an important project or harness quirk is learned;
- worker availability changes materially;
- the exact active task or `next_action` changes in a way a fresh session could
  misunderstand.

Routine task evidence stays in Decision Packets and reports. Mechanical state
stays in `state.json`. At checkpoint time, `scripts/context_checkpoint.py`
snapshots those files and writes a small resume manifest. The orchestrator adds
only a short continuity delta when something important is not already durable.

## Threshold policy

Defaults are user-configurable:

- **Checkpoint due:** 65% of orchestrator context.
- **Compact at:** the next safe orchestration boundary after checkpoint due,
  normally before 75%.
- **Hard ceiling:** at 80%, start no new substantial plan-wide reasoning. Persist
  and compact or switch to a fresh orchestrator session.

A safe boundary is after one atomic orchestration decision has been persisted:
for example after launching a worker, accepting a task, writing a remediation
plan, or recording a human blocker. Do not compact halfway through an unrecorded
phase-gate judgment.

When the harness exposes no reliable context percentage, use all of these:

- native PreCompact hooks;
- an incremental `HANDOVER.md`;
- a checkpoint after every configured number of accepted tasks (default 4);
- a checkpoint before a phase gate when the session is already long;
- a checkpoint after a plan revision or major remediation cycle;
- immediate checkpointing when recall degradation or repeated rereading appears.

The percentage is a trigger preference, not a correctness dependency.

## Checkpoint state machine

`state.json.context_checkpoint.status` uses:

- `none` or absent — no checkpoint is pending;
- `prepared` — immutable checkpoint files exist;
- `compacting` — native compaction was requested or started;
- `rehydration-required` — compaction completed or a replacement session began;
- `resumed` — identity and continuity were verified;
- `compaction-failed` — checkpoint remains valid, but native compaction failed.

While status is `prepared`, `compacting`, or `rehydration-required`, the
orchestrator performs no new project work. It completes the checkpoint or
rehydration transition first.

## Workspace additions

Each run contains:

```text
<run-root>/
  HANDOVER.md
  state.json
  authority-index.json
  compactions/
    LATEST
    0001/
      CHECKPOINT.md
      resume-manifest.json
      state.snapshot.json
      HANDOVER.snapshot.md
      plan-reference.snapshot.md
      authority-index.snapshot.json
      native-compact-summary.md   # when the harness exposes it
    0002/
      ...
```

Checkpoints are immutable. Never overwrite an older checkpoint.

## Preparing a checkpoint

At the threshold or native PreCompact event:

1. Finish the current atomic orchestration decision and persist `next_action`.
2. Ensure `HANDOVER.md` contains current non-mechanical continuity information.
3. Run the state invariant checker.
4. Run:

   ```bash
   python3 DeepSeekAndDestroy/tools/context_checkpoint.py prepare \
     --harness <orchestrator-harness> \
     --reason context-threshold \
     --context-percent <known-percent>
   ```

5. Verify that the checkpoint directory and resume manifest exist.
6. Invoke the harness-native compaction mechanism or begin a fresh orchestrator
   session using that checkpoint.
7. Do not perform new project reasoning between checkpoint preparation and
   compaction.

A worker may remain live during compaction. Record its exact identity and paths;
after compaction, revalidate the worker rather than trusting old liveness.

## Rehydrating after compaction

Before any project work:

1. Reload `SKILL.md` and the adapter selected in `HARNESS.md`.
2. Read live `HANDOVER.md`, `state.json`, and `plan/plan-reference.md`.
3. Read the latest `CHECKPOINT.md` and `resume-manifest.json`.
4. Run the mechanical continuity verifier:

   ```bash
   python3 DeepSeekAndDestroy/tools/context_checkpoint.py \
     --run-root <exact-run-root> \
     verify-resume \
     --sequence <checkpoint-sequence> \
     --harness <orchestrator-harness>
   ```

5. Revalidate any live worker/process separately; mutable execution state may have
   legitimately advanced during compaction.
6. Execute the live `state.json` `next_action` immediately.

Do not stop after announcing that compaction or rehydration succeeded.

## What belongs in HANDOVER.md

Keep it concise and current:

- run, plan, worktree, and authoritative snapshot identity;
- mission/ethos constraints that are easy to lose;
- user instructions introduced during this run;
- current phase, active task, and remediation cycle;
- recent accepted Decision Packet paths;
- important learned architecture or operational quirks;
- material corrections and major-log references;
- active worker identity and evidence paths;
- open disputed facts or human requirements;
- one exact `next_action`;
- actions explicitly forbidden on resume.

Do not copy full task reports, raw logs, large artifacts, or the full plan into the
handover.

## Failure handling

If native compaction fails:

- keep the prepared checkpoint untouched;
- record `compaction-failed` and the error;
- retry native compaction once when appropriate;
- otherwise start a fresh orchestrator session from the same checkpoint.

A fresh session from the checkpoint is a valid fallback and should be treated as
semantically equivalent to successful native compaction.

## Multiple active runs

Hooks must not guess among multiple active runs. Prefer, in order:

1. exact `DSD_RUN_ROOT`;
2. a state entry matching the current orchestrator session id;
3. one unambiguous active run in the current project.

If several candidates remain, block checkpoint mutation and require an explicit
run root. Ambiguity is safer than corrupting another orchestrator's run.


## Resume trust boundary

Compaction does not promote handover prose into technical authority. `HANDOVER.md`
restores continuity, but technical claims remain inherited assertions. Before the
orchestrator repeats/escalates/builds a new plan-wide decision on such a claim,
follow its cited governing/accepted evidence or route the predicate to a worker.
`verify-resume` itself checks governing plan-reference, authority-index, effective
configuration, and recorded plan-source identity against the checkpoint; it fails
closed on drift. Mutable task/worker state is intentionally revalidated separately.
State/run identity and helper-produced mechanical facts retain their normal
control-plane authority after a clean resume verification.
