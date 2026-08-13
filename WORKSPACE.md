# DSD Workspace Contract

Cold reference for state/evidence/recovery/concurrency/barriers. Normal tasks use `dsd_attempt.py` without repeatedly loading this file.

## Run layout

```text
DeepSeekAndDestroy/plans/<plan-id>/runs/<run-id>/
  manifest.json
  state.json
  plan-reference.md
  authority-index.json
  effective-configuration.md
  HANDOVER.md
  major-findings-and-fixes.md
  worker-rules/rNNNN/{WORKER_RULES.md,MANIFEST.json,protocol/...}
  phases/<phase>/
    phase-snapshot-*.json
    tasks/<task>/
      contracts/rNNNN.md
      attempts/<role>-<n>/
        launch-prompt.txt
        report.md
        worker.log
        scope-baseline.json
        scope-diff.json
        launch-reservation.json
        attempt.json
        terminal.json
        evidence-gate.json
```

New attempt evidence is self-contained. Run files are orchestration evidence, not project source.

## Authority / immutability

Current user instructions and governing project/plan authority define semantics. `state.json` is authoritative for **current execution reality**; immutable task/rules/attempt/gate artifacts prove what actually ran. HANDOVER/chat/progress are optional continuity aids only. If HANDOVER disagrees with live state about the active task/attempt/`next_action`, live state wins.

Once consumed by a launch, worker-rules revisions, task contracts, prompt/reservation/baseline bindings, terminal events, gates, and accepted semantic evidence are immutable. New meaning gets a new numbered artifact.

## Minimal state

State records facts, not routing heuristics. Per task retain the current contract, current attempt/gate, bounded `last_attempt`, status, and accepted evidence bindings. `semantic_report` points to the Reviewer report consumed directly or the optional Clerk report. Do not store regex verdicts, `next_role`, transport counters, dependency prose, or no-progress heuristics.

At run level keep execution status, one exact `next_action`, worker-rules/runtime binding, optional wait/availability state, and checkpoint state. Use `dsd_state.py`; do not hand-patch routine transitions. `check_state.py` validates objective consistency only.

## Attempt lifecycle

`dsd_attempt.py launch` resolves run-root authority, preflights the prior attempt, allocates/captures/renders, starts the detached monitor, and binds the new live attempt immediately; foreground mode then waits cheaply inside the helper. A later role moves the prior terminal attempt to bounded `last_attempt`.

No terminal event blocks normal relaunch. Recovery may use `--supersede-incomplete` only after establishing the old worker cannot still write; history records `lifecycle-incomplete`/`superseded`, never a fake exit.

`terminal.json` proves lifecycle end, not semantic correctness. A terminal attempt without usable report gates to `report-recovery`. `gate` stores objective integrity and may bind current or archived attempts; worker prose is omitted unless `--surface` is requested.

A clean gate means **safe to interpret**, never semantic PASS.

## Scope

Every attempt compares project paths/content against task start.

- read-only role: any project movement fails integrity;
- Implementer/Fixer: movement must remain inside exact `Allowed source changes`;
- Verification: read-only unless its contract explicitly grants generated/project write paths;
- Evidence Clerk and other specialists: project-read-only.

Git-ignored but load-bearing roots belong in task `Extra scope inventory`; baseline/diff recursively detect additions/removals/modifications there. Scope proves movement, not semantic validity. Content/path evidence outranks timestamps.

## Interrupted/reportless work

If a worker started but ends without trustworthy usable report evidence:
1. establish that no writer can still mutate project state;
2. preserve the immutable attempt;
3. run objective scope comparison;
4. source movement is **suspect changes**, never “nothing happened”;
5. use Recovery for technical disposition; Clerk only interprets existing report material;
6. any adopt/repair/revert/quarantine is an explicitly authorized writer task followed by fresh review.

Never blindly rerun over unknown interrupted writes.

## Worker rules / semantic evidence

`prepare_worker_rules.py` freezes run facts + worker doctrine into immutable `worker-rules/rNNNN/`; every attempt binds its exact revision/hash. Workers load only run facts + Common + one role + task; proof recipes only when explicitly named.

Python never decides whether long prose proves requirements or means PASS/FAIL. At a parent decision boundary, request a bounded report surface; if that is insufficient, run one always-read-only Evidence Clerk over the exact contract/report/gate. Missing technical proof goes to targeted Verification/Review. The parent decides.

Every project mutation requires **fresh Reviewer provenance** before acceptance. Python may enforce that provenance fact only; it does not judge the review. A Fixer never validates its own repair; role changes use fresh contexts.

## Phase barrier

A phase audit must describe one frozen source state:

```text
finish phase writers
→ close barrier + capture source snapshot
→ required read-only post-barrier Verification
→ fresh Phase Auditor
→ parent phase decision
```

Any phase-owned mutation reopens the barrier and invalidates prior post-barrier Verification/Audit. The barrier protects concurrency/state identity; it does not decide semantic phase success.

## Concurrency / waiting / availability

Run directories isolate orchestration history, not source writes. Concurrent orchestrators with overlapping write scope need separate worktrees/branches or explicitly disjoint scopes. If attribution becomes unsafe, stop launching writers until ownership is resolved.

Waiting is quiescent. Do not use model turns to poll logs/CPU/repository. Provider/quota/auth failure is infrastructure state, not permission for the premium parent to become the implementation worker. Preserve suspect writes before retrying post-start failures.

## Resume

A fresh parent first identifies the exact run using explicit binding or minimal candidate `state.json` metadata, then reads the chosen live `state.json`. Do not inspect git history, session notes, historical reports, old contracts, or project architecture merely because the parent session changed.

Execute a mechanically self-contained `next_action` immediately. If the next action requires judgment, read only the decision/evidence/authority pointers needed for that decision. HANDOVER is cold continuity context, not a prerequisite for routine resume.

When several active runs remain genuinely ambiguous, require exact `DSD_RUN_ROOT`/user authority; never infer ownership from broad archaeology. When ownership is explicitly transferred, do not leave the superseded run presented as the current run. Checkpoint details are in `COMPACTION.md`.

## Major log

`major-findings-and-fixes.md` records only serious defects/root causes, consequential decisions, major fixes, accepted residuals, and genuine availability/human blocks with evidence links. It is not a transcript. When the parent makes a consequential decision, record a **brief durable decision** there before delegating the follow-on task; later `next_action`/contracts should point to that decision instead of reconstructing it.
