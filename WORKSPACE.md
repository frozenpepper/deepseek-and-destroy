# DeepSeek and Destroy Workspace Contract

`SKILL.md` owns execution policy. This file owns durable run identity, state,
artifacts, evidence provenance, and continuity.

## Layout

```text
DeepSeekAndDestroy/
  plans/<plan-id>/runs/<run-id>/
    run-manifest.md
    state.json
    authority-index.json
    HANDOVER.md
    worker-rules/
      r0001/
        WORKER_RULES.md
        MANIFEST.json
        protocol/
          COMMON.md
          PROOF-PATTERNS.md
          roles/
            implementer/SKILL.md
            fixer/SKILL.md
            reviewer/SKILL.md
            verification/SKILL.md
            discovery/SKILL.md
            phase-surveyor/SKILL.md
            recovery/SKILL.md
            phase-auditor/SKILL.md
            evidence-clerk/SKILL.md
      r0002/ ...
    effective-configuration.md
    major-findings-and-fixes.md
    out-of-scope-defects.md
    plan/
      plan-reference.md
      snapshots/...
    compactions/...
    phases/<phase-id>/
      current-state-audit.md
      phase-audits/
      verification/
      phase-remediation-<n>.md
      <task-id>/
        contracts/
          r0001.md
          r0002.md
        discovery-spec.md
        preservation-baseline.md
        attempts/
          <role>-<n>/
            launch-prompt.txt
            launch-reservation.json
            attempt.json
            scope-baseline.json
            worker.log
            terminal.json
            scope-diff.json
            evidence-gate.json
            evidence-reconciliation.md
        implementer-report-<n>.md
        review-<n>.md
        fix-<n>.md
        verification-<n>.md
        recovery-audit-<n>.md
        verdict.json
```

The visible run tree contains durable orchestration/evidence only. OpenCode SQLite
worker state lives outside every project/worktree path; see `OPENCODE.md`.

## Mutability / provenance contract

**Mutable current control:** `state.json`, `HANDOVER.md`, current plan reference,
current task contract while still being prepared, configured project progress file.

**Append-oriented:** `major-findings-and-fixes.md`, `out-of-scope-defects.md`.

**Immutable after terminal attempt:** worker/reviewer/fixer/verification/recovery
reports, evidence reconciliation reports, launch reservations/lifecycle events,
phase-audit/gate evidence, and preserved scope snapshots used by those artifacts.

Never reopen a terminal report to append newer counts, later findings, gate
decisions, or polish. A later change/review uses a new numbered attempt/report.

## Plan/run identity

Plan id: readable slug + short unique suffix. Run id: collision-resistant semantic
id/timestamp. Run manifest records run/plan ids, orchestrator identity/harness,
project root/worktree/branch, parent/handoff run, creation time, and active/terminal
ownership.

Run directories prevent orchestration-file collisions, not source collisions.
Concurrent writers need disjoint ownership or separate worktrees/branches.

## Authority index / plan snapshots

`plan/plan-reference.md` records authoritative source path, immutable intake
snapshot/hash, whether execution follows live source or snapshot, and later plan
revisions with new hashes/snapshots.

`authority-index.json` records governing source paths, hashes, and compact current
summaries. It accelerates resume but does **not** replace the orchestrator's required
fresh-session reading of governing user/project/plan authority.

## state.json

State describes reality, not intention. Representative shape:

```json
{
  "workspace_root": "DeepSeekAndDestroy",
  "plan_id": "example--7f3a2c",
  "run_id": "20260810T170000Z-opus-a91f",
  "run_root": "DeepSeekAndDestroy/plans/example--7f3a2c/runs/20260810T170000Z-opus-a91f",
  "project_worktree": "/abs/project",
  "plan_reference": "<run-root>/plan/plan-reference.md",
  "plan_source_sha256": "<sha256>",
  "worker_rules": {
    "revision": 2,
    "path": "<run-root>/worker-rules/r0002/WORKER_RULES.md",
    "protocol_dir": "<run-root>/worker-rules/r0002/protocol",
    "sha256": "<sha256>",
    "protocol_fingerprint": "<sha256>",
    "manifest": "<run-root>/worker-rules/r0002/MANIFEST.json",
    "manifest_sha256": "<sha256>"
  },
  "orchestrator": {
    "id": "main",
    "harness": "claude-code",
    "session_id": "...",
    "adapter": "CLAUDE.md"
  },
  "worker_runtime": {
    "harness": "opencode-cli",
    "model": "opencode-go/deepseek-v4-flash",
    "opencode": {
      "run_db": "/external/cache/dsd/<run-id>/workers.db",
      "external_to_project": true,
      "cleanup": "terminal"
    }
  },
  "execution_status": "active",
  "next_action": "wait for phase-1/U2 reviewer terminal event",
  "worker_availability": {
    "status": "available",
    "next_probe_at": null
  },
  "orchestrator_wait": {
    "active": true,
    "kind": "claude-async-rewake",
    "terminal_event": "<task-root>/attempts/reviewer-1/terminal.json",
    "monitor_pid": 48100
  },
  "context_checkpoint": {
    "sequence": 2,
    "status": "resumed",
    "checkpoint_path": "<run-root>/compactions/0002/CHECKPOINT.md",
    "manifest_path": "<run-root>/compactions/0002/resume-manifest.json",
    "continuity_verified": true,
    "preserved_next_action": "wait for phase-1/U2 reviewer terminal event"
  },
  "phases": {
    "phase-1": {
      "status": "in-progress",
      "gate_barrier": {
        "status": "OPEN",
        "snapshot": null
      },
      "tasks": {
        "U2": {
          "status": "in-progress",
          "dependency_status": "valid",
          "current_contract": {
            "revision": 3,
            "path": "<task-root>/contracts/r0003.md",
            "sha256": "<sha256>"
          },
          "decomposition_required": false,
          "zero_intended_change_streak": 0,
          "next_role": "reviewer",
          "transport_attempts": 1,
          "current_attempt": {
            "role": "reviewer",
            "attempt": 1,
            "event_dir": "<task-root>/attempts/reviewer-1",
            "launch_reservation": "<task-root>/attempts/reviewer-1/launch-reservation.json",
            "launch_reservation_sha256": "<sha256>",
            "terminal_event": "<task-root>/attempts/reviewer-1/terminal.json",
            "worker_pid": 48122,
            "session_id": "ses_abc",
            "launched_at": "2026-08-10T17:03:00Z",
            "liveness": "confirmed"
          },
          "last_verdict": null
        }
      }
    }
  }
}
```

## Quiescent wait state

When a detached external worker is handed to a host-native or blocking wait, persist
`orchestrator_wait` before yielding: `active`, wait `kind`, exact `terminal_event`,
and the detached monitor PID when one exists. Clear it as soon as the terminal event
is consumed. `check_state.py --for-turn-exit` rejects an active wait whose terminal
event already exists or whose recorded monitor has died without producing one.
This is a pre-yield consistency check, not periodic polling.

## Attempt states

Minimum lifecycle:

- `prepared` — durable task + launch prompt exist; no process claimed;
- `launching` — launcher started and attempt identity/event path recorded;
- `in-progress` — real worker process/liveness established;
- `waiting-for-worker` — transient provider incident with persisted probe/relaunch;
- `process-exited` — terminal event exists; report/evidence still requires gate;
- `evidence-reconciliation` — Evidence Clerk resolving a flagged discrepancy;
- `accepted` / `reopened` / `needs-revalidation` / `still-valid` / `superseded` /
  `suspect-changes` / `blocked` as applicable.

`in-progress` requires real attempt identity. A planned launch is not a worker.

Before every worker launch, state must contain current plan identity, task/dependency
status, contract revision, decomposition guard, the attempt's launch-reservation
path/hash plus lifecycle event path/identity, and exact `next_action`. Immutable
prompt/rules/baseline/report bindings live once in the reservation, not duplicated
through state.

## Worker-rules revisions

At run initialization, `scripts/prepare_worker_rules.py` creates immutable
`<run-root>/worker-rules/r0001/WORKER_RULES.md`, `MANIFEST.json`, and that revision's `protocol/`
snapshot. Stable environment/project worker rules are paid once here rather than
retyped in every prompt. The snapshot contains universal `COMMON.md`, focused role
`SKILL.md` files, and proof patterns. The manifest binds every file so an old
attempt cannot silently resolve to newer/tampered worker doctrine.

Record the current default revision/path/hash/manifest in state. Each attempt's exact
worker-rules revision is bound by its immutable launch reservation; active state need
not repeat those bindings. `check_state.py` treats mutation of a frozen revision as
an integrity error.
If a newly learned constraint is truly run-wide, create `r0002`, `r0003`, ... and
point later attempts to the new immutable revision; **never rewrite an older
revision**. If the change is task-specific, create a new task-contract revision
instead of growing run-wide rules.

Do not put secrets or changing task details in worker rules.

## Task contract / path-only handoff

Each task has immutable numbered contract revisions under `contracts/`; see
`PROMPTS.md`. The current revision contains only task-specific semantic material:
objective, needed authority/inputs, optional sharp risks, AC/proof contract,
verification, optional Clerk checks/outputs, and always-explicit **`Allowed source
changes`**. Launch-derived report/evidence/lifecycle paths are not duplicated into
the semantic task contract. `state.json.current_contract` records its exact
path/hash/revision. Once launched, that revision is frozen; material changes create
a new revision.

The launch prompt is generated mechanically against the exact frozen contract and
one exact worker-rules revision. Store it under the attempt directory for
recovery/audit. A task may narrow source writes further than its expected semantic
scope; `Allowed source changes` is a mechanical write boundary, never permission
to broaden the objective.

## Scope facts

Before **every terminal worker role** in the built-in Git flow, capture a full
Git-worktree content snapshot immediately before launch, excluding **only**
`DeepSeekAndDestroy/`:

```bash
python3 <skill-root>/scripts/scope_snapshot.py capture \
  --root <project-root> \
  --output <attempt>/scope-baseline.json \
  --git-worktree --exclude-prefix DeepSeekAndDestroy
```

This one baseline serves two different integrity checks:

- Implementer/Fixer (and a Clerk explicitly assigned one project progress/doc
  file): every changed source path must fall under the contract's exact
  `Allowed source changes`; anything else is hard scope drift.
- Reviewer/Verification/Discovery/Survey/Recovery/Phase Auditor: **no** project
  source change is allowed. Any movement is an integrity/recovery event, not a
  clerical discrepancy.

The comparison re-enumerates tracked plus untracked **nonignored** Git paths, so unexpected new/deleted nonignored files are visible. Git-ignored build/cache/generated outputs are not automatically covered; when such an artifact is acceptance-relevant, give it an explicit artifact/verification contract rather than inferring safety from the source-scope gate. Symlinks are hashed by link identity/target string rather than following an external target. `Allowed source changes` never authorizes writing through a project symlink into an external target. The automatic built-in evidence gate currently requires this Git worktree baseline; a non-Git project needs an explicitly configured equivalent mechanical scope gate rather than pretending the built-in fast path applied.

Mechanical baselines are authoritative facts only when the current immutable
contract/state binds the exact artifact/attempt identity. A similarly named stale
baseline from another attempt is not authority. Workers should not recompute a
current bound helper result merely for diligence.

Do not use mtimes or Git status letters as content-preservation proof. Rolling
scope baselines refresh per attempt; behavior-preservation baselines remain
immutable unless authoritative contract intentionally changes. Parent-facing
packets never need per-file hash catalogs; cite the mechanical artifact instead.

## Terminal worker event

`run_worker.py` first creates `launch-reservation.json` and the recognizable report
skeleton, then writes `attempt.json` once the OpenCode child exists and `terminal.json`
when it exits.

`launch-reservation.json` is the **single immutable attempt authority**: it binds
role/attempt plus exact report/log, launch prompt, task contract, worker-rules
snapshot/manifest, scope baseline, and their hashes. `attempt.json`/`terminal.json`
are lifecycle records that bind back to the reservation by path/hash instead of
repeating all authority. `evidence_gate.py` rechecks the reservation before consuming
worker claims. Historical v14 terminal records remain readable.

`terminal.json` is the portable terminal event. For an external worker it is emitted
after the actual child process exits; for a supported native worker it is finalized
after the native Task tool returns. Under the Worker Rules
**no-background-writer invariant**, child-process exit is the no-more-task-writes
boundary for that attempt. If a worker violates the invariant by leaving a writer
behind, terminal evidence is invalid and recovery is mandatory. **Terminal does not
mean successful:** classify its status first.

- `completed` + exit 0 → eligible for the evidence gate;
- `process-error` after the OpenCode child started → `suspect-changes` / recovery
  path, because partial edits may exist even if the report is a skeleton;
- `transport-error` before a worker was established → transport/availability
  handling; do not launch a Clerk merely because the safe report skeleton remains.

The orchestrator harness may receive a native wake signal before reading this event,
but `terminal.json` remains the durable evidence.

## Evidence gate

Only after a successful terminal event, and before interpreting its report, run
`evidence_gate.py`.

It checks structural/mechanical predicates only. It may write a scope diff. Results:

- **CLEAN** (exit 0) — terminal evidence is mechanically consumable;
- **FAIL** (exit 1) — non-waivable integrity/semantic contradiction; route repair or
  recovery as appropriate;
- **CLERK REQUIRED** (exit 4) — clerical/provenance normalization is required; do not
  resolve it in premium context. Gate the Clerk attempt first, then re-gate the
  originating attempt with the matching clean Clerk report/gate overlay.

Typical Clerk triggers: missing/unchanged canonical report requiring exact-attempt
recovery, noncanonical FINAL/report formatting (`RC-002`), Reviewer proof that needs
canonical AC normalization (`RC-001`), provenance/tripwire checks, inconsistent
verification arithmetic, or a worker-declared clerical check. **Project source
movement is never a Clerk reconciliation:** read-only movement or changes outside
`Allowed source changes` are hard integrity failures and enter recovery.

The Evidence Clerk writes `evidence-reconciliation.md`; the orchestrator still owns
the task verdict/state transition. Capture the same full worktree baseline before
Clerk launch, excluding only `DeepSeekAndDestroy/`. If Clerk is explicitly
authorized to maintain one project progress/documentation file, that exact path
must be in `Allowed source changes`; product source/tests remain read-only. The
Clerk task must not request another Clerk. A CLEAN Clerk overlay may normalize only
its named clerical check IDs; it cannot invent a missing role verdict/semantic proof
or waive source-scope/authority integrity. Missing/unchanged canonical reports must
actually be recovered to the canonical path before re-gate can pass.

## Decision Packets

Parent reads the Decision Packet by default. `decision_packet.py` extracts it.
Full reports/raw logs are cold evidence opened only for a named contradiction that
cannot be resolved from the packet + reconciliation + exact cited slice.

Reviewer fast-path is **derived by the evidence gate**, never declared by the
worker. Canonical Proof Matrix coverage passes directly; equivalent noncanonical
per-AC evidence routes through Clerk normalization before fast-path can become true.

If one orchestrator decision would need >3 substantive deep evidence/source slices,
commission a bounded compression brief instead of loading a dossier.

## Handover trust / currency

`HANDOVER.md` is compact continuity, not a technical authority or second log.
Update it when resume semantics materially change: user/plan revision, phase/
remediation transition, reopened prerequisite/supersession, consequential harness/
architecture quirk, material correction, blocker, compaction/session handoff.

Technical claims in HANDOVER must cite primary/accepted evidence whenever they may
matter later. On resume, treat uncited technical claims as inherited assertions, not
established facts.

Routine task transitions need not rewrite handover narrative when state already
captures them.

The Evidence Clerk may maintain HANDOVER when explicitly assigned. `state.json`
remains orchestrator-owned.

## Major findings / progress

`major-findings-and-fixes.md` stores durable material engineering knowledge:
serious defects, non-obvious root causes, consequential fixes/decisions, material
corrections, availability incidents, and phase remediation/human escalation.

Technical entries should be written by the worker closest to trustworthy evidence
or by the Evidence Clerk. The orchestrator should not spend premium tokens writing
long technical summaries. It may add concise plan-wide decision entries.

A project progress file may be updated by Evidence Clerk only when its exact path is
configured/assigned. Never let a clerk roam for arbitrary progress files.

## Two-zero-change guard

Track `zero_intended_change_streak`. After two consecutive substantial mutating
attempts against the same contract produce zero intended changes and do not prove
already-satisfied behavior:

- set `decomposition_required: true`;
- no third mutating launch is valid;
- split/re-scope/Discovery/construction brief first;
- a materially revised contract creates the next immutable revision and may clear the guard with recorded reason.

`check_state.py` enforces the launch-side guard.

## Reopened prerequisites

Materially changed accepted prerequisites put dependents in `needs-revalidation`.
Cheap bounded revalidation yields `still-valid` or `superseded`. Do not silently
continue stale contracts.

## Reportless/forced worker recovery

If worker ends without a trustworthy canonical report after work began:

1. mark `suspect-changes`;
2. confirm terminal process event/no further writes;
3. capture mechanical scope evidence;
4. if expected report is unchanged skeleton/missing, Evidence Clerk inspects only exact-attempt log/output paths and may recover one unambiguous complete report;
5. use Recovery Auditor for non-obvious source disposition;
6. orchestrator chooses adopt-for-review/quarantine/revert/additional evidence;
7. only then relaunch/split.

“No report” never means “no changes.” A skeleton's pre-filled FAIL/BLOCKED text is
not a substantive verdict.

## Phase write barrier

The phase barrier closes only after **all phase-owned writers are terminal**,
including any Verification Worker whose assigned check generates or mutates an
accepted project artifact. Such verification belongs before closure (or must write
only to an isolated temporary location outside accepted project state).

Barrier sequence:

1. all implementation/fix/generated-artifact writers terminal and individually
   evidence-gated;
2. all required artifact-mutating verification writers terminal;
3. capture the phase mechanical snapshot/fingerprint and set
   `gate_barrier.status = CLOSED`;
4. run only read-only post-barrier verification/audit/Phase Auditor work against
   that frozen state;
5. the orchestrator decides from the Phase Auditor packet and governing authority.

Any later phase-owned mutation immediately sets the barrier OPEN and invalidates
post-barrier audit/gate evidence produced against the prior snapshot. Repairs use
new numbered evidence and the barrier must be re-closed. Discovery of a lingering
background/task-owned writer after terminal completion is an integrity incident: the terminal
no-more-writes assumption was false, so recover/re-establish evidence before
gating.

## Context checkpoints

Follow `COMPACTION.md`. Each checkpoint is immutable. While checkpoint status is `prepared`, `compacting`, or `rehydration-required`, do
no project work. Rehydrate, run `verify-resume` to mechanically validate governing
plan/config/authority continuity, separately revalidate live worker lifecycle, then
execute the preserved `next_action` immediately.
