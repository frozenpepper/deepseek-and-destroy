# DeepSeek and Destroy Workspace Contract

`SKILL.md` owns orchestration policy. This file defines durable run identity,
state, concurrency, evidence, recovery, and continuity.

## Workspace layout

Use one visible project-root workspace:

```text
DeepSeekAndDestroy/
  plans/
    <plan-id>/
      runs/
        <run-id>/
          run-manifest.md
          state.json
          authority-index.json
          HANDOVER.md
          effective-configuration.md
          major-findings-and-fixes.md
          out-of-scope-defects.md
          plan/
            plan-reference.md
            snapshots/
              0001-intake-...
              0002-...
          compactions/
            LATEST
            0001/
              CHECKPOINT.md
              resume-manifest.json
              state.snapshot.json
              HANDOVER.snapshot.md
              plan-reference.snapshot.md
              authority-index.snapshot.json
          phases/
            <phase-id>/
              current-state-audit.md
              phase-audit.md
              phase-audits/
              phase-remediation-1.md
              verification/
              <task-id>/
                task.md
                discovery-spec.md
                scope-baseline.json
                scope-diff.json
                preservation-baseline.md
                implementer.log
                implementer-report.md
                verification-report.md
                review-1.md
                fix-1.md
                review-2.md
                recovery-audit.md
                verdict.json
```

The run directory is the mutable source of truth for that execution's **durable
orchestration artifacts**. Harness runtime state is separate. In particular,
OpenCode worker SQLite files must live outside the repository/project/worktree;
see `OPENCODE.md`.

## Plan and run identity

### Plan id

Use a readable slug plus short unique suffix. Reuse an existing plan grouping only
when its recorded canonical source path clearly refers to the same authoritative
plan. Duplicate groups are safer than merging unrelated histories.

### Run id

Every new orchestrator execution gets a collision-resistant run id, e.g.
`<UTC timestamp>-<orchestrator-label>-<short-random>` unless explicitly resuming an
existing run.

### Run manifest

Record:

- run id / plan id;
- orchestrator identity and harness;
- creation time and status;
- project root/worktree/branch;
- parent/handoff run when applicable;
- active/paused/completed ownership.

Do not edit another active run's files.

## Source-code concurrency

Run folders prevent orchestration-artifact collisions, not source collisions.
Concurrent orchestrators that may edit overlapping files need separate VCS
worktrees/branches or explicitly disjoint scopes.

Before relaunching a task/role, reconcile any possibly-live prior worker. A duplicate
launch on the same task/role is an incident: do not let two workers race on the
same source tree merely because one PID/session record was malformed.

## Plan reference and immutable snapshots

`plan/plan-reference.md` records:

- authoritative plan path/source;
- intake snapshot path and hash;
- intake time/orchestrator;
- whether execution follows live source or stored snapshot;
- every later plan revision with old/new hashes, reason, time, and new immutable
  snapshot.

Never overwrite plan snapshots. On resume or when a plan change is noticed, compare
current source to recorded hash before new worker work. Classify impact on current
scope, proof obligations, dependencies, and accepted work.

## state.json

State describes reality, never intention. A representative structure:

```json
{
  "workspace_root": "DeepSeekAndDestroy",
  "plan_id": "example-plan--7f3a2c",
  "run_id": "20260809T120000Z-orchestrator-a91f",
  "run_root": "DeepSeekAndDestroy/plans/example-plan--7f3a2c/runs/20260809T120000Z-orchestrator-a91f",
  "run_manifest": "<run-root>/run-manifest.md",
  "plan_reference": "<run-root>/plan/plan-reference.md",
  "authoritative_plan_path": "DOCS/Plans/example.md",
  "plan_snapshot": "<run-root>/plan/snapshots/0001-intake-example.md",
  "plan_source_sha256": "<sha256>",
  "project_worktree": "/abs/project/worktree",
  "orchestrator": {
    "id": "main-orchestrator",
    "harness": "claude-code",
    "session_id": "abc123",
    "adapter": "CLAUDE.md"
  },
  "worker_runtime": {
    "opencode": {
      "storage_scope": "run",
      "run_db": "/external/cache/DeepSeekAndDestroy/opencode/<run-id>/workers.db",
      "external_to_project": true,
      "cleanup": "terminal"
    }
  },
  "execution_status": "active",
  "terminal_condition": null,
  "next_action": "launch phase-1-task-2 reviewer round 1",
  "worker_availability": {
    "status": "available",
    "last_incident": null,
    "next_probe_at": null
  },
  "context_checkpoint": {
    "sequence": 2,
    "status": "resumed",
    "checkpoint_path": "<run-root>/compactions/0002/CHECKPOINT.md",
    "manifest_path": "<run-root>/compactions/0002/resume-manifest.json",
    "continuity_verified": true,
    "preserved_next_action": "launch phase-1-task-2 reviewer round 1"
  },
  "phases": {
    "phase-1": {
      "status": "in-progress",
      "tasks": {
        "phase-1-task-2": {
          "status": "in-progress",
          "dependency_status": "valid",
          "transport_attempts": 1,
          "current_attempt": {
            "role": "reviewer",
            "attempt": 1,
            "pid": 48122,
            "session_id": "ses_abc",
            "launched_at": "2026-08-09T12:03:00Z",
            "log_path": "<task-root>/run-reviewer-1.log",
            "report_path": "<task-root>/review-1.md",
            "liveness": "confirmed"
          },
          "last_verdict": null,
          "proof_contract_status": "required",
          "review_independence": "independent"
        }
      }
    }
  }
}
```

OpenCode DB paths are run-level runtime state, not per-worker project artifacts.

## State transitions

Minimum attempt states:

- `prepared` — audited task/prompt exists; no worker claimed;
- `launching` — transport actually started and real identity is recorded;
- `in-progress` — positive liveness confirmed;
- `waiting-for-worker` — transient provider incident with persisted next probe and
  relaunch action;
- `process-exited` — worker actually exited/completed; report still may need
  validation;
- evidence/verdict state after final report and post-exit scope capture.

Task/dependency lifecycle may additionally use:

- `accepted`;
- `reopened`;
- `needs-revalidation`;
- `still-valid`;
- `superseded`;
- `suspect-changes`;
- `blocked`.

`in-progress` requires a real transport attempt and either a live confirmed worker
identity or a complete role report proving the attempt ran. Never mark it based on
a planned spawn.

## State and HANDOVER currency

Before every worker launch, `state.json` must reflect:

- current plan hash;
- phase/task/remediation cycle;
- accepted/reopened/needs-revalidation/superseded dependencies;
- currently live worker identity, if any;
- report/log/session/runtime paths;
- exact next action.

Stale state is a launch blocker.

`HANDOVER.md` is a compact continuity packet, not a second log. Update it whenever
resume semantics materially change:

- new user instruction or plan revision;
- phase/remediation transition;
- reopened prerequisite or task supersession;
- consequential architecture/harness quirk;
- material correction;
- blocker;
- compaction/session handoff.

Routine task transitions need not rewrite narrative if state and existing handover
remain accurate. HANDOVER must never contradict state.

## Reopened prerequisites

When a prerequisite is reopened or materially corrected, dependent work becomes
`needs-revalidation` before continuation.

A bounded cheap worker or clear mechanical dependency check determines:

- `still-valid` — changed prerequisite does not invalidate contract/proof
  assumptions;
- `superseded` — old task contract/proof assumptions are invalid; create a
  replacement task.

Never continue a stale dependent contract merely because its task file already
exists.

## Authority index and resume fast path

`authority-index.json` records governing file paths, hashes, and compact summaries.

On resume, first read:

- `HANDOVER.md`;
- `state.json`;
- `plan-reference.md`;
- latest checkpoint when relevant;
- Decision Packets needed for the next decision.

Compare hashes mechanically. Re-read only changed, missing-summary, contradictory,
or decision-critical authority. Do not reload the full unchanged corpus merely
because the orchestrator session changed.

## Context checkpoints

Follow `COMPACTION.md`. Each checkpoint is immutable. While checkpoint status is
`prepared`, `compacting`, or `rehydration-required`, do no project work. Rehydrate,
verify run/plan/worktree/worker identity, run `verify-resume`, then execute the
preserved next action immediately.

## Task artifacts and proof contracts

Every meaningful task acceptance criterion uses a stable `AC-*` id. Non-trivial
behavioral tasks include `## Proof Obligations` in `task.md` or a referenced
Discovery spec.

Reviewer reports include:

- `## Decision Packet`;
- `## Proof Matrix` with one row per task AC;
- detailed evidence/findings;
- literal verdict marker.

The Decision Packet contains at minimum:

- role/task/status/verdict;
- changed/read-only scope;
- criteria/proof summary;
- verification summary;
- scope/preservation result;
- `TASK-RELEVANT DEFECTS: NONE|<ids>`;
- major-log ids;
- risks/blockers;
- evidence paths;
- `FAST-PATH ELIGIBLE: YES|NO` and reason.

Use `scripts/check_review_contract.py` as a **structural** validator. It checks AC
coverage and internal fast-path consistency; it does not judge semantics.

## Scope baseline and preservation

Before each mutating worker attempt, capture a fresh per-attempt content-hash scope
baseline against the immediately previous accepted tree. Record expected existing
and new paths plus enough broader inventory to detect undeclared edits.

Do not use mtimes or Git status letters as content stability proof. Rolling scope
baselines refresh after accepted mutations; behavior-preservation baselines remain
immutable unless the authoritative contract intentionally changes through the
normal plan process.

## Reportless-worker recovery

If a worker exits without trustworthy completion after beginning work:

1. mark task `suspect-changes`;
2. confirm process/session can no longer write;
3. capture before/after content evidence;
4. commission a fresh Recovery Auditor for non-obvious changes;
5. classify complete/partial/unrelated/undeclared/preservation-moving changes;
6. orchestrator chooses adopt-for-review, quarantine, revert, or additional
   evidence;
7. refresh state/survey as necessary;
8. only then retry/split/relaunch.

“No report” never means “no changes.”

## Decision Packets and evidence loading

Read the Decision Packet first. Full reports/raw logs/code/large artifacts are cold
evidence opened only when the packet is malformed/inconsistent, evidence conflicts,
preservation moved, independence was lost, a material correction invalidated prior
acceptance, or a plan-wide decision genuinely needs more detail.

A fresh independent reviewer PASS is eligible for the fast path only when the
Proof Matrix is complete and structural review-contract validation passes in
addition to normal verification/scope/preservation conditions.

## Phase evidence and remediation

Phase-level Verification reports live under `phases/<phase-id>/verification/`.
A fresh Phase Auditor writes `phase-audit.md` and builds compact Proof Coverage
across phase requirements/dimensions.

The Phase Auditor advises; the main orchestrator approves. Missing required proof,
contradictory evidence, stale accepted evidence, or unresolved maintained
consequence suites block the phase.

When the orchestrator finds a gap, write immutable
`phase-remediation-<n>.md` containing:

- governing requirement/finding ids;
- bounded independently reviewable tasks;
- dependencies;
- AC/proof obligations;
- verification and preservation tripwires;
- exclusions;
- evidence required before the gate repeats.

Workers execute remediation; fresh verification and a fresh Phase Auditor precede
the next gate.

## Turn-exit invariant

An active run may yield only when:

- a recorded worker identity is live; or
- run is `waiting-for-worker` with concrete next probe/relaunch; or
- legitimate terminal state is recorded.

Future-tense prose is not enough. `scripts/check_state.py` may enforce this
mechanically.

## Major findings and fixes log

Each run owns one append-oriented `major-findings-and-fixes.md`. Record material
engineering knowledge that future workers should not rediscover:

- serious defects/regressions/integrity incidents;
- non-obvious root causes;
- consequential fixes/architecture/contract decisions;
- rejected alternatives when material;
- material corrections;
- worker availability incidents;
- phase gate/remediation/human escalations.

Do not duplicate routine task reports or private chain-of-thought. Use stable ids
and link evidence/status/follow-up.
