# DeepSeek and Destroy

> **Feed it a plan. It keeps spawning, reviewing, fixing, proving, and moving
> forward until the plan is actually done.**

DeepSeek and Destroy (DSD) is a portable coding-agent skill for executing large,
multi-phase implementation plans while keeping expensive orchestrator context for
plan-wide judgment instead of repository-scale grunt work.

The main orchestrator:

- understands the authoritative plan and project architecture;
- decomposes phases into independently reviewable units;
- routes workers and resolves genuine plan-wide decisions;
- accepts credible independently reviewed work;
- owns phase gates and human escalation.

Cheap workers:

- survey current state;
- discover unfamiliar subsystems;
- implement bounded changes;
- run expensive verification;
- independently review;
- repair findings;
- recover reportless/partial work;
- synthesize phase evidence.

The rule is:

> **Workers execute and establish technical facts. The orchestrator routes,
> decides, and approves.**

## The loop

```text
plan
  │
  ▼
Phase Survey / Discovery when needed
  │
  ▼
bounded task + AC IDs + Proof Obligations
  │
  ▼
Fresh IMPLEMENTER
  │
  ▼
Fresh REVIEWER
  │
  ├── PASS + complete proof contract ──► accept task
  │
  └── FAIL ──► fixer ──► fresh reviewer

all phase tasks accepted
  │
  ▼
Verification Workers + fresh Phase Auditor
  │
  ▼
main-orchestrator phase gate
  │
  ├── findings ──► remediation worker loops
  └── clean ─────► next phase
```

It continues automatically until the complete plan is done, a real human blocker
is reached, the user pauses it, or the user abandons it.

A task finishing is not a reason to stop. A phase finishing is not a reason to
stop. A review failure is normal workflow. A context window ending is not project
completion.

## Why the worker proof layer exists

Long field runs exposed a nasty class of failure: a test can be green for the
**wrong reason**.

Examples include:

- a negative test aborting before the production guard it claims to test;
- a single-member fixture hiding a multi-member "last parent wins" bug;
- a fail-closed approval gate whose approval is copied from the object being gated;
- aggregate counts hiding incorrect per-entity identity;
- same-instance continuation being mistaken for durable restart behavior.

DSD therefore gives workers a compact proof discipline in `worker/`.

The central rule is:

> **An expected outcome is not proof. Establish why the outcome occurred and that
> the production mechanism named by the acceptance criterion was actually reached.**

Non-trivial tasks use stable acceptance IDs (`AC-001`, etc.) and compact **Proof
Obligations**. Implementer and reviewer receive the same obligations.

Reviewer reports contain a **Proof Matrix** with one row per AC:

```markdown
| AC | Mechanism reached | Positive | Negative | Dimensions exercised | Counterexample defeated | Result |
|---|---|---|---|---|---|---|
| AC-001 | YES: validator reached | PASS | PASS | multi-member | YES | PASS |
```

For risky criteria the reviewer asks:

> What plausible broken implementation could still make the current evidence look
> green?

If the evidence would not catch that counterexample, the criterion is not proven.

## Small proof recipes, not giant checklists

`worker/PROOF-PATTERNS.md` currently defines five optional recipes:

- **NEGATIVE-GATE** — realistic allowed + rejected paths and independent authority;
- **CARDINALITY** — exercise `>1` members and assert individual mappings;
- **IDENTITY** — structural relationships derive from canonical identity;
- **DURABILITY** — cross the real restart/persistence boundary;
- **DERIVED-EVIDENCE** — distinct green claims require their actual contractual
  predicates.

Discovery/Survey workers recommend only the patterns that actually apply. The
orchestrator forwards those durable recommendations rather than hand-authoring an
expensive review theory.

## Fast-path acceptance without paying twice

A credible fresh reviewer PASS is meant to save premium-model work.

The task fast path requires:

```text
fresh independent reviewer PASS
+ complete Decision Packet
+ Proof Matrix covers every AC and all rows PASS
+ TASK-RELEVANT DEFECTS: NONE
+ required verification PASS
+ scope/preservation clean
+ no conflicting evidence
+ structural review-contract check PASS
= accept and continue
```

The orchestrator does **not** then reread the code, rerun tests, or repeat the
review. If something is doubtful, it sends the exact question to another fresh
worker.

`scripts/check_review_contract.py` checks structural completeness and internal
consistency. It does not pretend to judge software semantics.

## Defect honesty

A correctness defect affecting a required acceptance dimension cannot be relabeled
as a "known limitation", technical debt, cleanup, or future work to preserve PASS.
It is a task failure.

Intentional downstream contract consequences may be scheduled as concrete closure
tasks, but the containing phase remains blocked until maintained consequence suites
are restored.

When a prerequisite is reopened, dependent tasks become `needs-revalidation`.
They are either confirmed `still-valid` or marked `superseded` and replaced; stale
contracts are not allowed to continue silently.

## Worker instructions

The worker protocol is intentionally small:

```text
worker/
├── SKILL.md             # proof/evidence kernel
├── BUILD.md             # implementer/fixer discipline
├── REVIEW.md            # reviewer/verifier/auditor discipline
└── PROOF-PATTERNS.md    # optional proof recipes
```

Every worker gets:

1. Common Rules from `PROMPTS.md`;
2. Worker Core;
3. the applicable Build/Review role protocol;
4. only relevant proof-pattern excerpts;
5. exact bounded task paths, ACs, Proof Obligations, verification and report paths.

This is prompt assembly, not a new premium-orchestrator investigation job.

## Task sizing and discovery

The strongest field predictor of worker failure has been **too many independently
reviewable units in one worker context**.

Default to one unit per task. One behavioral change plus directly coupled tests can
be one unit. Separately reviewable wiring, generated clients, fixture migrations,
artifact audits, browser batteries, and full-suite runs are usually separate.

For unfamiliar subsystems, Discovery first produces a durable construction brief:

- exact files/symbols/call paths;
- construction boundaries and wiring;
- exclusions;
- first edit/checkpoint;
- acceptance/verification;
- Proof Obligations and recommended proof patterns.

The implementer verifies local assumptions and starts writing instead of
rediscovering already-settled architecture.

## Durable state and crash recovery

Each execution owns a run under:

```text
DeepSeekAndDestroy/plans/<plan-id>/runs/<run-id>/
```

The run keeps:

- plan reference + immutable plan snapshots;
- `state.json` with exact `next_action`;
- compact `HANDOVER.md`;
- authority index;
- task reports/verdicts;
- Proof Matrices;
- phase audits/remediation plans;
- major findings/fixes log;
- context checkpoints.

`state.json` must describe reality before every worker launch. HANDOVER stays
compact and is updated whenever resume semantics materially change.

A reportless/dead worker leaves a **suspect tree**, not an assumption of no changes.
DSD captures content evidence and sends non-obvious recovery to a fresh Recovery
Auditor before retrying.

## OpenCode worker storage

Default workers use OpenCode CLI with:

```text
opencode-go/deepseek-v4-flash
```

OpenCode workers use **one disposable external SQLite DB per DSD run**, never a DB
inside the project/worktree and never the user's normal interactive DB.

This provides:

- clean user history;
- reviewer/fixer session resume;
- no project-copy self-scan of an actively-written DB;
- simple terminal cleanup.

Default sequential execution uses one run DB. Explicit parallel execution uses one
external DB per concurrency lane.

OpenCode PID files contain raw digits only. DSD reconciles an ambiguous possibly-live
worker before relaunch; duplicate workers on one task are an incident.

See `OPENCODE.md`.

## Kilo Code

Kilo Code is supported through native subagents. DSD installs two worker profiles:

- `dsd-mutating-worker` — implementer/fixer;
- `dsd-readonly-worker` — survey/discovery/verification/review/audit roles.

The role-specific DSD prompt still carries the Worker Core and relevant proof
protocol. See `KILOCODE.md` and `scripts/install_kilo_agents.py`.

## Context checkpoints

Long orchestrator sessions do not trust native compaction summaries as the sole
continuity mechanism.

Default policy:

- checkpoint due at 65% when measurable;
- compact at next safe boundary, normally before 75%;
- no new substantial phase-level reasoning at 80%;
- fallback safe-boundary checkpointing when percentage is unavailable.

After compaction/session replacement, DSD rehydrates the skill, state, handover,
checkpoint and plan identity, validates live workers, runs `verify-resume`, and
continues the exact stored next action.

## Install

Copy the complete repository folder into the skill location used by your harness.
Keep the folder intact:

```text
deepseek-and-destroy/
├── SKILL.md
├── README.md
├── WORKSPACE.md
├── PROMPTS.md
├── HARNESS.md
├── COMPACTION.md
├── CODEX.md
├── CLAUDE.md
├── OPENCODE.md
├── KILOCODE.md
├── CONFIG.example.md
├── LICENSE
├── worker/
│   ├── SKILL.md
│   ├── BUILD.md
│   ├── REVIEW.md
│   └── PROOF-PATTERNS.md
├── adapters/
└── scripts/
    ├── check_state.py
    ├── check_review_contract.py
    ├── context_checkpoint.py
    ├── decision_packet.py
    ├── detect_harness.py
    ├── install_compaction_adapter.py
    ├── install_kilo_agents.py
    ├── opencode_probe.py
    └── scope_snapshot.py
```

## Quick start

```text
Use DeepSeek and Destroy to execute the authoritative plan at
DOCS/Plans/implementation-plan.md.

Continue autonomously until the complete plan is finished or a genuine
human-level blocker is reached. Complete all non-live work before any final
live-test gate.
```

That is enough when defaults fit.

## Optional configuration

Use `CONFIG.example.md` to override only what you need:

- worker harness/model/endpoint;
- role routing and fallback workers;
- review/transport budgets;
- project-specific rules and domain lenses;
- live/destructive test policy;
- context checkpoint behavior.

The main orchestrator is never an implicit fallback worker.

## License

MIT. Use it, modify it, fork it, improve it, redistribute it, sell things built on
it, or strap it to whatever agent harness you enjoy. See `LICENSE`.

Copyright (c) 2026 FrozenPepper.
