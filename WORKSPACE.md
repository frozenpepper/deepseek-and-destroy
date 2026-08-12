# DSD Workspace / Recovery Reference

Load this only for state, provenance, recovery, or phase-barrier work. `SKILL.md` owns
normal execution policy.

## Durable layout

```text
DeepSeekAndDestroy/plans/<plan>/runs/<run>/
  state.json
  run-manifest.md
  authority-index.json
  plan/...
  worker-rules/rNNNN/{WORKER_RULES.md,MANIFEST.json,protocol/...}
  major-findings-and-fixes.md
  phases/<phase>/<task>/
    contracts/rNNNN.md
    attempts/<role>-<n>/
      prompt.txt
      scope-baseline.json
      launch-reservation.json
      attempt.json
      report.md
      worker.log
      terminal.json
      scope-diff.json
      evidence-gate.json
  compactions/...
```

New attempts are self-contained. Historical v15 layouts with role reports outside the
attempt directory remain readable by low-level helpers.

OpenCode worker databases live outside the project tree (`OPENCODE.md`). Run namespaces
prevent DSD-artifact collisions; concurrent project writers still need disjoint ownership
or separate worktrees.

## Mutability / authority

Mutable control: `state.json`, current HANDOVER/continuity prose, current contract only
before first launch. Append-oriented: major findings/out-of-scope defect logs. Immutable
after launch/terminal as applicable: snapshotted rules, launched contracts/prompts,
reservations, lifecycle events, scope baselines/diffs, terminal reports, gates, accepted
Clerk/audit packets.

`state.json` + exact immutable accepted evidence are execution authority. HANDOVER,
progress prose, old chat, and summaries are continuity claims.

## Minimal state expectations

State records:

- project/run/plan identity and authoritative plan reference/hash;
- current immutable worker-rules revision;
- parent harness + worker runtime/model/external DB;
- execution status and one exact `next_action`;
- per phase: status + write-barrier state/snapshot;
- per task: status/dependencies, current contract path/hash/revision,
  `decomposition_required`, zero-change streak, next role, and current/last attempt;
- active attempt: role/number, event dir, reservation path/hash, terminal path,
  liveness identity, and whether it writes project state;
- worker availability/backoff and context checkpoint when active.

Use `check_state.py`; use `dsd_state.py` for routine `bind-contract`, `bind-attempt`,
`accept`, and `set-next` transitions. The helper validates a candidate before atomic
replacement. Do not build a generic state patch API.

`dsd_state.py accept` verifies the referenced **mechanical** evidence gate is clean; the
parent must supply/own the semantic verdict/acceptance decision.

## Attempt authority

`launch-reservation.json` is the single immutable attempt identity. It binds task id,
role/attempt number, report/log, prompt + hash, contract + hash, worker rules/manifest +
hashes, scope baseline + hash, and reservation time. Lifecycle events bind back to it.
Worker-authored Role/Task prose is never identity authority.

A role change starts a fresh worker session. Same-role session continuation is only for
a trustworthy transport continuation. Pass durable prior evidence paths rather than chat
history; `dsd_attempt.py launch --evidence` embeds their path+hash in the prompt.

## Scope facts

Every attempt baseline covers tracked + untracked-nonignored Git worktree content,
excluding only `DeepSeekAndDestroy/`. Contract `Extra scope inventory` adds ignored but
load-bearing roots (locks/freezes/runtime roots); compare re-enumerates additions,
removals, and modifications there too. Symlinks are hashed as links, never followed to
external targets.

Mechanical gate behavior:

- writer: changed project paths must be inside exact `Allowed source changes`;
- read-only role: any project movement is `READONLY-SCOPE-MOVED` and requires Recovery,
  never semantic normalization;
- baseline/reservation/hash/transport corruption is a hard mechanical failure;
- missing/unchanged report after completed transport is evidence-availability trouble,
  not a semantic FAIL and not a reason to rerun a long worker automatically.

Inventory proves movement, not artifact correctness. Non-Git projects need an explicitly
configured equivalent scope mechanism; do not pretend the Git gate applied.

## Meaning / Clerk

`evidence_gate.py` deliberately does **not** parse verdicts, AC coverage, Proof Matrices,
defect prose, arithmetic, or report Markdown. `report_surface.py`/`dsd_attempt gate`
may extract a bounded preview but that preview is non-authoritative.

Evidence Clerk is project-read-only and may interpret/compress exact existing evidence.
Use it when the parent-facing report is long/awkward/ambiguous or AC mapping is expensive.
Give it the source report + mechanical gate (and exact-attempt log only when report
recovery is needed). Clerk cannot run missing technical proof, repair, approve, waive
mechanical failures, or recurse. Missing substance becomes one targeted specialist task.

## Reportless / interrupted recovery

If no trustworthy report exists after work began:

1. confirm the worker/monitor can no longer mutate state;
2. preserve terminal/lifecycle/log/scope evidence;
3. if mechanical scope is trustworthy and the exact log/evidence contains the semantic
   result, let one Clerk interpret it without altering project state;
4. if project changes are partial/ambiguous/untrusted, launch read-only Recovery;
5. Recovery recommends adopt-for-fresh-review, revert, quarantine, or specific missing
   evidence; it does not perform the disposition;
6. any disposition that mutates the project is a normal bounded writer task followed by
   fresh review.

Never infer "no changes" from a forced exit. Never let Clerk convert project-scope drift
into acceptance.

## Two-zero-change / revalidation

Two consecutive substantial Implementer/Fixer attempts with zero intended changes and no
proof the task was already satisfied set `decomposition_required=true`; no third writer
until rediscovery/splitting/rescoping or a materially revised contract resolves why.

If an accepted prerequisite materially changes, mark dependents `needs-revalidation`.
Cheap bounded revalidation yields still-valid or superseded; old PASS does not survive a
changed premise automatically.

## Phase write barrier

Before whole-phase audit:

1. finish and mechanically gate every phase-owned writer, including mutating Verification;
2. close the barrier and capture the frozen project snapshot;
3. run required post-barrier Verification read-only (or isolated outside accepted state);
4. run fresh Phase Auditor against the same frozen state;
5. parent adjudicates phase authority + compact audit evidence;
6. remediation is new bounded tasks;
7. any accepted-state mutation reopens the barrier and invalidates stale post-barrier
   verification/audit evidence.

`check_state.py` rejects a CLOSED/auditing barrier with an active project-writing attempt.
Writer capability is derived from role + immutable contract, not role prose.

## Waiting / transport / checkpoints

Persist host wait identity before yielding when the parent harness needs it. A wait tool
timeout without a terminal event is a non-event; wait again. If monitor/lifecycle state is
inconsistent, load the active harness adapter and `OPENCODE.md` for diagnostics.

Provider/auth/quota failures are availability/transport problems, never authority for the
premium parent to implement. Use bounded health probes/backoff/fallback.

For compaction, load `COMPACTION.md`. A resume must mechanically re-bind governing
plan/config/authority and separately revalidate any live attempt. Native summaries are
advisory.
