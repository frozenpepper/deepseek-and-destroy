---
name: deepseek-and-destroy
description: "Execute complex implementation plans with a token-frugal premium orchestrator, cheap specialist workers, fresh adversarial review, and mechanical provenance/scope gates."
license: MIT
compatibility: codex, claude-code, opencode, kilo, and comparable coding harnesses
metadata:
  default-worker-harness: opencode-cli
  default-worker-model: opencode-go/deepseek-v4-flash
  workspace-root: DeepSeekAndDestroy
  pass-standard: zero task-relevant findings
  review-rounds-budget: "5"
  transport-attempt-budget: "5"
---

# DeepSeek and Destroy

> Parent owns authority/judgment. Workers own technical volume. Python proves facts,
> not meaning. Clerk interprets evidence when that saves premium context.

## Parent rules

Own: current user/project/plan authority, decomposition, acceptance, architecture
choices, escalation. Delegate repository survey, implementation, repair, adversarial
review, bounded verification, and recovery. Never redo technical work or serialize
routine contracts/state/launch plumbing in premium context.

Persist reality plus one exact `next_action`. Continue until `COMPLETED`,
`HUMAN-BLOCKED`, `PAUSED-BY-USER`, or `ABANDONED`.

## Load only when needed

Normal execution uses this file only. Lazy-load:

- active harness adapter (`CLAUDE.md`, `CODEX.md`, `KILO.md`, etc.) for host wait/hooks;
- `WORKSPACE.md` for recovery, state/provenance, phase barriers;
- `PROMPTS.md` for manual contract/helper details;
- `OPENCODE.md` for transport/provider/DB diagnostics;
- `COMPACTION.md` only for checkpoint/rehydration.

Workers receive only immutable run rules + `worker/COMMON.md` + one role skill + task.
`PROOF-PATTERNS.md` is loaded only when the task names a recipe.

## Start / resume

Identify project root, authoritative plan, applicable project instructions, and parent
harness. Read enough authority personally to decompose the current phase. Create/bind
run state, snapshot worker rules with `prepare_worker_rules.py`, then delegate discovery
when repository mapping is needed.

`state.json` + immutable accepted evidence are execution authority. Chat/HANDOVER/
progress prose are continuity aids.

## Task contracts

One task = one bounded semantic objective a fresh Reviewer can prove/disprove. Create
immutable contracts with:

```bash
python3 <skill>/scripts/render_task_contract.py --spec <contract.json>
```

Keep only needed fields: objective; governing inputs/authority; exact `Allowed source
changes`; stable `AC-*`; proof obligations; optional proof recipe; targeted verification;
exclusions; ignored/load-bearing `Extra scope inventory`.

Use `dsd_state.py` for routine state transitions. After two substantial Implementer/
Fixer zero-change attempts without proof the task was already satisfied, set
`decomposition_required` and rediscover/split/rescope before another writer.

## Normal worker lifecycle

Parent chooses phase/task/role, then:

```bash
python3 <skill>/scripts/dsd_attempt.py launch \
  --state <run>/state.json --phase <phase> --task <task> --role <role>
```

This mechanically derives paths/config, captures scope, renders the minimal prompt,
reserves/launches the worker, and binds state. It never chooses semantics, retries, or
acceptance.

Wait for that exact attempt's terminal event using the active harness. Do not poll logs,
CPU, or repository state for reassurance. A wait timeout without a terminal event is a
non-event: wait again.

Then:

```bash
python3 <skill>/scripts/dsd_attempt.py gate \
  --state <run>/state.json --phase <phase> --task <task>
```

The gate proves only objective attempt facts: immutable bindings/hashes, transport,
report bytes present/not launcher skeleton, worktree movement, read-only isolation, and
write boundaries. It returns a bounded non-authoritative report surface.

## Semantic boundary

Worker reports are evidence-rich prose, not a machine protocol. Formatting, headings,
`Verdict:` wording, AC labels, tables, or arithmetic prose never determine acceptance
and never justify rerunning expensive technical work.

At a parent decision boundary:

1. read the bounded report surface;
2. if clear and small, judge it against the contract;
3. if long/awkward/ambiguous or AC mapping is costly, launch **one Evidence Clerk** with
   exact source report + mechanical gate as immutable evidence inputs;
4. consume the Clerk's small semantic packet;
5. if substance is missing, commission only the missing technical predicate.

Evidence Clerk is always project-read-only. It may interpret, map, reconcile clerical
inconsistencies, and compress existing evidence. It may not run missing technical proof,
repair code, waive mechanical failures, invent evidence, approve work, or Clerk a Clerk.

## Routing

Typical mutation loop:

```text
Implementer → mechanical gate → fresh Reviewer
                               ↙            ↘
                             PASS           FAIL → Fixer → fresh Reviewer
```

Do not add Clerk between workers when the parent does not need to consume that report.
Use Discovery/Phase Surveyor before work when mapping is needed. Verification owns one
predicate and is read-only unless its contract explicitly grants generated/project
paths. Recovery is read-only forensics. Phase Auditor is fresh and read-only.

Every project mutation requires fresh independent review; no self-approval. Accept only
when the parent has trustworthy semantic evidence that all ACs are established, required
verification is clean, no task-relevant defect remains, and the mechanical gate is clean.

## Exceptional paths

Missing/unchanged report after completed transport: recover exact-attempt evidence first;
do not rerun the technical worker for formatting/serialization. Scope/authority/lifecycle
uncertainty goes to Recovery. Load `WORKSPACE.md` only for these cases and for phase
barrier/revalidation rules.

Keep routine launch/wait/pass/fix chatter silent. Surface material findings, decisions,
blockers, phase results, requested updates, and completion. Never estimate token usage
when the host exposes no exact counter.
