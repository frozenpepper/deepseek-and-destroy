# Changelog

## v15.4.3 — Stable phase finalization

- Require all selector/pointer/promotion/finalization operations that establish or refer to a final snapshot to be exercised before the freeze is declared final.
- Treat any finalization that requires later mutation of an artifact inside that same snapshot, or creates a self-invalidating dependency cycle, as a phase defect.
- Added only concise parent/Phase-Auditor doctrine; no new validator, state, helper, proof pattern, or document.

## v15.4.2 — Premium trust/context discipline

- Make worker trust explicit: fresh Reviewer is routine technical verification; parent technical self-verification is reserved for frozen phase approval or explicit worker escalation.
- Define the premium evidence ladder: mechanics → bounded surface → Clerk → targeted evidence → full report.
- Forbid premium consumption of Implementer/Fixer output when another specialist is the next consumer, redundant technical re-verification, authority restatement in contracts, and routine progress narration.
- Treat DSD-framework investigation as delegated cheap-worker work whenever possible.
- Keep parent-facing `dsd_attempt` stdout status-only by default; durable detail remains on disk.
- No new validators, state fields, documents, or orchestration mechanics.

## v15.4.1 — Attempt lifecycle and run-root binding hardening

- Fixed run-relative state/attempt paths to resolve against the DSD run root rather than the caller's process cwd, including resumed/legacy `current_contract.path` bindings.
- Added pre-launch state/lifecycle preflight so known state-binding failures are detected before starting a new worker. High-level launch now always starts the detached low-level monitor, binds the live attempt immediately, and only then waits internally when foreground behavior was requested; `wait` refreshes state to `process-exited`.
- Added bounded factual `last_attempt`; binding a new role automatically moves the prior terminal/gated attempt there instead of overwriting its only state pointer or calling it `retired-unaccepted`. Full history remains cold in immutable attempt directories.
- Allowed gates to bind to either the current attempt or the matching archived immutable attempt.
- Kept reportless terminal attempts representable as `report-recovery`. Added an explicit exceptional `--supersede-incomplete` path for terminal-less attempts; it records `lifecycle-incomplete`/`superseded` honestly and refuses when a recorded worker/monitor is still alive.
- Added lifecycle regression coverage for all of the above.

## v15.4 — Context-economy consolidation and strict semantic/mechanical boundary

- Made Evidence Clerk **optional at parent semantic-consumption boundaries**. Implementer/Fixer normally flow directly to fresh Reviewer; Clerk is never inserted merely because it exists.
- Made Evidence Clerk always project-read-only. Missing technical predicates route to Verification/Review; project documentation changes are ordinary writer tasks.
- Removed task-level Clerk-check semantics and all remaining executable verdict/AC/defect/arithmetic/Proof-Matrix interpretation. Obsolete semantic-gate flags fail instead of becoming misleading no-ops.
- Reduced worker context to immutable run facts + Common + one role + task; proof recipes load only when explicitly named and never for Clerk.
- Made new attempts self-contained under `attempts/<role>-<n>/`; `dsd_attempt.py` owns normal launch/wait/gate bookkeeping.
- Made gate stdout mechanics-only by default; `--surface` explicitly opts in to a bounded non-semantic report prefix at a parent decision boundary, preventing intermediate worker prose from leaking into premium context.
- Retired the multi-argument contract authoring interface. `render_task_contract.py` accepts one JSON spec (`--spec FILE|-`) so premium models cannot fall back to dozens of shell arguments.
- Simplified state to durable facts and exact `next_action`; removed semantic/routing/no-progress bookkeeping from new state.
- Kept deterministic enforcement only for objective integrity: immutable authority, lifecycle, exact scope movement, ignored load-bearing roots, read-only/write boundaries, fresh Reviewer provenance after mutation, phase freeze, and resume authority continuity.
- Split Kilo's optional native-worker detail out of the hot parent adapter and substantially shortened `SKILL.md`, `WORKSPACE.md`, `OPENCODE.md`, and `COMPACTION.md`.

## v15.3 — Finish the Clerk architecture; remove deterministic prose adjudication

- Finished the v15 design instead of merely relaxing its regexes: `evidence_gate.py` is now an integrity-only envelope for immutable authority, lifecycle, report artifact state, worker-rules integrity, and project scope movement. It does not interpret worker conclusions, AC coverage, Proof Matrix shape, defect prose, or test arithmetic.
- Removed `check_review_contract.py`, `_report.py`, and `decision_packet.py` from the live control path. Python no longer pretends that regex presence proves engineering review quality.
- Made worker reports explicitly natural semantic artifacts. Exact `Verdict:`/FINAL/Decision Packet/Proof Matrix/test-count/Clerk-id serialization is guidance only, never an acceptance grammar.
- Promoted Evidence Clerk from exceptional formatting repair to the normal semantic bridge protecting premium context. `dsd_attempt.py interpret` launches a fresh Clerk over the exact source task, source report, and clean integrity gate without hand-authoring a second Clerk contract.
- Removed the old Clerk-overlay/re-gate protocol and semantic `fast_path_eligible` derivation. Clerk output is itself mechanically integrity-gated, then read directly by the premium parent.
- Changed task acceptance so Python records—but never infers—the premium parent's semantic verdict. `dsd_state.py accept-task` now binds the source integrity gate plus the exact semantic-evidence report (normally Clerk) and that report's clean integrity gate.
- Removed stable Clerk-check-id enforcement and made AC ids an authoring convenience: JSON acceptance items without an `AC-*` prefix receive stable ids automatically at render time.
- Simplified the launcher report placeholder so it contains no fake semantic verdict or defects; the integrity gate recognizes it by the reservation-bound hash.
- Kept deterministic mechanisms only where they establish objective facts: exact write scopes, ignored-tree inventories, immutable hashes/bindings, lifecycle, concurrency-relevant worktree movement, zero-change guard, phase barrier, and resume authority continuity.

## v15.2 — Premium-control serialization and tolerant gate cleanup

- Added JSON/stdin task specs to `render_task_contract.py`; contract semantics no longer need 40–80 hand-authored shell arguments.
- Added `dsd_state.py` named atomic transitions so routine contract/attempt/accept/next-action bookkeeping no longer requires hand-written `state.json` heredocs.
- Added `dsd_attempt.py` for the normal external-OpenCode path: derive attempt/report/log/prompt paths and run runtime from state, capture the task-bound scope baseline, render the handoff, launch, bind lifecycle state, and later gate the current terminal attempt with short commands.
- Relaxed report parsing around Markdown decoration (`- **Verdict: PASS**`, descriptive Proof Matrix AC cells, etc.) while keeping role-valid semantic verdicts and missing AC proof strict. Acceptance ACs are now extracted only from the `Acceptance criteria` section, preventing quoted foreign AC ids from becoming phantom obligations.
- Removed FINAL-marker clerical routing for substantive exact-attempt reports; process/native Task terminal lifecycle is the finality authority. Missing/untouched launcher skeletons still fail closed into recovery.
- Made Evidence Clerk self-recursion a launch-time contract error; historical malformed Clerk contracts no longer recursively request another Clerk at gate time. Vague/legacy Clerk requests receive stable built-in reconciliation ids rather than burning a worker rerun for formatting.
- Added first-class ignored/load-bearing `Extra scope inventory` support to task specs and scope baselines, including explicit added/removed/modified reporting for Git-ignored trees.
- Made Verification conditionally artifact-mutating only when exact generated-artifact `Allowed source changes` are declared; otherwise it remains mechanically read-only and any source movement fails hard.
- Corrected Evidence Clerk capability classification: evidence-only Clerk attempts are read-only; a Clerk becomes a project writer only when its exact contract declares an allowed documentation path.
- Allowed run-relative evidence-gate paths and improved multi-run resume selection by preferring the unique checkpoint-requiring run when session binding is unavailable.
- Kept the high-value field-proven safeguards unchanged: immutable attempt authority, full scope tripwire, fresh adversarial review, Recovery, two-zero-change guard, phase barrier, and `DECISION_REQUIRED`.

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
