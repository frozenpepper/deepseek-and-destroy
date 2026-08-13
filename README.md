# DeepSeek and Destroy

> Give a premium coding agent the plan. Cheap specialist workers do the repository-scale work; the parent keeps authority and judgment.

DeepSeek and Destroy (DSD) is a long-horizon plan-execution skill for Codex, Claude Code, OpenCode, Kilo Code, and comparable coding harnesses. The default worker backend is external OpenCode using `opencode-go/deepseek-v4-flash`.

## Core model

```text
premium parent
  authority / decomposition / decisions
        │
        ▼
cheap technical worker
  natural engineering report + evidence
        │
        ▼
objective integrity gate
  hashes / lifecycle / exact source movement
        │
        ├── clear bounded result ─────────► parent
        │
        └── costly/unclear to interpret ─► Evidence Clerk ─► parent
```

Python proves facts it can know exactly. It does **not** decide whether worker prose proves an acceptance criterion, contains a defect, or semantically means PASS/FAIL.

The Evidence Clerk is an optional, always-project-read-only semantic adapter. It interprets and compresses evidence already produced; it cannot invent missing proof, rerun technical verification, repair code, waive integrity failures, approve work, or recurse into another Clerk.

## Normal task loop

```text
Implementer
    ↓
fresh Reviewer
   ↙     ↘
PASS    FAIL
 │        ↓
 │      fresh Fixer
 │        ↓
 │      fresh Reviewer
 └────────┘
    ↓
parent consumes bounded Reviewer surface
    ↓ only if useful
Evidence Clerk
    ↓
parent accepts / routes / escalates
```

A Clerk is **not** inserted between specialists by default. Implementer/Fixer evidence normally goes straight to the fresh Reviewer. Missing technical evidence goes to a targeted Verification/Review worker, not a formatting retry.

Every project mutation still requires fresh independent Reviewer provenance before acceptance.

## Context economy

The always-relevant parent doctrine is `SKILL.md`. Detailed material is cold-loaded only when needed:

- `WORKSPACE.md` — state, evidence, recovery, concurrency, barriers;
- `CODEX.md`, `CLAUDE.md`, `KILO.md` — parent harness adapters;
- `OPENCODE.md` — external worker transport/recovery;
- `COMPACTION.md` — checkpoint/resume;
- `PROMPTS.md` — task/handoff authoring reference.

Workers receive only:

```text
WORKER_RULES.md                 run facts
worker/COMMON.md                universal worker behavior
worker/roles/<role>/SKILL.md    exactly one specialist role
task contract                   exact task semantics
PROOF-PATTERNS.md               only when explicitly named by that task
```

Unrelated roles and manuals are never loaded by default.

## Parent interface

Task semantics are authored as compact JSON and rendered into an immutable contract. Routine attempt bookkeeping is mechanical:

```text
dsd_attempt.py launch …
dsd_attempt.py wait …       # detached workers only
dsd_attempt.py gate …
```

`launch` derives a self-contained attempt directory, scope baseline, prompt/report/log paths, immutable reservation, worker launch, and state binding. `gate` checks only objective integrity; add `--surface` only at a parent semantic-consumption boundary. Intermediate specialist gates therefore inject no worker prose into premium context.

If the requested bounded prefix is insufficient for a parent decision, run the optional Evidence Clerk over the exact immutable contract/report/gate. The parent then records acceptance with `dsd_state.py accept-task`.

The premium parent should not hand-edit `state.json`, serialize dozens of launch arguments, inspect parser regexes, or poll workers in chat context.

## Self-contained attempts

New attempts live at:

```text
phases/<phase>/tasks/<task>/attempts/<role>-<n>/
  launch-prompt.txt
  scope-baseline.json
  launch-reservation.json
  attempt.json
  report.md
  worker.log
  terminal.json
  scope-diff.json
  evidence-gate.json
```

`launch-reservation.json` is the immutable attempt authority. Lifecycle records bind back to it rather than duplicating authority fields.

## Worker reports are natural language

A long worker report is evidence, not a machine wire protocol. Mechanical acceptance does not require:

- `Verdict: PASS` or any other magic line;
- a FINAL marker;
- a Proof Matrix table;
- repeated AC identifiers;
- a special defects section;
- machine-parseable test arithmetic.

Workers are encouraged to lead with a concise conclusion and then provide real evidence. If semantic mapping is expensive or ambiguous, the Clerk interprets it. If proof is genuinely absent, it remains absent.

## Deterministic safeguards that remain

DSD deliberately retains deterministic mechanisms for facts where they are stronger than LLM inference:

- immutable contract/rules/evidence hashes;
- exact attempt reservation and real terminal lifecycle;
- content-based changed-path baselines;
- read-only-role write violations;
- writer changes outside exact allowed paths;
- declared Git-ignored/load-bearing trees;
- reportless/suspect-change Recovery;
- external OpenCode DB isolation outside the repository;
- phase write barrier / frozen phase evidence;
- governing-authority continuity across compaction/resume;
- fresh Reviewer provenance after mutation.

A clean integrity gate means **safe to interpret**, not “the engineering passed.”

## Roles

- **Phase Surveyor** — measured current state before decomposition.
- **Discovery** — traces one unfamiliar subsystem and writes a durable construction brief.
- **Implementer** — builds one bounded change.
- **Fixer** — repairs explicit supplied findings.
- **Reviewer** — fresh adversarial read-only review.
- **Verification** — establishes one technical predicate; it may write only exact generated/project paths explicitly authorized by the contract.
- **Recovery** — read-only forensic disposition of suspect interrupted changes.
- **Phase Auditor** — fresh whole-phase audit against a frozen phase state.
- **Evidence Clerk** — read-only interpretation/reconciliation/compression of existing evidence.

The role files are Agent-Skill-compatible `SKILL.md` files, but production DSD selects their exact immutable paths explicitly. It does not depend on probabilistic native skill discovery.

## Phase completion

After task work finishes:

```text
finish all phase writers
→ close/freeze phase barrier
→ required read-only post-barrier verification
→ fresh Phase Auditor
→ premium parent phase decision
```

Any later phase mutation invalidates the frozen evidence and reopens the barrier.

## Waiting and failure recovery

External workers emit `terminal.json` when the actual worker process ends. Waiting is quiescent: no terminal event means wait again, without model-driven log/CPU/repository polling.

If a worker dies after starting, source changes are **suspect**, not assumed absent. Recovery inspects the immutable baseline/diff and recommends disposition before retry or adoption.

Worker/provider availability problems do not turn the premium parent into the implementation workforce.

## Installation

Copy the whole `deepseek-and-destroy` directory into the skills directory supported by your parent harness. The package includes first-class adapters for Codex, Claude Code, OpenCode, and Kilo Code.

No configuration file is required for the default external OpenCode worker profile. `CONFIG.example.md` shows optional overrides. Do not store credentials in DSD configuration.

## Quick start

```text
Use DeepSeek and Destroy to execute the authoritative plan at <path>.
Continue autonomously until complete or genuinely human-blocked.
```

For long runs, DSD preserves exact state/evidence and one `next_action`. A fresh parent reads live state first and executes a mechanical next action immediately; HANDOVER/session history are cold continuity, not a reason to reconstruct the run.
