# Changelog
## Unreleased

### Worker proof-contract revision

Based on a long field run where independent reviews still accepted materially
wrong-reason evidence:

- added `worker/SKILL.md`, `worker/BUILD.md`, `worker/REVIEW.md`, and
  `worker/PROOF-PATTERNS.md` as a compact worker discipline layer rather than
  growing one giant orchestrator prompt;
- established the causal-proof rule: an expected outcome is not proof unless the
  named production mechanism was actually reached and caused it;
- added stable `AC-*` acceptance ids, shared builder/reviewer Proof Obligations,
  and reviewer Proof Matrices;
- added counterexample-first review for high-risk criteria;
- added optional proof recipes for negative/fail-closed gates, cardinality,
  canonical identity, durability, and derived status/evidence;
- made task-relevant correctness defects incompatible with PASS/fast-path even when
  described as known limitations or future cleanup;
- required concrete closure tasks for intentional maintained-suite consequences,
  while keeping the phase blocked until closure;
- added `needs-revalidation` → `still-valid|superseded` handling for dependent work
  after reopened prerequisites;
- added `scripts/check_review_contract.py` to mechanically verify AC coverage,
  Proof Matrix structure, verdict, defect declaration, and fast-path consistency
  without pretending to judge software semantics;
- hardened OpenCode PID persistence/recovery and duplicate-launch prevention;
- refreshed `SKILL.md`, `PROMPTS.md`, `WORKSPACE.md`, and README around the proof
  contract while preserving worker authority and orchestrator quota economy.

- Added the canonical root `LICENSE` file for the MIT License already declared in `SKILL.md`.
- Added an explicit README license section covering permitted reuse, modification, redistribution, and commercial use.


## Prescribed-construction and progress-watch revision

Based on a 36-hour run using the same DeepSeek model for orchestrator and workers:

- add **prescription over instruction** for decided large mechanical refactors;
- require a worker-produced construction brief with exact files, symbols,
  boundaries, wiring, exclusions, first edit, and verification;
- treat the first substantial zero-change analytical death as a decomposition
  failure requiring split/prescription, not an identical retry;
- distinguish startup liveness from ongoing progress and detect probable
  hung-but-alive workers through repeated process/CPU/output/checkpoint windows;
- make scope baselines per-attempt and refresh them against the immediately
  previous accepted tree while keeping behavior-preservation baselines immutable;
- retry a flaky session resume exactly once before falling back to a fresh fixer;
- require immediate plan-hash/snapshot capture whenever an authoritative revision
  is noticed mid-run.

## v8 — Worker authority and phase-remediation gates

- Made the worker/orchestrator boundary absolute: workers establish technical
  facts and modify project files; the orchestrator routes, decides, and approves.
- Removed direct orchestrator spot checks, code intervention, test execution, and
  self-verification paths.
- Added the doubt-to-worker rule: conflicting or suspicious evidence launches a
  fresh clean-context Review, Verification, Discovery, Recovery, or Phase Audit
  worker; findings re-enter repair plus fresh re-review.
- Changed non-converging task handling to re-scope, commission discovery, improve
  prompts, or route stronger workers rather than orchestrator takeover.
- Added immutable `phase-remediation-<n>.md` plans. Every phase-gate finding is
  converted into bounded worker tasks, followed by fresh verification and a new
  Phase Auditor before the gate repeats.
- Clarified that the hard gate is a plan-wide judgment, not a task-level code
  review or implementation pass.

## v7 — Orchestrator quota economy

- Added an explicit task-acceptance fast path after credible independent PASS.
- Prohibited routine orchestrator code rereads, test reruns, artifact reparsing, and count re-derivation.
- Added recorded triggers and a two-check limit for direct orchestrator spot checks.
- Added compact Decision Packets to every worker report and a helper to extract them.
- Added hash-based authority caching and a resume fast path that avoids rereading unchanged plans/docs/run history.
- Added minimum-sufficient prompt envelopes and a three-item cap on bespoke reviewer risk hypotheses.
- Added sparse user-facing communication defaults; detailed evidence remains in run artifacts.
- Clarified that Phase Surveyor audits are reused until material drift.
- Consolidated related major-log entries by root cause.
- Added collision-resistant task directory guidance.

## Delegation-boundary revision

Corrects an overreach introduced by the context-load revision: the reliability
requirements remain, but their tool-heavy execution returns to cheap workers and
mechanical helpers.

- establish the primary rule: the orchestrator owns decisions, routing, conflict
  resolution, and approval—not repository-scale investigation volume;
- add Phase Surveyor, Recovery Auditor, and Phase Auditor worker roles;
- make current-state audits worker-produced inputs to decomposition;
- build rich prompts from authoritative documentation and durable worker briefs
  rather than orchestrator rediscovery;
- capture scope baselines through a helper, equivalent tooling, or a bounded cheap
  worker;
- route reportless-worker forensics to a fresh Recovery Auditor while the
  orchestrator chooses the final disposition;
- route large verification classes to Verification Workers and phase evidence
  synthesis to a Phase Auditor;
- retain the main orchestrator as the only phase approver, with targeted spot
  checks rather than mandatory bulk command execution;
- add `scripts/scope_snapshot.py` for mechanical content-hash capture and compare.

## Context-load and crash-recovery revision

Based on 42 worker launches and field reports from long plan executions:

- count independently reviewable units before each spawn and split when there is
  more than one primary unit;
- treat discovery cost, artifact size, and verification classes as task size;
- add discovery workers that emit cited durable specs before construction;
- choose fresh implementer versus resumed explorer based on whether findings
  compress without losing important context;
- add explicit exclusions and verification-only worker prompts;
- require workers to create reports early and append during execution;
- wait for process exit before final artifact/scope judgments;
- treat reportless worker exits as suspect-tree events requiring hash/diff
  reconciliation;
- forbid VCS status letters as content-preservation evidence;
- use fresh fixers after heavy review contexts instead of blindly resuming them;
- replace single-signal OpenCode liveness with process + elapsed + CPU + output
  classification and warn against `pgrep -f` self-matches;
- add minimal health probes, exact model-id discovery, active
  `WAITING-FOR-WORKER` re-probing, and automatic fallback/relaunch;
- require phase current-state audits before decomposition;
- strengthen reviewer independence, bidirectional gate checks, authority/path
  validation, and verification-coverage checks;
- forbid ending an active turn on a future-tense intention.

## Runtime reliability and claim-discipline revision

Based on extended orchestrator use:

- replace buffered OpenCode log-growth liveness with actual-process accumulated
  CPU-time sampling;
- add explicit `prepared` → `launching` → `in-progress` state transitions and a
  consistency invariant that catches intended-but-never-started spawns;
- add a preflight heuristic to split likely >30-minute tool-heavy tasks before
  the first worker launch;
- require inherited prompt audits to cover rules, criteria, commands, worktree,
  and every report/log/output path;
- add measurement-predicate discipline for counts, absence, completeness, and
  search claims;
- require material corrections to be surfaced, logged, propagated through state
  and decisions, and followed by continued execution.

## Autonomous-continuation and clarity revision

This revision restructures the skill around the primary execution contract:

- continue until the complete plan is finished or genuinely human-blocked;
- do not stop after tasks, reviews, or phases for routine acknowledgement;
- resolve ordinary decisions from the plan, project documentation, architecture,
  accepted evidence, and project ethos;
- escalate to humans only for major decisions, authorization/access, persistent
  worker availability, unsafe concurrency, or irreconcilable plan problems;
- never substitute the main orchestrator for unavailable workers;
- distinguish substantive escalation from worker availability and human escalation;
- persist one exact `next_action` after every meaningful transition;
- treat resume as continued execution rather than status reporting.

The formerly monolithic skill was split for clarity:

- `SKILL.md` — core mission, authority, loop, escalation, and gates;
- `WORKSPACE.md` — run namespaces, plan snapshots, concurrency, state, and logs;
- `PROMPTS.md` — exact worker prompts and Common Rules;
- `OPENCODE.md` — OpenCode-specific worker storage and launch behavior.

The existing multi-orchestrator run layout, immutable plan references, major
findings/fixes log, reviewer-led repair, fresh re-review, liveness checks,
transport separation, preservation baselines, defect ledger, and validation
independence remain in place.

## v10 — Durable context checkpoints and harness adapters

- Added a harness-neutral Context Checkpoint Protocol for long orchestrator runs.
- Added configurable 65% checkpoint, 75% compact-before, and 80% hard-ceiling defaults.
- Made `HANDOVER.md` incrementally maintained so compaction does not require a large rewrite.
- Added immutable per-run `compactions/<sequence>/` snapshots and resume manifests.
- Added separate main-orchestrator harness detection; worker harness routing remains independent.
- Added Codex, Claude Code, and OpenCode orchestrator adapter documentation.
- Added project-local adapter templates and an idempotent installer.
- Added `detect_harness.py` and `context_checkpoint.py` helpers.
- Extended `check_state.py` with checkpoint-state and turn-exit invariants.
- Added a generic fresh-session fallback when native compaction is absent or fails.
