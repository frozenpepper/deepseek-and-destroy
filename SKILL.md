---
name: deepseek-and-destroy
description: "Execute a complex multi-phase implementation plan through configurable worker-agent loops: fresh implementer, fresh reviewer, resume that reviewer to fix its own findings, then fresh re-review, while the main orchestrator retains decomposition, escalation, and phase-level approval. Defaults to OpenCode with DeepSeek V4 Flash; optional Markdown configuration may replace workers, models, endpoints, role routing, and project rules."
license: MIT
compatibility: codex, claude-code, opencode, and comparable coding harnesses
metadata:
  default-harness: opencode
  default-model: opencode-go/deepseek-v4-flash
  review-rounds-budget: "5"
  transport-attempt-budget: "5"
  startup-liveness-grace-seconds: "90"
  pass-standard: zero task-relevant findings
---

# DeepSeek and Destroy

> Feed it a plan. Let the workers implement, review, fix, and repeat until it passes.

You are the main orchestrator for a complex, multi-phase plan. You own the whole
plan, decomposition, architectural judgment, escalation, and phase approval.
Worker agents do the bounded implementation, review, repair, and verification.
The design goal is to keep the main orchestrator focused on high-value judgment
while capable, inexpensive workers perform most of the execution.

## When to use

- You are given a plan file with phases or ordered implementation steps.
- The work is too large for one context or requires verified, phase-gated delivery.
- You need durable interruption recovery and independent task review.
- You want most execution delegated without surrendering phase-level judgment.

## Configuration — optional

The skill is self-contained with the defaults below. A user may optionally attach
or name a Markdown configuration file in the first prompt. The file may override
only what it states; omitted settings inherit these defaults.

Configuration priority, highest first:

1. Current explicit user instructions.
2. A configuration file explicitly attached or named by the user.
3. One unambiguous project-local file named `.deepseek-and-destroy.md`,
   `deepseek-and-destroy.config.md`, or `DSD_CONFIG.md`.
4. `CONFIG.md` beside this skill when the harness exposes sibling files.
5. The defaults in this section.

An external configuration may define:

- agent profiles: harness, endpoint label, model or named agent, reasoning level,
  fresh launch, resume method, liveness signal, safe stop, and suitable roles;
- role routing for implementer, reviewer, resumed fixer, fresh re-reviewer,
  phase-finding worker, and escalation;
- planning, implementation, review, delivery, or domain-specific rules;
- role-specific prompt additions, or replacement templates that preserve every
  required rule, context field, evidence input, report path, and verdict contract;
- review and transport budgets, liveness grace, workspace, and live-test policy;
- project-local guides or rule files that must be read.

Treat configuration as natural-language instructions, not as a rigid schema. Do
not place credentials in it; use existing harness profiles or environment
variables. Do not silently combine materially conflicting external files.

### Ephemeral worker storage (opencode harness only)

This section applies **only when the effective worker harness is OpenCode CLI**.
Other harnesses (Codex, claude-code, custom) have their own session/storage
models and are unaffected by these rules. If the resolved harness is not
opencode, skip this entire section.

OpenCode has no built-in ephemeral/in-memory session mode. Every `opencode run`
writes to a shared SQLite database at `~/.local/share/opencode/opencode.db` by
default. Procedural DSD runs spawn many short-lived workers (implementer,
reviewer, fixer, re-reviewer) that accumulate sessions, messages, parts, diffs,
and snapshots — quickly reaching multi-GB database growth and making the session
history unusable for real interactive work.

To prevent this, every opencode worker spawn MUST use an isolated, disposable
database file via the `OPENCODE_DB` environment variable. Each worker gets its
own throwaway SQLite file; when the worker's lifecycle is complete, the file is
deleted. This keeps the main opencode database pristine for interactive use.

> **`OPENCODE_DB` must be an absolute path (or `:memory:`).** A relative value is
> resolved by opencode against its own data directory
> (`~/.local/share/opencode/`), **not** the current working directory, so a
> relative path would create/look up the DB in the wrong location and resume
> would fail to find the stored session. Always expand `<workspace>` to an
> absolute path (e.g. via `$(pwd)`) before building `WORKER_DB`, and store the
> absolute path verbatim in `state.json`.

The pattern:

1. **Before spawning a worker**, create a unique ephemeral DB path (absolute):
   ```bash
   # WORKSPACE must be an absolute path
   EPHEMERAL_DB_DIR="$WORKSPACE/.plan-execution/ephemeral-db"
   mkdir -p "$EPHEMERAL_DB_DIR"
   WORKER_DB="$EPHEMERAL_DB_DIR/<task-id>-<role>-<round>.db"
   # WORKER_DB is absolute and is what gets recorded in state.json
   ```

2. **Launch the worker** with `OPENCODE_DB="$WORKER_DB"` prefixed on the command.

3. **Resume the same worker** with the same `OPENCODE_DB="$WORKER_DB"` value
   (the absolute path recorded in `state.json`) so the session ID resolves in
   the worker's own database.

4. **After the worker's full lifecycle ends** (report extracted, verdict
   recorded, no further resume needed), delete the ephemeral DB:
   ```bash
   rm -f "$WORKER_DB" "$WORKER_DB-wal" "$WORKER_DB-shm"
   ```

Credentials (API keys) are stored in `~/.local/share/opencode/auth.json`, a
separate file outside the database. The worker process reads credentials from
the default data directory regardless of `OPENCODE_DB`, so no credential
symlinking is required.

In addition, the project `opencode.json` (or the orchestrator's effective
config) SHOULD include these settings to minimize per-worker disk growth when
using the opencode harness:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "snapshot": false,
  "compaction": { "auto": true, "prune": true }
}
```

- `snapshot: false` disables the internal git snapshot system that tracks file
  changes for undo/revert — the largest non-DB disk consumer. Workers do not
  need undo capability.
- `compaction.prune: true` removes old tool outputs from context to save tokens
  and reduce the `part` table growth.

### Default worker profile

- **Profile:** DeepSeek Flash Worker
- **Harness:** OpenCode CLI
- **Model:** `opencode-go/deepseek-v4-flash`
- **Endpoint:** the provider already configured in OpenCode
- **Ephemeral DB:** opencode-harness worker spawns use an isolated `OPENCODE_DB`
  file (see "Ephemeral worker storage" above). The DB path is recorded in
  `state.json` alongside the session ID so resume can reuse it. Non-opencode
  harnesses skip this.
- **Fresh launch:**

  ```bash
  WORKER_DB="<ephemeral-db-path>"
  OPENCODE_DB="$WORKER_DB" opencode run \
    --model opencode-go/deepseek-v4-flash \
    --auto \
    --title "<task-id>-<role>-<round>" \
    --dir "<project-root>" \
    "<full-self-contained-prompt>" 2>&1 | tee "<log-path>"
  ```

- **Resume:**

  ```bash
  OPENCODE_DB="<worker-db-path-from-state>" opencode run \
    --model opencode-go/deepseek-v4-flash \
    --auto \
    --session "<session-id>" \
    --dir "<project-root>" \
    "<continuation-prompt>" 2>&1 | tee "<log-path>"
  ```

- **Cleanup after worker lifecycle:**

  ```bash
  rm -f "<worker-db-path>" "<worker-db-path>-wal" "<worker-db-path>-shm"
  ```

- **Liveness:** within 90 seconds, require positive worker-level evidence such as
  log growth, report creation/growth, or harness status proving model execution
  began. A wrapper PID or registered session alone is insufficient.
- **Roles:** implementer, reviewer, resumed fixer, fresh re-reviewer, and
  phase-finding worker.

Default routing uses this profile for every worker role. The current main
orchestrator performs decomposition, escalation, and final phase approval.
Default review budget is 5 substantive rounds; default transport budget is 5
launch attempts per role invocation. Execution is sequential.

### Configuration application contract

Before intake and before every spawn:

1. Resolve the effective profile, role routing, policy values, prompt additions,
   and applicable project rules.
2. Record a concise, secret-free snapshot in
   `.plan-execution/effective-configuration.md` and the selected role profile in
   `state.json`.
3. Launch through the resolved profile. Never silently fall back to the built-in
   OpenCode command when another profile was assigned.
4. Put the actual task context, acceptance criteria, verification commands, and
   applicable rules into the worker prompt. Workers do not magically inherit the
   orchestrator's configuration.
5. Reject and rerun an invocation that used the wrong harness, model, endpoint,
   reasoning level, fresh/resumed mode, or required rule set.

Project-local instructions such as `AGENTS.md`, `CLAUDE.md`, and files referenced
by the authoritative plan remain binding. Configuration may specialize them but
may not weaken honesty, safety, test integrity, or explicit acceptance criteria.

## Core execution defaults

- **PASS:** zero unresolved findings relevant to the task or phase. A genuine
  pre-existing defect outside scope belongs in the defect ledger, not in the
  current task's fix list.
- **Repair:** resume the reviewer that reported FAIL so it retains its evidence;
  a different fresh reviewer validates the repair.
- **Substantive budget:** at most 5 fresh review rounds, then escalation.
- **Transport budget:** at most 5 attempts for dead launches, broken transport,
  hangs, or malformed reports. Transport failures do not consume review rounds
  and do not by themselves justify abandoning delegation.
- **Timeout:** once liveness is established, allow at least 30 minutes or run in
  the background and poll. Never wait the full timeout when liveness was absent.
- **Scope evidence:** use VCS diff or content hashes, never timestamps alone.
- **Live/destructive/paid tests:** require explicit authorization.

> Fresh contexts provide independent judgment. A context is resumed only for the
> repair step that benefits from evidence already gathered. If fresh independent
> validation is lost, record that loss explicitly; do not present self-validation
> as peer review.

## Workflow overview

```
PLAN FILE
  │
  ├─ read whole plan, decompose into ordered tasks (Phase 1 → N)
  │
  ▼  for each task, sequentially:
  ┌─────────────────────────────────────────────────────────┐
  │  PER-TASK LOOP                                          │
  │  1. compose self-contained task prompt                  │
  │  2. spawn IMPLEMENTER (fresh) → implementer-report.md   │
  │  3. spawn REVIEWER (fresh)   → review-<n>.md (VERDICT)  │
  │     PASS (zero relevant findings) → task passed          │
  │     FAIL (relevant finding) → RESUME reviewer to fix     │
  │        its own findings → fresh review (n+1)            │
  │     round reaches 5 without PASS → ESCALATE (you fix it)│
  └─────────────────────────────────────────────────────────┘
  │  all tasks in the phase passed
  ▼
  MAIN-ORCHESTRATOR PHASE REVIEW (you, no code changes)  ← HARD GATE
  │  findings? → spawn REVIEWER; on FAIL resume it to fix;
  │     fresh review, same loop/budget, until zero relevant findings
  ▼  you approve (and verification genuinely passes)
  Phase complete → update plan progress → next phase
  │
  ▼  after the last phase is approved
  FINAL: run full verification, update plan progress log, report completion
```

Rules of thumb that follow from this:

- **Per-step/single-task quality is normally decided by spawned agents.** You
  interpret their evidence and intervene directly only for escalation, suspicious
  evidence, structural problems, or configuration failure.
- **Major-phase completion is decided by you alone.** You review the whole phase
  yourself (read-only); no spawned reviewer approves your phase gate. Only the
  *fixes* you generate go through the spawned review/fix loop.
- **Soft vs hard gates.** A task review is a *soft* gate: even an independent
  worker can miss plan-wide or cross-task consequences. Your phase gate is the
  *hard* gate: you run the full verification suite yourself. A phase is never
  approved with a failing verification command.
- **Context model.** Fresh session for divergent judgment (implement, validate);
  resumed session for incremental repair (a reviewer fixing the findings it just
  produced).

## Step 0 — Intake

1. Read the entire plan and every project instruction or referenced handover that
   materially governs it. Locate `AGENTS.md` first when present.
2. Resolve the effective configuration and persist its secret-free snapshot.
3. Create or resume the orchestration workspace.
4. Map phases, dependencies, acceptance criteria, and verification commands.
5. Decompose the next phase into bounded tasks and persist the decomposition.
6. Resolve minor implementation ambiguity from the plan, project conventions,
   and existing architecture. Ask the user only when ambiguity materially changes
   product behavior, public contracts, data compatibility, security, destructive
   operations, architecture, or the meaning of acceptance.

## Decomposition rules

A handoff unit is **one phase, a contiguous run of steps, or a single step** —
choose the largest chunk that is still:

- **Well-defined:** outputs, intended subsystem, and public contracts are known up front.
- **Self-contained:** requires no mid-task judgment from you; all decisions are
  in the plan or in the prompt you write.
- **Verifiable:** has explicit acceptance criteria and runnable verification
  commands (tests, typecheck, lint).
- **Single-spawn sized:** completable by one agent run without blowing context.

Never hand off:

- Architecture/design decisions or ambiguity resolution — you keep those.
- Anything whose material acceptance criteria you would have to invent mid-run.
- The plan file itself — you own it; agents never modify it.
- "Explore and figure it out" tasks. If a step is too vague to scope, re-scope it
  (or ask the plan-owner) rather than spawning a guessing agent.

Order tasks so each depends only on already-passed work. Run them **sequentially,
one at a time**. Do not parallelize the loop.

## Orchestration workspace

Create a hidden directory at the project root (default `.plan-execution/`;
respect project conventions and add it to `.gitignore` when appropriate):

```
.plan-execution/
  state.json                       # durable progress and effective role choices
  effective-configuration.md       # concise resolved configuration; no secrets
  out-of-scope-defects.md          # unrelated defects discovered during work
  <phase-id>/
    <task-id>/
      task.md                       # exact audited worker prompt
      scope-baseline.json           # optional hashes/diff baseline
      preservation-baseline.md      # required for behavior-preserving refactors
      implementer.log
      implementer-report.md
      review-1.md   fix-1.md
      review-2.md   fix-2.md
      ... review-5.md
      reviewer-session-<n>.id
      run-<role>-<attempt>.log
      verdict.json
```

Keep the workspace proportional: raw logs are useful for failures and audit, but
do not create redundant narrative files beyond those needed to resume reliably.

Task-id convention: `<phase-id>-<seq>` or a short stable slug.

### state.json

```json
{
  "plan_path": "DOCS/Plans/example.md",
  "effective_config": ".plan-execution/effective-configuration.md",
  "phases": {
    "phase-1": {
      "status": "in-progress",
      "tasks": {
        "phase-1-task-1": {
          "status": "in-progress",
          "role_profile": "DeepSeek Flash Worker",
          "transport_attempts": 1,
          "rounds": 1,
          "last_verdict": "FAIL",
          "review_session_id": "svc_abc123",
          "review_worker_db": "/abs/path/to/<workspace>/.plan-execution/ephemeral-db/phase-1-task-1-review-1.db",
          "review_independence": "independent"
        }
      },
      "phase_review": { "status": "pending", "findings": [] }
    }
  }
}
```

`*_worker_db` fields are present only when the harness is opencode and must
always be absolute paths (see "Ephemeral worker storage" above).

Update `state.json` before every spawn and after every meaningful transition.
Record the effective role profile, attempt, report/log paths, verdict, session id,
worker ephemeral DB path (`*_worker_db`, opencode harness only), and review
independence. It is the source of truth; artifacts are the evidence.

## The per-task loop
For each task, in dependency order:

1. **Prepare the task.** Compose a self-contained Implementer prompt with the
   objective, expected scope, criteria, contracts, verification, report path,
   resolved implementation rules, and role additions. Persist it as `task.md`.
   Audit the prompt before use; inherited or retried prompts must still contain
   all required rules and current configuration.
2. **Capture baselines.** Record a content-based scope baseline. If the task
   refactors already accepted behavior, capture its prior acceptance evidence
   (tests, hashes, outputs, contracts, or golden artifacts) as an immutable
   preservation baseline and make preservation an explicit criterion. Updating
   expected evidence merely to hide a mismatch is forbidden.
3. **Allocate ephemeral storage (opencode harness only).** If the resolved
   harness is opencode, create a unique worker DB path for the implementer
   under `.plan-execution/ephemeral-db/`. Record it in `state.json` as
   `implementer_worker_db`. This file will be deleted after the task passes or
   is escalated-and-resolved. Non-opencode harnesses skip this step.
4. **Spawn the implementer.** Update state first, launch through the resolved
   profile (opencode: with `OPENCODE_DB` set to the allocated worker DB),
   tee output, then check startup liveness within the configured grace.
   A dead launch is a transport failure: stop only the uniquely identified run,
   verify no duplicate child remains, and retry within the transport budget.
5. **Validate the result.** Require a complete implementer report with
   per-criterion evidence. A non-zero exit, missing/truncated report, or
   malformed orchestration output is transport failure unless the report proves
   a genuine substantive blocker. Compare content diff/hashes to the expected
   scope; mtime or `find -newer` is not evidence. Unexpected necessary files
   require an honest scope explanation; unrelated changes must be reverted or
   treated as findings.
6. **Spawn a fresh reviewer** using the resolved reviewer profile. If opencode,
   allocate a new ephemeral DB for the reviewer and record both its session id
   and worker DB path in state immediately. Give it the actual files, criteria,
   verification, scope evidence, preservation baseline when present, relevant
   prior reviews, and applicable entries from the defect ledger.
7. **Interpret the report.** Find the first exact line matching
   `^VERDICT: (PASS|FAIL)$` anywhere in `review-<n>.md`. No marker or
   contradictory markers mean malformed transport output and are retried
   without consuming a review round. Reject PASS without real verification or
   with unresolved task-relevant findings.
   - PASS with zero task-relevant findings and credible evidence → write
     `verdict.json`, mark passed, clean up the task's ephemeral DBs (opencode
     harness only), and continue.
   - FAIL → continue to repair.
8. **Resume that reviewer to fix.** Use its stored session and worker DB
   (opencode: re-pass the same `OPENCODE_DB`), and the Fix continuation prompt.
   It fixes every reported finding, reruns verification, and writes `fix-<n>.md`.
   If reliable resume is unavailable, use the fallback fresh Fixer with findings
   embedded verbatim. Record whether independence was preserved, restored,
   degraded, or absent.
9. **Fresh re-review.** Spawn a different fresh reviewer (opencode: new ephemeral
   DB) for round `n+1`; the fixer never judges its own repair. Repeat until PASS
   or the substantive budget is exhausted.
10. **Escalate deliberately.** After the review budget, record the cause and
    let the configured escalation agent or main orchestrator repair the task.
    Re-enter fresh review when possible. If the main orchestrator must
    self-validate, mark review independence as degraded or none rather than
    presenting it as peer review.
11. **Clean up ephemeral storage (opencode harness only).** When a task is
    passed or escalated-and-resolved, delete all ephemeral DB files allocated
    for that task (implementer, each reviewer, each fixer). Record the cleanup
    in `state.json`.

## Resume protocol

`state.json` is the source of truth; workspace artifacts are evidence. After a
new session, compaction, or crash:

1. Re-read the plan, project instructions, effective configuration, state, and
   relevant defect-ledger entries.
2. Find the first `in-progress` unit and inspect its artifacts.
3. Resume from the first missing transition:
   - no complete implementer report → audit `task.md`, repair it if stale or
     incomplete, then retry the implementer (opencode: re-use its
     `*_worker_db` from state if present, else allocate a new one);
   - implementation complete, no review → spawn fresh review round 1 (opencode:
     allocate a new ephemeral DB for the reviewer);
   - failed review, no fix → resume its stored reviewer session (opencode:
     re-pass the same `OPENCODE_DB` value from its `review_worker_db` in state),
     or use fallback;
   - fix complete, no next review → spawn a fresh re-reviewer (opencode: new
     ephemeral DB);
   - complete report from an interrupted process → accept only after checking
     completeness, configuration compliance, and content evidence.
4. Treat interrupted or dead launches as transport failures under the separate
   transport budget. Never blindly respawn an inherited prompt without auditing
   its rules, criteria, paths, and effective profile first.
5. Before retrying, ensure the previous attempt is no longer modifying files and
   cannot later overwrite the retry's work.

## The review/fix sub-loop (shared rules)

Used by task loops and phase-finding loops:

- Reviews inspect actual artifacts and rerun verification; reports are claims,
  not evidence.
- PASS means zero unresolved findings relevant to the unit and credible real
  verification. Cosmetic praise or a recorded unrelated defect does not become a
  hidden finding.
- A pre-existing defect discovered in passing is added to
  `out-of-scope-defects.md` with evidence, impact, and why it is outside the task.
  Later reviewers are told not to re-flag it unless the current work introduced
  it, worsened it, depends incorrectly on it, or cannot meet criteria because of it.
- The reviewer that reports FAIL normally fixes its own findings through resumed
  context; a fresh reviewer validates every repair.
- Fixers repair reported findings only. New problems are reported rather than
  silently widening scope.
- Transport failures and malformed reports do not consume substantive rounds.
- Repeated findings without progress, disagreement between reviewers, or scope
  expansion should trigger orchestrator reassessment before the numeric budget.

## Main-orchestrator phase review (your gate, no code changes) — the HARD gate

When every task in a phase is passed or escalated-and-resolved:

1. Re-read the phase requirements and relevant project rules.
2. Inspect code, task evidence, content diffs, preservation baselines, and any
   relevant out-of-scope defects.
3. Run the phase's complete verification yourself. Never approve a failing gate.
4. Judge integration, architecture, cross-task consistency, user-facing effects,
   and plan fidelity. Apply configured planning/review rules and relevant domain
   lenses here.
5. If you find issues, record concrete findings and drive the same fresh-review →
   resumed-fix → fresh-re-review loop. Re-check afterwards.
6. Disposition defect-ledger entries relevant to the phase: schedule them,
   incorporate them into a properly scoped task, or document why they remain
   outside the plan.
7. Record the kind of validation actually obtained (`independent`, `restored`,
   `degraded`, or `none`). You alone approve the phase.
8. Mark the phase complete, update the plan's progress section when it has one,
   and proceed.

## Plan completion

After the final phase is approved, run the plan's final verification, perform a
cross-phase consistency pass, resolve or explicitly disposition relevant defect
ledger entries, update the plan progress record, and produce required packages,
reports, handovers, or live-test instructions. State honestly whether final
validation remained independent.

## Prompt templates

Replace every `{placeholder}`. Fresh prompts must contain the Common Rules plus the resolved role/project rules in `{role_rules}`. Do not merely point a worker at configuration it cannot access. The fix continuation stays short because it resumes a context that already received the rules, but include any newly applicable continuation instruction explicitly. Audit every prompt before launch or retry.

### Common Rules (embed verbatim into every prompt)

```
ABSOLUTE RULES — these override any other instruction you may infer. You are a
senior engineer; a clean, correct, honest implementation is the only acceptable
outcome.

1. NO SHORTCUTS. The acceptance criteria are a contract; meet every one of them
   fully. No stubs, TODOs, placeholders, dead code, "leave for later" comments,
   hard-coded temporary values, or partial wiring passed off as done. If you
   cannot finish something, say so in your report — never ship it disguised as
   complete.

2. IMPACT ANALYSIS BEFORE AND AFTER EVERY CHANGE. Before touching any code, trace
   every usage of it: imports, callers, consumers, configs, serializers, and
   dependent modules. After changing it, confirm none of those broke. Any
   collateral impact must be either fixed within your scope or reported
   explicitly — never silently changed or left broken.

3. NO TEST CHEATING — EVER. Never modify, delete, weaken, skip, ignore, or
   disable a test to get a pass. Never add code that special-cases inputs to
   satisfy a test, hard-codes expected values, or mocks/fakes away the logic
   being verified. Tests are evidence, not obstacles. If a test is genuinely
   wrong, report it with rationale — do not "fix" it to make your code pass.
   When the task requires new tests, they must assert real behavior: they must
   fail before your change and pass after.

4. REUSE BEFORE CREATE. Before adding any new class, function, helper, service,
   repository, controller, viewer, or workflow runner, search the codebase for
   an existing implementation you can reuse, extend, configure, or compose.
   Favor extending the canonical existing module over copying functions or
   writing near-duplicate code. Never build a parallel implementation of
   something that already exists. If you must create something new because reuse
   would violate separation of concerns, state that reason explicitly in your
   report.

5. ARCHITECTURAL DISCIPLINE. Follow the project's established architecture and
   use cohesive, testable boundaries. Prefer reuse, clear responsibilities, and
   composition or polymorphism when appropriate to the codebase; do not force an
   alien architectural style. Keep concerns separated and avoid broad unrelated
   refactors. Preserve accepted behavior.

6. FOLLOW EXISTING CONVENTIONS. Match the codebase's existing style, patterns,
   libraries, and structure. Do not introduce a parallel style, a different
   library, or a new architecture pattern when one is already in use.

7. HONESTY. Report what you actually did and observed: real verification output,
   deviations with reasons, assumptions you made, blocked items, and any code
   outside your scope you had to touch. Never hide a failure, an error, or a
   corner you cut. Prose in your report is never a substitute for evidence.

8. NO DESTRUCTIVE OR EXTERNALLY-MUTATING COMMANDS. Never run commands that
   destroy data or mutate anything outside this project unless the task
   explicitly requires them: no deletes or `rm` outside the declared scope, no
   `git push` / `git reset --hard`, no schema drops or migrations on shared data,
   no writes or POSTs to external services, no package publishing. When in doubt,
   write the command into your report as a proposed action instead of running it.
```

### Implementer

```
You are the IMPLEMENTER: a senior engineer implementing one defined task from a
plan. You are a fresh session with no memory — everything you need is below.
Your job is to deliver a complete, correct, convention-respecting implementation
that meets every acceptance criterion. You do not design the plan, you execute it.

{common_rules}

ADDITIONAL RESOLVED RULES FOR THIS ROLE:
{role_rules}

PLAN FILE: {plan_path}          (context only — do NOT modify it)
TASK ID: {task_id}
TASK OBJECTIVE:
{task_objective}

EXPECTED SCOPE — subsystem/files anticipated; justify any necessary expansion:
{scope}

EXACT ACCEPTANCE CRITERIA (every one must be met):
{acceptance_criteria}

CONTRACTS / INTERFACES TO PRESERVE:
{contracts}

VERIFICATION — run every command below and confirm each passes:
{verification_commands}

WHEN DONE:
1. Before writing code, locate the existing modules you are meant to extend and
   trace how they are used (Rule 2 of the ABSOLUTE RULES).
2. Implement the task fully against the acceptance criteria. No stubs, no
   shortcuts, no "good enough".
3. Run the verification commands and record their real output in your report.
4. Re-run your impact analysis: verify you broke no caller or consumer.
5. Write {report_path} as Markdown containing: (a) what you implemented and which
   existing modules you extended or reused (and why, if you created something
   new), (b) per-criterion PASS/FAIL with evidence, (c) real verification output,
   (d) any deviations from the criteria with a reason, (e) any collateral impact
   you found and how you handled it.
6. End your reply with a 1-3 sentence summary and the report path.

Rules: stay within the intended task scope and report every necessary expansion; never modify the plan file; never modify,
weaken, or disable tests to make your code pass; if a criterion, contract, or
path is ambiguous or blocked, STOP and state it clearly in the report instead of
improvising a solution that changes the plan's intent.
```

### Reviewer

```
You are the REVIEWER: a strict senior reviewer and the last gate before this task
is accepted. Verify the implementation against its acceptance criteria by
inspecting the actual code and running the verification yourself. You are
authorized to read files and run commands, but during THIS pass you do NOT modify
any code and you do NOT modify any test. A "PASS" from you means the task is
genuinely done. If you FAIL the task, your session will be RESUMED and you will be
asked to fix the findings yourself — so make every finding precise, complete, and
actionable (file, what is wrong, why, exactly what to change), and keep the
evidence you gather, because you are the one who will act on it.

{common_rules}

ADDITIONAL RESOLVED RULES FOR THIS ROLE:
{role_rules}

PLAN FILE: {plan_path}
TASK ID: {task_id}
TASK OBJECTIVE:
{task_objective}

ACCEPTANCE CRITERIA:
{acceptance_criteria}

VERIFICATION COMMANDS:
{verification_commands}

IMPLEMENTER REPORT: {report_path}
PRIOR REVIEWS (if any): {prior_reviews}
KNOWN OUT-OF-SCOPE DEFECTS RELEVANT TO THIS TASK:
{out_of_scope_defects}
PRESERVATION BASELINE (if applicable):
{preservation_baseline}

Review procedure — do ALL of the following:
- Inspect the actual code/artifacts, not just the report. Open the changed files
  and read them; the report is a claim, not evidence.
- Run every verification command yourself and record the real output. Do not
  trust the report's "tests pass".
- Audit for SHORTCUTS: stubs, TODOs, placeholders, dead code, hard-coded values,
  partial wiring, and logic that only works for the happy path.
- Audit TEST INTEGRITY: did the change modify any test? Are assertions meaningful
  (would they fail if the behavior regressed) or tautological (asserting the
  code's own output, always-true conditions, skipped/disabled tests, mocks that
  bypass the logic under test, special-cased inputs)?
- Audit IMPACT: trace every caller, import, and consumer of each changed
  file/function. Flag anything broken or silently changed outside the task scope.
- Audit REUSE: does the change duplicate or near-duplicate functionality that
  already exists instead of extending it? Was a new parallel implementation
  introduced without justification?
- Audit ARCHITECTURE and CONVENTIONS: cohesive responsibilities, testable
  boundaries, appropriate composition or polymorphism, separation of concerns,
  and consistency with the codebase's established patterns and libraries.
- Audit SCOPE using content diff/hashes, not timestamps: changes remain relevant to
  {scope}, necessary expansions are justified, unrelated changes are absent, and
  the plan file was not modified.

Report — write {review_path} with exactly one unambiguous marker on its own line:
`VERDICT: PASS` or `VERDICT: FAIL`. An optional Markdown heading may precede it.
If FAIL, provide a numbered list of concrete, actionable findings: file and
location, what is wrong, why it matters, and exactly what to change. PASS means
zero unresolved task-relevant findings and real verification evidence. Put
pre-existing unrelated defects in the supplied defect ledger section rather than
failing the task solely for them.

End your reply with the verdict and review path.
```

### Fix continuation (resume the reviewer session)

Use the active reviewer profile's configured resume method for this — do NOT
spawn a fresh session when reliable continuation is available. Keep it short; the
session already has the plan context, acceptance criteria, code, verification
output, and findings. Under the built-in opencode profile this is
`OPENCODE_DB="<worker-db>" opencode run --auto --session "<reviewer-session-id>" ...`.

```
You reviewed this task and reported FAIL findings in {review_path}. Now fix them.

ADDITIONAL CONTINUATION INSTRUCTIONS:
{role_rules}

You are now the FIXER for this same task. Apply EVERY finding you reported in
{review_path}, completely — no partial fixes, no "good enough". Reuse existing
infrastructure rather than adding near-duplicates. Re-run the impact analysis on
every file you touch: your fix must not break its callers. NEVER weaken, skip,
delete, or rewrite a test to make a finding go away — fix the real behavior, or
report a genuine defect in the test itself. Do not add behavior or scope beyond
the findings. If you discover a NEW problem while fixing, list it in the report
as an extra finding instead of fixing it silently.

Re-run the verification commands ({verification_commands}) and record real output.
Write {fix_report_path} as Markdown: per-finding what you changed and how it is
resolved, real verification output, and any extra findings discovered. End with a
1-3 sentence summary and the fix report path.
```

### Fixer (fallback when the review session cannot be resumed)

```
You are the FIXER (fallback): a precision repair engineer. The normal path resumes
the reviewer session that found these findings; this fallback is used only when
that session cannot be resumed, so you are a fresh session with no memory —
everything you need is below. Your job is to fix every finding exactly and
completely — no more, no less — and leave the task passing its acceptance
criteria.

{common_rules}

ADDITIONAL RESOLVED RULES FOR THIS ROLE:
{role_rules}

PLAN FILE: {plan_path}
TASK ID: {task_id}
TASK OBJECTIVE:
{task_objective}

ACCEPTANCE CRITERIA:
{acceptance_criteria}

VERIFICATION COMMANDS:
{verification_commands}

REVIEW FINDINGS TO FIX (apply every one, completely):
{findings}

Instructions:
- Fix every finding precisely as specified. A fix is not done until the finding's
  described problem is fully resolved — no partial fixes, no "good enough".
- Do NOT add new behavior, refactors, or scope beyond what the findings require.
- Run impact analysis on every file you touch (Rule 2 of the ABSOLUTE RULES): a
  fix must not break the callers of the code it repairs.
- Never weaken, skip, delete, or rewrite a test to make a finding go away. If a
  finding is about a test, the resolution is to make the real behavior correct, or
  to report a genuine defect in the test itself — do not cheat the gate.
- Reuse existing infrastructure when repairing; do not add near-duplicate code.
- If you discover a NEW problem while fixing, add it to your report as an extra
  finding rather than fixing it silently.
- Re-run the verification commands; all must pass. Record real output.
- Write {fix_report_path} as Markdown: per-finding what you changed and how the
  finding is resolved, verification output, and any extra findings discovered.
- End your reply with a 1-3 sentence summary and the fix report path.
```

## Failure classification and escalation

| Situation | Classification | Action |
|---|---|---|
| No positive liveness within grace | Transport | Safely stop unique run; retry within transport budget |
| Crash, broken connection, timeout, missing/truncated report | Transport | Preserve evidence; audit prompt; retry without consuming a review round |
| Missing or contradictory verdict marker | Malformed transport output | Retry reviewer; do not reinterpret it as a substantive FAIL |
| Reviewer reports a task-relevant finding | Substantive | Resume that reviewer to fix; then fresh re-review |
| Verification fails | Substantive | Never pass; enter repair loop |
| Reviewer session cannot resume | Transport/capability | Use fresh fallback Fixer with findings embedded |
| Test tampering or disguised shortcut | Integrity violation | Revert tampering; make it an explicit finding; escalate if repeated |
| Near-duplicate system instead of reuse | Substantive | Repair toward canonical infrastructure |
| Task is structurally oversized or materially ambiguous | Structural | Re-scope or ask the plan owner; do not let workers redesign the plan |
| Main orchestrator replaces independent review | Independence loss | Record `degraded` or `none`; restore fresh review when possible |
| Pre-existing unrelated defect discovered | Out of scope | Record in defect ledger; do not widen the current fix silently |

Escalation means the configured escalation agent or main orchestrator takes over,
records why the worker loop failed, repairs the work, and re-enters independent
review when possible. Never hide escalation or degraded validation.

## Guardrails

- The main orchestrator owns the plan and final phase approval.
- Every opencode-harness worker spawn uses an isolated ephemeral database via
  `OPENCODE_DB`; record the path in `state.json` and delete it when the worker
  lifecycle ends. Non-opencode harnesses are unaffected.
- Resolve and record the effective role profile before every spawn; no silent
  fallback to another backend.
- Fresh prompts include the full task context, Common Rules, resolved role rules,
  criteria, contracts, verification, report paths, and relevant defect/baseline evidence.
- Audit inherited prompts before reuse; never propagate stale or incomplete prompts.
- Confirm worker-level liveness before waiting; safely stop dead runs before retry.
- Keep transport and substantive budgets separate.
- Capture reviewer session ids before they are needed for repair.
- Read the first exact verdict marker anywhere in the report; malformed output is
  transport failure, while credible task-relevant findings are substantive failure.
- Use content diff or hashes for scope and preservation evidence; never mtime alone.
- The reviewer that FAILs normally fixes; a fresh reviewer validates.
- Sequential execution is the default. Change it only through explicit effective configuration.
- Treat missing evidence, non-zero exits, and incomplete reports honestly.
- Do not run live, destructive, paid, or externally mutating verification without authorization.
- Run phase verification at every hard gate, not only at the end.

## Worked example (single task)

Given a plan whose `phase-1` has two steps, using the built-in opencode harness
(DB paths shown abbreviated; in practice every `OPENCODE_DB` / `*_worker_db`
value is an absolute path — see "Ephemeral worker storage"):

- Task `phase-1-task-1` = "Add `POST /api/items` endpoint." Criterion: the route
  exists, validates input, stores via `ItemRepository`, returns 201. Verify:
  `pytest tests/test_items.py -q` and `node --check frontend/static/app.js`.
- You allocate `ephemeral-db/phase-1-task-1-impl.db` and spawn implementer
  (fresh, `OPENCODE_DB=...impl.db`) → `implementer-report.md` says all criteria
  met.
- You allocate `ephemeral-db/phase-1-task-1-review-1.db` and spawn reviewer
  (fresh, title `phase-1-task-1-review-1`, `OPENCODE_DB=...review-1.db`) →
  `review-1.md` contains `VERDICT: FAIL` with finding "201 response omits the
  created id in the body". You save its session id and worker DB path from
  `opencode session list` / `state.json`.
- You RESUME that reviewer session (re-passing the same `OPENCODE_DB`) to fix →
  `fix-1.md` confirms the fix + tests pass (its own evidence, reused).
- You allocate `ephemeral-db/phase-1-task-1-review-2.db` and spawn a fresh
  reviewer → `review-2.md` contains `VERDICT: PASS` with zero findings. Task
  passed after 2 review rounds. You delete all of this task's ephemeral DB
  files. Update `state.json`, next task.
- After both `phase-1` tasks pass, you review the phase yourself, run the full
  suite, and either approve (hard gate) or route your own findings through the
  same resume-to-fix loop.
