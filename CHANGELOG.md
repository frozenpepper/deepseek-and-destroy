# Changelog

## v15.3 — Context-economy consolidation and semantic-boundary completion

- completed the v15 Evidence Clerk architecture: long worker prose is no longer a
  machine acceptance protocol; deterministic gates prove objective attempt/scope facts
  only, while semantic adequacy stays with LLMs and the premium parent;
- removed `check_review_contract.py` and `_report_contract.py`; removed obsolete
  reviewer/Clerk semantic gate flags rather than silently pretending they still check
  meaning;
- renamed the bounded non-authoritative report preview helper to `report_surface.py` to
  avoid implying decision authority;
- added `dsd_attempt.py launch|gate`, a thin transaction facade that derives attempt
  paths/config, scope baseline, prompt, reservation, launch, gate artifacts and routine
  state bookkeeping without choosing roles, retries, semantics or acceptance;
- made attempts self-contained under `attempts/<role>-<n>/` and clean up pre-launch
  helper failures before an immutable reservation exists;
- made Evidence Clerk always project-read-only; project documentation mutation is a
  normal bounded writer task, while Verification remains conditionally writable only
  for explicit generated/project paths;
- reduced worker context to run rules + COMMON + one role + task; proof recipes are
  loaded only when explicitly named, and prior evidence is passed by immutable path +
  SHA-256 rather than copied prose;
- compressed parent/worker/harness doctrine and moved recovery/barrier/transport/
  compaction details behind lazy-loaded references;
- replaced legacy tests that encoded Verdict markers, Proof Matrices, arithmetic parsing
  and Clerk overlays as correctness with objective-mechanics and natural-report
  regressions;
- added an end-to-end natural-prose Reviewer regression proving that a report with no
  ceremonial verdict/table/finality syntax still passes the mechanical gate cleanly.

## v15.2 — Orchestrator secretarial-work elimination

Field feedback from a Claude Opus orchestration run showed that v15.1 preserved
strong evidence semantics but leaked mechanical serialization back into premium
context. v15.2 fixes the abstraction boundary rather than adding another worker
ritual:

- `render_task_contract.py` now accepts a JSON spec file or stdin while retaining
  the legacy slot CLI; it can use `DSD_RUN_ROOT` and run-relative output paths, and
  optional role preflight rejects Evidence-Clerk recursion.
- added `dsd_state.py` for validated atomic `bind-contract`, `bind-attempt`, `accept`,
  and `set-next` transitions instead of repeated state heredocs.
- centralized report wire parsing in `_report_contract.py` and task-contract field
  parsing in `_task_contract.py`; gates accept harmless bullet/bold decoration and
  descriptive labels after Proof Matrix AC ids without duplicating private grammar.
- Reviewer task AC discovery is now scoped strictly to `## Acceptance criteria`, so
  AC ids mentioned in objectives/inputs cannot contaminate the review contract.
- published the canonical report wire grammar in worker `COMMON.md`, including the
  stable Clerk-check-id requirement; validator archaeology is no longer a startup
  task.
- Evidence Clerk attempts no longer self-route because their own contract happens to
  contain an `Evidence Clerk Checks` section; the renderer rejects that combination
  when the intended role is known, while the gate treats it as nonrecursive.
- Verification is conditionally writable when and only when its immutable contract
  has non-empty `Allowed source changes`, covering generated accepted artifacts
  without adding a redundant specialist role.
- `scope_snapshot.py --extra-inventory` now captures and re-enumerates Git-ignored
  load-bearing roots; `--task-contract` imports the contract declaration automatically
  and `evidence_gate.py` rejects baselines that omit required roots.
- documented the report-only same-role correction pattern for the rare missing
  semantic field that a Clerk cannot invent; Clerk-normalizable formatting still
  does not consume a new semantic worker run.
- `evidence_gate.py` accepts run-relative artifact paths and normalizes them before
  immutable binding checks; Claude multi-run resume guidance explicitly uses
  `DSD_RUN_ROOT` rather than guessing.
- added focused v15.2 regressions for JSON contracts, parser tolerance/AC isolation,
  ignored-tree additions, state transactions, and conditional Verification writes.
- tightened parent doctrine around compact recommended adjudications instead of
  presenting routine decision menus, while preserving human escalation for true
  authorization/intent boundaries.

## v15.1 — Kilo restoration and orphan-surface audit

- Restored Kilo Code as a first-class parent harness with top-level `KILO.md`,
  explicit detection/installation, and canonical `.kilo/plugin/` compaction asset.
- Promoted Kilo subagent templates to canonical `adapters/kilo/` assets and retained
  old `contrib/kilo/` Python entry points only as compatibility wrappers.
- Added `native_worker_attempt.py` so Kilo-native Task delegation reserves/finalizes
  the same immutable launch/terminal authority and enters the ordinary scope/evidence
  gate instead of bypassing the v15 lifecycle.
- Corrected stale v15 configuration that still described Reviewer→Fixer session
  resume and oversimplified Evidence Clerk write capability.
- Made the harness installer consume checked-in canonical Codex/Claude/OpenCode/Kilo
  adapter assets instead of synthesizing hidden duplicate plugin/hook bodies.
- Centralized harness detection in `detect_harness.py`; the installer no longer owns
  a second harness registry.
- Fixed the old Kilo compaction path/module convention and complete helper-copy set;
  hardened Kilo/OpenCode compaction plugins against resume-instruction failure.
- Added Kilo/native lifecycle and orphan-regression acceptance coverage.

## v15 — Semantic-worker tolerance and single-source control cleanup

- Removed the duplicate premium-facing `orchestrator/CONTROL.md`; `SKILL.md` is now the single parent doctrine and role technique remains outside premium context.
- Reduced generated `WORKER_RULES.md` to run facts/run-specific constraints; universal and specialist behavior live only in `COMMON.md` and the exact role mini-skill.
- Relaxed terminal-report clerical coupling: launcher-owned Role/Task identity is no longer required from workers, `FAST-PATH ELIGIBLE` is derived by the evidence gate, and the Evidence Clerk uses one canonical verdict marker.
- Kept semantic proof strict while making noncanonical report finality and equivalent per-AC review serialization Clerk-normalizable. A missing/untouched report skeleton, forbidden source movement, mutated immutable authority, or genuinely missing proof remains non-waivable.
- Made ordinary role changes start fresh sessions; durable reports transfer context across Reviewer/Fixer/Implementer boundaries. `--resume-session` is limited to trustworthy same-role continuation/recovery.
- Made `launch-reservation.json` the single immutable authority for new attempts. v15 `attempt.json`/`terminal.json` lifecycle records bind to its path/hash instead of duplicating all authority fields; historical v14 terminal evidence remains readable.
- Simplified task contracts by omitting empty optional sections and launch-derived report/log/evidence boilerplate while retaining explicit `Allowed source changes`.
- Made the Decision Packet extractor tolerate noncanonical reports with a bounded decision surface rather than forcing premium context to open the entire artifact.
- Fixed compaction continuity semantics: checkpoints bind governing plan-reference, authority-index, effective-config, and plan-source hashes; `verify-resume` now checks them mechanically and fails closed on authority drift.
- Centralized role capability sets (`contract-scoped writers`, `zero-change roles`, `phase-barrier writers`, `read-only roles`) in `scripts/_roles.py`.
- Added role-skill integrity coverage so truncated/incomplete specialist doctrine is detected; corrected terminal-status guidance for Discovery, Phase Surveyor, and Verification.
- Simplified harness/wait doctrine while preserving event-driven quiescent waiting, Evidence Clerk offload, exact scope tripwires, reportless Recovery, two-zero-change guard, phase write barrier, and fresh independent review.

## v14 — Specialist role skills and a cleaner premium control plane

- Split worker behavior into one universal `worker/COMMON.md` plus nine focused `worker/roles/dsd-<role>/SKILL.md` files for Implementer, Fixer, Reviewer, Verification, Discovery, Phase Surveyor, Recovery, Phase Auditor, and Evidence Clerk.
- Keep those role files Agent-Skill-compatible for standalone evaluation while production DSD selects the exact role explicitly; native harness skill discovery/activation is never part of the correctness contract.
- Snapshot every role skill immutably into each run-level worker-rules revision and bind nested role-skill hashes in `MANIFEST.json` (`dsd-worker-rules-manifest-v2`).
- Simplify worker launch authority to `WORKER_RULES.md` + `COMMON.md` + the exact role `SKILL.md` + immutable task contract + proof patterns. Remove the old `ROLES.md` / `BUILD.md` / `REVIEW.md` / `EVIDENCE.md` role-family layering.
- Add `scripts/_roles.py` as the single mechanical registry for role names, terminal vocabularies, role-skill paths, and mutation classification, eliminating duplicated launcher/gate registries without merging semantic roles.
- Slim the premium-facing `SKILL.md` around orchestration decisions and routing; worker-job technique stays in the role mini-skills instead of consuming premium context.
- Preserve the v13 architecture that matters: external OpenCode workers, immutable contracts/evidence, Evidence Clerk token offload, fresh review after mutation, exact write scopes, quiescent waiting, two-zero-change guard, and phase write barrier. No rigid JSON worker-response protocol or new supervisor subsystem is introduced.

## v13 — Premium-context economy and external-worker event control

- Reassert the real default topology: premium orchestrator -> external OpenCode CLI -> `opencode-go/deepseek-v4-flash`; native subagent hooks are not assumed to observe that worker.
- Add `orchestrator/CONTROL.md` with mandatory authority reading, handover trust boundary, event-driven narration, three-deep-read ceiling, and two-zero-change decomposition guard.
- Replace hand-authored multi-kilobyte worker prompts with immutable versioned `worker-rules/rNNNN/` snapshots (including canonical `worker/ROLES.md` role contracts), small immutable numbered task-contract revisions, `render_task_contract.py`, and `render_worker_prompt.py`.
- Add `run_worker.py` and `wait_worker.py`: one wrapper owns OpenCode process/DB/log/session bookkeeping and emits a durable terminal event; harnesses wait natively or through one long blocking helper rather than model-level polling.
- Claude adapter now uses a project `PostToolUse:Bash` `asyncRewake` hook to wait on the detached OpenCode wrapper terminal event and wake idle Claude; Codex/OpenCode use foreground or long blocking event waits. CPU/log polling is recovery-only.
- Add a conditional Evidence Clerk role plus `evidence_gate.py` for report skeleton/misplacement, verification arithmetic, provenance/tripwire reconciliation, and cheap log/progress/handover maintenance; read-only source movement and mutating changes outside declared write scope are hard recovery failures, never clerical reconciliation.
- Tighten worker behavior: current contract-bound mechanical helper facts are given facts; stale helper artifacts are not authority; ordinary repository mismatch is resolved from authority rather than returned as a scope-choice menu.
- Add full Git-worktree per-attempt scope baselines and exact `Allowed source changes` for mutating roles, with symlink-safe hashing and hard scope-drift enforcement.
- Add atomic attempt reservations so the same numbered attempt/report/log cannot be launched twice, and prohibit task-owned background writers after FINAL.
- Bind each attempt cryptographically to its exact launch prompt, task-contract revision, worker-rules revision + manifest/protocol snapshot, and scope baseline; the evidence gate rejects post-launch mutation of any bound authority/evidence artifact.
- Bind accepted Evidence Clerk overlays to the exact Clerk report SHA-256 so a later same-path edit cannot inherit an older CLEAN gate.
- Keep the semantic task contract role-neutral: role-specific report paths live in immutable launch handoffs, avoiding contradictory Implementer/Reviewer deliverables.
- Make terminal worker/review evidence immutable; later repairs/reviews use new numbered attempts.
- Add an explicit phase write barrier: artifact-mutating verification is a writer and finishes before closure; post-barrier verification/audit is read-only, and any later mutation reopens/invalidates the gate snapshot.
- Make routine parent narration mechanically bounded: silent by default; host-forced routine update is one sentence (~25 words).
- Demote optional contributed adapters from core workflow assumptions; they load only when explicitly selected.
- Incorporate selected Lunacy lessons (path-only handoffs, quiescent waits, compact control packets, immutable evidence, three-deep-read ceiling, write barrier) without copying Codex-native worker semantics or parent repository review.

## v12 — Worker proof contracts

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
