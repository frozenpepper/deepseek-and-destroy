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

Current user instructions and governing project/plan authority define semantics. `state.json` records execution reality; immutable task/rules/attempt/gate artifacts prove what actually ran. HANDOVER/chat/progress are continuity aids only.

Once consumed by a launch, worker-rules revisions, task contracts, prompt/reservation/baseline bindings, terminal events, gates, and accepted semantic evidence are immutable. New meaning gets a new numbered artifact.

## Minimal state

State records facts, not routing heuristics. Per task retain contract, current attempt/gate, bounded `last_attempt` pointer, status, and accepted evidence bindings:

```json
{
  "status": "accepted",
  "current_contract": {"revision": 3, "path": "...", "sha256": "..."},
  "last_attempt": {"role": "implementer", "attempt": 1, "event_dir": "...", "status": "gated", "integrity_gate": {"path": "...", "sha256": "..."}},
  "current_attempt": {
    "role": "reviewer", "attempt": 1, "event_dir": "...",
    "launch_reservation": "...", "launch_reservation_sha256": "...",
    "terminal_event": "...", "writes_project": false
  },
  "accepted": {
    "source_gate": {"path": "...", "sha256": "..."},
    "semantic_report": {"path": "...", "sha256": "..."},
    "semantic_gate": {"path": "...", "sha256": "..."}
  }
}
```

`semantic_report` is the Reviewer report when the parent consumed it directly, or a Clerk report when compression was useful. Do not store regex verdicts, `next_role`, transport counters, dependency prose, or no-progress heuristics.

At run level keep execution status, one exact `next_action`, worker-rules/runtime binding, optional availability/wait state, and checkpoint state. Use `dsd_state.py`; do not hand-patch routine transitions. `check_state.py` validates objective consistency only.

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

A fresh parent starts from `state.json`, exact `next_action`, current contract/attempt/gate, relevant plan/authority reference, and only accepted semantic evidence needed for the next decision. Do not reread all historical reports/project architecture merely because the session changed.

When several runs are active, require exact `DSD_RUN_ROOT`/user authority; never guess. Checkpoint details are in `COMPACTION.md`.

## Major log

`major-findings-and-fixes.md` records only serious defects/root causes, consequential decisions, major fixes, accepted residuals, and genuine availability/human blocks with evidence links. It is not a transcript and does not duplicate routine reports.
