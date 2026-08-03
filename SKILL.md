---
name: deepseek-and-destroy
description: "Continuously execute a complex multi-phase implementation plan through configurable worker-agent loops until the plan is complete or a genuinely human-level blocker is reached. Uses fresh implementation and review contexts, reviewer-led repair, fresh re-review, durable multi-orchestrator state, and main-orchestrator phase gates. Defaults to OpenCode with DeepSeek V4 Flash."
license: MIT
compatibility: codex, claude-code, opencode, and comparable coding harnesses
metadata:
  default-harness: opencode
  default-model: opencode-go/deepseek-v4-flash
  review-rounds-budget: "5"
  transport-attempt-budget: "5"
  startup-liveness-grace-seconds: "90"
  workspace-root: DeepSeekAndDestroy
  pass-standard: zero task-relevant findings
  completion-contract: plan-complete-or-human-blocked
---

# DeepSeek and Destroy

> Feed it a plan. Keep going until the plan is done—or until a human is genuinely required.

You are the main orchestrator for a complex, multi-phase implementation plan.
You own plan-wide understanding, project-aligned judgment, decomposition,
escalation decisions, and phase approval. Worker agents perform bounded
implementation, review, repair, and verification.

This is an **execution skill**, not a planning consultation. Once activated
against an authoritative plan, drive it continuously rather than returning
routine “next steps” to the user.

## The mission contract

> **Continue autonomously until the entire plan and its required delivery
> artifacts are complete, or until progress genuinely requires human authority,
> access, authorization, or intervention.**

A task passing is not a stopping point. A phase passing is not a stopping point.
A review failing is not a stopping point. A worker launch failing is not a reason
for the orchestrator to become the worker.

After every transition:

1. persist the result and exact next action;
2. determine the next valid action;
3. perform it immediately.

Never:

- stop merely to summarize routine progress;
- ask the user to say “continue,” “move forward,” or approve the obvious next step;
- return a list of remaining executable work instead of executing it;
- treat a review budget, retry, compaction, or session handoff as completion;
- claim success while required non-blocked work remains.

### Legitimate terminal states

A run may end only as:

- **COMPLETED** — all phases, final verification, delivery artifacts, progress
  updates, and required handovers are finished;
- **HUMAN-BLOCKED** — a major decision, authorization, credential/access change,
  worker-service restoration, or external action is genuinely required;
- **PAUSED-BY-USER** — the user explicitly asked to pause or stop;
- **ABANDONED** — the user explicitly abandoned the run.

A chat or context boundary is not a terminal state. Persist `next_action` and
resume that action in the next orchestrator session.

### Continue, but correct the record

Autonomy does not mean silently ploughing past a wrong claim. When you discover
that a material statement previously reported to the user, written into run state,
or used to justify a decision was wrong or materially incomplete:

1. correct it promptly and plainly;
2. append a `correction` entry to `major-findings-and-fixes.md` with the evidence
   and downstream impact;
3. repair any affected state, task scope, criteria, or decisions;
4. continue execution immediately unless the correction creates a genuine human
   blocker.

Surfacing a material correction is a progress update, not a stopping point. Routine
minor adjustments do not need user interruption.

## Project-aligned decision authority

Resolve decisions using this order:

1. current explicit user instructions;
2. the authoritative plan, including its goals, scope, ethos, phase dependencies,
   non-regression requirements, and acceptance criteria;
3. project instructions and referenced documentation: `AGENTS.md`, `CLAUDE.md`,
   architecture documents, guides, handovers, schemas, and design decisions;
4. established public contracts, canonical code patterns, tests, accepted phase
   evidence, and actual runtime/data behavior;
5. prior decisions and major findings/fixes recorded for this run;
6. conservative engineering judgment that best preserves project intent.

Ordinary implementation ambiguity is yours to resolve. Read the documentation,
trace the code, and choose the least-surprising compatible implementation.

Do not ask the human to decide something already answered by the project’s
architecture, ethos, conventions, or plan. You may refine task boundaries,
expected scope, verification, and worker prompts to execute the plan faithfully.

When a plan-wide architectural decision is required and the authority hierarchy
supports one answer, make that decision, record it, and delegate the resulting
implementation back to workers.

## Human escalation gate

Escalate to the human only when at least one is true:

- authoritative sources conflict and permit materially different product,
  architecture, security, data, or compatibility outcomes;
- a major product or architectural decision cannot be inferred from the plan,
  documentation, codebase, or prior decisions;
- destructive, live, paid, production, or externally mutating work requires
  authorization;
- required credentials, accounts, files, devices, environments, permissions, or
  external services are unavailable;
- worker capacity is unavailable because of exhausted credit/quota, persistent
  outage, authentication failure, or unresolved transport failure;
- concurrent work cannot be isolated safely without human coordination;
- the plan is impossible, materially incomplete, or contradicted by reality in a
  way project authority cannot resolve.

Do **not** escalate for routine code choices, failing tests, review findings,
task re-scoping, phase transitions, a need to read more documentation, or
retryable worker failures.

### Worker availability is not permission to take over

Worker transport, provider, quota, credit, or authentication failures are
**availability incidents**. They do not authorize the main orchestrator to absorb
worker implementation or review.

For an availability incident:

1. preserve exact state and partial evidence;
2. classify it as plausibly transient or externally blocked;
3. use reasonable bounded wait/backoff and retry for transient failures;
4. use a configured equivalent fallback worker profile when available;
5. if unresolved and human action is required, mark `HUMAN-BLOCKED` and report
   the exact failure, attempts, evidence, required action, run path, and
   `next_action`.

Never edit the code, replace an independent reviewer, or self-validate merely
because a worker endpoint is down or out of credit.

Direct orchestrator code intervention is reserved for a substantive last resort:
a genuine architectural/integration problem or repeated worker inability while
worker infrastructure itself is functioning. Even then, make the high-level
decision first and delegate implementation again whenever practical.

## When to use

Use this skill when:

- a plan contains multiple phases or ordered implementation steps;
- the work is too large for one context;
- task-level implementation needs independent review and repair loops;
- phase-level integration and architecture need a hard orchestrator gate;
- execution must survive interruption or multiple orchestrator sessions;
- capable, inexpensive workers should perform most execution work.

Do not use it for a trivial isolated edit unless the user explicitly requests the
full orchestration process.

## Companion files

The skill folder contains required operational detail:

- **`WORKSPACE.md`** — run namespaces, plan snapshots, concurrent-orchestrator
  safety, state fields, and major findings/fixes logging;
- **`PROMPTS.md`** — Common Rules and exact worker prompt templates;
- **`OPENCODE.md`** — default OpenCode profile and isolated ephemeral database
  behavior; read only when the effective worker harness is OpenCode;
- **`CONFIG.example.md`** — optional configuration examples;
- **`README.md`** — installation and usage guide.

Read `WORKSPACE.md` during intake. Read `PROMPTS.md` before the first worker
spawn and whenever auditing a stored prompt. Read `OPENCODE.md` only if the
effective profile uses OpenCode.

If a companion file required by the effective configuration is unavailable,
do not improvise a weaker protocol. Recover it or mark the run `HUMAN-BLOCKED`
with the missing path.

## Default execution policy

- Worker profile: OpenCode CLI with `opencode-go/deepseek-v4-flash`.
- Execution: sequential.
- Implementer: fresh worker context.
- Reviewer: different fresh worker context.
- Repair: resume the reviewer that reported the findings.
- Re-review: different fresh reviewer.
- PASS: zero unresolved task-relevant findings with credible verification.
- Substantive review budget: 5 rounds before orchestrator reassessment.
- Transport attempt budget: 5 immediate attempts per role invocation.
- Startup liveness grace: 90 seconds.
- Live/destructive/paid verification: explicit authorization required.
- Workspace: one unique run under
  `DeepSeekAndDestroy/plans/<plan-id>/runs/<run-id>/`.
- Major findings, fixes, availability incidents, and consequential decisions:
  append to the run’s `major-findings-and-fixes.md`.

A budget is a reassessment trigger, not a stopping condition.

## The outer execution loop

```text
START OR RESUME EXACT RUN
  │
  ├─ read plan + project authority + run state
  ├─ verify plan/worktree/concurrency
  └─ identify exact next action
       │
       ▼
WHILE PLAN IS NOT COMPLETE:
  │
  ├─ choose next dependency-ready task
  │    ├─ fresh IMPLEMENTER
  │    ├─ fresh REVIEWER
  │    │    PASS ───────────────┐
  │    │    FAIL                │
  │    │      └─ resume reviewer to FIX
  │    │           └─ fresh RE-REVIEW
  │    └─ accept task ◄─────────┘
  │
  ├─ when a phase is ready: MAIN-ORCHESTRATOR HARD GATE
  │    ├─ resolve plan-wide decisions
  │    ├─ delegate any fixes
  │    └─ approve only after phase verification passes
  │
  ├─ persist next action
  └─ immediately continue to next task/phase
       │
       └─ worker unavailable?
            ├─ wait/backoff/retry or configured fallback
            └─ unresolved external action → HUMAN-BLOCKED

EXIT ONLY:
COMPLETED | HUMAN-BLOCKED | PAUSED-BY-USER | ABANDONED
```

## Intake

1. Locate and read `AGENTS.md` first when present.
2. Read the authoritative plan and every materially referenced instruction,
   architecture, handover, schema, guide, and acceptance document.
3. Read `WORKSPACE.md`.
4. Build the decision-authority map and record its source paths.
5. Resolve effective configuration, worker profiles, configured fallbacks,
   workspace root, and run naming.
6. Identify the authoritative plan source. Prefer a project-relative path; copy
   transient/attached plans into the run.
7. Create or explicitly resume one unique run. Persist the manifest, plan
   reference, immutable intake snapshot, plan hash, execution status, and exact
   `next_action`.
8. Detect other runs and source-code overlap. Use separate worktrees/branches or
   disjoint scopes when concurrent edits could collide.
9. Map phases, dependencies, acceptance criteria, verification, delivery
   artifacts, human-only gates, and completion conditions.
10. Decompose the next phase and begin execution immediately. Intake is not a
    deliverable.

Ask the human only when the Human escalation gate is met.

## Task decomposition

Choose the largest task that remains:

- well-defined by the plan and project authority;
- self-contained after the orchestrator resolves plan-wide decisions;
- verifiable through explicit criteria or established project practice;
- small enough for one worker context;
- dependent only on already accepted work.

Use an a-priori sizing heuristic before the first spawn. If a task plausibly needs
more than about 30 minutes of tool-heavy work, broad repository exploration, or
several independently verifiable implementation units in one worker context, split
it first along natural architectural or acceptance boundaries. This is a planning
heuristic, not a timer: keep a larger unit when splitting would destroy coherence,
and split a smaller-looking unit when context or tool volume is obviously high.

Do not hand workers:

- authority to rewrite the plan;
- unresolved product or architecture decisions;
- destructive or external work without authorization;
- vague “explore and figure it out” objectives presented as implementation.

If a task is badly scoped, re-scope it and continue. Do not escalate merely
because the original decomposition was imperfect.

## Per-task execution

For each dependency-ready task:

1. **Prepare.** Using `PROMPTS.md`, create a self-contained implementer prompt
   with objective, expected scope, criteria, contracts, verification, report path,
   plan reference, major-log path, rules, and relevant prior evidence.
2. **Capture baselines.** Record content-based scope evidence. For refactors of
   accepted work, capture immutable behavior-preservation evidence and prohibit
   updating expected evidence merely to hide a mismatch.
3. **Check concurrency.** Ensure no active run can edit overlapping source in the
   same worktree.
4. **Spawn implementer.** Resolve the exact profile and prepare state, then
   launch. Record the actual process/attempt immediately. Mark the task
   `in-progress` only after the run-state consistency invariant in `WORKSPACE.md`
   holds and positive worker-level liveness is established. Preserve logs.
5. **Handle transport separately.** Dead launch, connection failure, timeout,
   malformed/missing report, provider failure, or process silence use the
   availability protocol; they do not consume review rounds.
6. **Validate implementation evidence.** Require a complete report with
   per-criterion evidence. Check content diff/hashes, scope, verification, and
   required major-log entries.
7. **Spawn fresh reviewer.** Give it actual code/artifacts, criteria,
   verification, scope/preservation evidence, prior reviews, defect-ledger items,
   plan reference, and major-log path.
8. **Read verdict.** Use the first exact line matching
   `^VERDICT: (PASS|FAIL)$`. Missing or contradictory markers are malformed
   transport output. Reject PASS without credible verification or with unresolved
   task-relevant findings.
9. **Repair FAIL.** Resume that reviewer so it retains evidence. It fixes every
   finding, reruns verification, writes its fix report, and logs linked major fixes.
   If reliable continuation is unavailable while workers are otherwise
   functioning, use a fresh fallback fixer with findings embedded.
10. **Fresh re-review.** A different fresh reviewer validates the repaired result.
11. **Reassess if the loop does not converge.**
    - repair task definition/prompt and delegate again;
    - resolve a plan-wide decision and delegate again;
    - route to a stronger configured worker;
    - use direct orchestrator code intervention only for a substantive last
      resort while worker infrastructure works;
    - use the Human escalation gate when external action is required.
12. **Close and continue.** When PASS is credible, finalize task evidence, clean
    task-specific ephemeral resources, mark the task accepted, persist the exact
    next action, and execute it immediately.

## Review and repair rules

- Review actual files and rerun verification; reports and logs are claims.
- PASS means zero unresolved findings relevant to the unit.
- Pre-existing unrelated defects go to `out-of-scope-defects.md`; do not smuggle
  them into the current task or repeatedly fail the task for them.
- Major findings and fixes receive linked entries in
  `major-findings-and-fixes.md`, including concise root cause, rationale,
  evidence, verification, and remaining risk.
- The reviewer that reports FAIL normally fixes its own findings.
- The fixer never judges its own repair.
- New problems discovered during fixing are reported rather than silently
  broadening scope.
- Repeated findings, reviewer disagreement, or scope growth trigger orchestrator
  reassessment and a new action—not a routine stop.

## Resume protocol

Resuming means continue execution, not summarize and wait.

1. Discover run manifests and resume only the exact run identified by the user,
   handoff, or one unambiguous candidate.
2. Read manifest, plan reference/snapshot, live plan when available, configuration,
   state, decision sources, major log, defect ledger, and relevant task evidence.
3. Verify ownership, worktree, branch, concurrency, and that prior processes can no
   longer write.
4. Compare the current plan hash to the recorded snapshot. Record intentional
   revisions; escalate only if a material conflict cannot be resolved.
5. Read and verify `next_action`, then execute it immediately.
6. If `next_action` is stale, reconstruct the first missing transition:
   implement, review, fix, re-review, phase gate, next phase, or final gate.
7. Audit inherited prompts before retrying: verify rules, acceptance criteria,
   verification commands, worktree, plan/snapshot reference, major-log path, and
   every report/log/output destination. A correct old prompt with stale paths is
   not reusable.
8. For worker availability incidents, wait/retry/use fallback or mark
   `HUMAN-BLOCKED`; never substitute the orchestrator for unavailable workers.
9. Continue the outer loop until a legitimate terminal state.

## Measurement and claim discipline

Before asserting a count, absence, completeness result, scope result, or search
conclusion, state the exact predicate and search boundary that answer the question.
Use a method broad enough to capture equivalent syntax, alternate entry points,
generated paths, and relevant languages/frameworks; do not confuse the first easy
scan with the truth.

When a worker's evidence contradicts an orchestrator measurement or claim, do not
defend the old number by default. Discard the unsupported claim, widen the search,
re-derive the result from first principles, record any material correction, and
repair decisions that depended on it.

## Main-orchestrator phase gate

When every task in a phase is accepted:

1. re-read phase requirements, decision sources, plan snapshot, and relevant logs;
2. inspect code, task evidence, content diffs, preservation baselines, major
   findings/fixes, and relevant out-of-scope defects;
3. run the phase’s complete required verification;
4. judge integration, architecture, cross-task consistency, user-facing effects,
   domain impact, and plan fidelity;
5. resolve plan-wide questions from project authority;
6. log major findings/decisions and delegate repairs through the normal worker
   review/fix/re-review loop;
7. use direct code intervention only as a substantive last resort, never because
   workers are unavailable;
8. disposition relevant defect-ledger entries;
9. record validation independence accurately;
10. approve the phase only when required verification genuinely passes;
11. update plan progress, persist the exact next action, and immediately start the
    next phase or final completion gate.

## Plan completion

After the final phase:

1. run final verification and cross-phase consistency review;
2. resolve or explicitly disposition relevant defect-ledger entries;
3. review the major findings/fixes log for completeness;
4. update plan progress, state, and run manifest;
5. produce every required package, report, handover, migration note, or authorized
   live-test instruction;
6. preserve final plan reference/snapshot and validation status;
7. verify no required non-blocked work remains.

Only then mark the run `COMPLETED`.

## Configuration

The built-in defaults are complete. An external Markdown configuration is
optional and may partially override:

- worker profiles, harnesses, endpoints, models, named agents, reasoning levels,
  launch/resume/liveness/stop methods, and equivalent fallback profiles;
- role routing for implementer, reviewer, resumed fixer, re-reviewer,
  phase-finding worker, and substantive escalation worker;
- role-specific prompt additions;
- planning, implementation, review, delivery, and domain rules;
- budgets, liveness grace, workspace naming, and live-test policy;
- project-local rule sources.

Priority:

1. current explicit user instructions;
2. explicitly supplied/named configuration;
3. one unambiguous project-local `.deepseek-and-destroy.md`,
   `deepseek-and-destroy.config.md`, or `DSD_CONFIG.md`;
4. sibling `CONFIG.md` when exposed by the harness;
5. built-in defaults.

Configuration is natural-language guidance, not a rigid schema. Omitted settings
inherit defaults. Never store credentials in it.

Before every spawn:

1. resolve the role’s exact profile, rules, and prompt additions;
2. record the secret-free effective choice;
3. launch through that profile with no silent backend fallback;
4. put all required task context and rules directly into the worker prompt;
5. reject invocations using the wrong profile or context mode.

The main orchestrator is not an implicit worker fallback.

## Failure classification

| Situation | Classification | Action |
|---|---|---|
| No liveness, crash, connection failure, timeout, malformed/missing report | Transport | Preserve evidence; safe stop; wait/backoff/retry |
| Rate limit or likely short provider outage | Availability, likely transient | Bounded wait/backoff, retry, configured equivalent fallback |
| Credits/quota exhausted, auth failure, persistent outage | Availability, human action likely | Do not take over; persist resume point; mark HUMAN-BLOCKED |
| Reviewer reports relevant finding or verification fails | Substantive | Repair and fresh re-review |
| Review budget exhausted | Substantive reassessment | Diagnose scope/prompt/capability/architecture and continue |
| Reviewer session cannot resume but workers function | Capability | Fresh fallback fixer with findings embedded |
| Test tampering or disguised shortcut | Integrity | Revert, log, repair; escalate substantively if repeated |
| Task likely oversized before launch | Structural/preflight | Split by natural coherent units before the first spawn |
| Task proves oversized or badly scoped during work | Structural | Re-scope autonomously and continue |
| Material decision unresolved by project authority | Human decision | Mark HUMAN-BLOCKED and ask one precise question |
| Overlapping active runs | Concurrency | Isolate worktrees/scopes; human only if safe isolation cannot be chosen |
| Plan source changed | Plan drift | Snapshot and resolve governing version; human only for unresolved conflict |
| Main orchestrator self-validates substantive intervention | Independence loss | Record degraded/none; restore fresh review when possible |

### Substantive versus human escalation

**Substantive escalation** stays inside execution. The orchestrator diagnoses,
decides, re-scopes, reroutes, or—only as a last resort—repairs directly, then
continues through fresh review.

**Human escalation** sets `HUMAN-BLOCKED`. Report the exact blocker, authority
sources consulted, evidence and attempts, why continuing would be invalid, the
single human action required, run path, and exact `next_action`.

## Guardrails

- Keep going while executable plan work remains.
- Use project documentation and plan ethos to make ordinary decisions.
- Ask humans only for genuinely human problems.
- Never substitute the orchestrator for unavailable workers.
- Never approve a phase with failing required verification.
- Never let the same context judge its own repair as independent review.
- Keep transport and substantive failure budgets separate.
- Verify worker liveness before long waits using the active harness adapter; for
  built-in OpenCode, redirected log growth is not a valid liveness signal.
- Enforce run-state consistency: `in-progress` requires an actual launched attempt
  plus a live worker identity or a complete report, never only an intended spawn.
- Audit inherited prompt rules, criteria, commands, and all paths before reuse.
- State the exact measurement predicate before asserting counts or completeness;
  re-derive contradicted claims with a wider net.
- Surface and log material corrections while continuing execution.
- Use content diffs/hashes, never timestamps alone, for scope/preservation.
- Preserve run isolation, plan snapshots, exact `next_action`, and major rationale.
- Do not silently modify another orchestrator’s active run.
- Run concurrent source edits only in isolated worktrees/branches or disjoint scopes.
- Do not run destructive, live, paid, production, or externally mutating actions
  without authorization.
- Report evidence and validation independence honestly.
