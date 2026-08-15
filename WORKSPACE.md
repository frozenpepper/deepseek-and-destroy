# DSD Workspace Contract

Cold reference for state/evidence/recovery/concurrency. Normal tasks use `dsd_attempt.py` without repeatedly loading this file.

## Run layout

```text
DeepSeekAndDestroy/plans/<plan-id>/runs/<run-id>/
  state.json
  plan-reference.md
  authority-index.json
  effective-configuration.md
  HANDOVER.md
  major-findings-and-fixes.md
  worker-rules/rNNNN/{WORKER_RULES.md,MANIFEST.json,protocol/...}
  phases/<phase>/
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

`state.json` is authoritative for **current execution reality**; immutable task/rules/attempt/gate artifacts prove what ran. HANDOVER/chat/progress are optional continuity only and never override live task/attempt/`next_action`.

Once consumed by a launch, worker-rules revisions, task contracts, prompt/reservation/baseline bindings, terminal events, gates, and accepted semantic evidence are immutable. New meaning gets a new numbered artifact.

## Minimal state

State records facts, not routing heuristics. Active tasks keep the contract plus current/bounded prior attempt facts; accepted tasks keep only contract, accepted evidence bindings, and status. Detailed lifecycle stays cold in attempt directories. Do not store regex verdicts, routing counters, dependency prose, or no-progress heuristics.

At run level keep execution status, one exact `next_action`, worker-rules/runtime binding, active wait state, and checkpoint state. Use `dsd_state.py`; do not hand-patch routine transitions. `check_state.py` validates objective consistency only.

## Attempt lifecycle

`dsd_attempt.py launch` resolves run-root authority, preflights the prior attempt, allocates/captures/renders, starts the detached monitor, and binds the new live attempt immediately; foreground mode then waits cheaply inside the helper. A later role moves the prior terminal attempt to bounded `last_attempt`.

No terminal event blocks normal relaunch. Recovery may use `--supersede-incomplete` only after establishing the old worker cannot still write; history records `lifecycle-incomplete`/`superseded`, never a fake exit.

`terminal.json` proves lifecycle end, not semantic correctness, and binds both the exact report bytes/state and compact scope diff observed immediately after worker return; later gates reuse that evidence instead of re-reading mutable artifacts/worktree state. A terminal attempt without usable report gates to `report-recovery`; worker prose is omitted unless `--surface` is requested.

A clean gate means **safe to interpret**, never semantic PASS.

## Scope

Every attempt records a compact factual project diff at terminal. New Git attempts baseline only dirty/untracked paths plus explicitly named ignored roots, then hash only paths that could have changed; historical full-worktree snapshots remain readable.

- read-only role: any project movement fails integrity;
- Implementer/Fixer: choose their implementation surface; if authority supplied `Allowed source changes`, that explicit boundary is enforced;
- Verification: read-only unless its contract explicitly grants generated/project write paths;
- Evidence Clerk and other specialists: project-read-only.

`Extra scope inventory` is optional for already-known ignored/load-bearing roots; do not discover paths merely for DSD. Scope records movement, not whether the engineering change was appropriate—that belongs to fresh Review.

## Interrupted/reportless work

If a started worker ends without usable report evidence, first establish that no writer remains live and preserve the attempt. Any recorded movement is **suspect**; use Recovery for disposition, not Clerk. Adoption/repair/revert/quarantine is a normal writer task followed by fresh review. Never blindly rerun over unknown interrupted writes.

## Worker rules / semantic evidence

`prepare_worker_rules.py` freezes run facts + worker doctrine into immutable `worker-rules/rNNNN/`; every attempt binds its exact revision/hash. Workers load only run facts + Common + one role + task; proof recipes only when explicitly named.

Python never decides whether long prose proves requirements or means PASS/FAIL. At a parent decision boundary, request a bounded report surface; if that is insufficient, run one always-read-only Evidence Clerk over the exact contract/report/gate. Missing technical proof goes to targeted Verification/Review. The parent decides.

Every project mutation requires **fresh Reviewer provenance** before acceptance. Python may enforce that provenance fact only; it does not judge the review. A Fixer never validates its own repair; role changes use fresh contexts.

## Phase close

Finish phase mutations, exercise finalization operations, freeze the intended final state, run fresh read-only Verification and a fresh Phase Auditor, then make the parent phase decision. Any later mutation makes that phase evidence stale and requires fresh verification/audit; no separate barrier state machine exists.

## Concurrency / waiting / availability

Assume one intentional project writer per checkout. DSD does not implement file locking or require the parent to pre-plan disjoint write scopes. If another writer is discovered and attribution becomes unsafe, stop writers until ownership is resolved or use an isolated worktree.

Waiting is quiescent. Do not use model turns to poll logs/CPU/repository. Provider/quota/auth failure is infrastructure state, not permission for the premium parent to become the implementation worker. Preserve suspect writes before retrying post-start failures.

## Resume

A fresh parent identifies the run from explicit binding/minimal `state.json` metadata and reads live state first—never broad git/session/report/contract archaeology merely because the parent changed. Execute mechanical `next_action` immediately; for judgment, read only its named decision/evidence/authority. HANDOVER is cold continuity only.

For normal resume, exact run/session identity wins; parent-harness ownership may disambiguate otherwise stale active runs. If ambiguity remains genuine, do not mutate a guessed run. Compaction itself must still proceed. Checkpoint details are in `COMPACTION.md`.

## Major log

`major-findings-and-fixes.md` records only serious defects/root causes, consequential decisions, major fixes, accepted residuals, and genuine availability/human blocks with evidence links. It is not a transcript. When the parent makes a consequential decision, record a **brief durable decision** there before delegating the follow-on task; later `next_action`/contracts should point to that decision instead of reconstructing it.
