---
name: deepseek-and-destroy
description: "Continuously execute a complex implementation plan with a token-frugal expert orchestrator and cheap external worker agents until completion or a genuine human blocker. Defaults to DeepSeek V4 Flash through OpenCode CLI, durable path-only task contracts, independent review/proof, mechanical evidence gates, and harness-adaptive quiescent waiting."
license: MIT
compatibility: codex, claude-code, opencode, and comparable coding harnesses; optional contributed adapters may exist
metadata:
  default-worker-harness: opencode-cli
  default-worker-model: opencode-go/deepseek-v4-flash
  workspace-root: DeepSeekAndDestroy
  pass-standard: zero task-relevant findings
  review-rounds-budget: "5"
  transport-attempt-budget: "5"
  context-checkpoint-due-percent: "65"
  context-compact-before-percent: "75"
  context-hard-ceiling-percent: "80"
---

# DeepSeek and Destroy

> Spend premium context on authority and judgment. Make cheap workers and mechanical
> helpers own the volume.

DSD executes a complex plan continuously until the whole plan is complete or a
human is genuinely required.

The normal topology is:

```text
premium orchestrator (Claude / Codex / OpenCode / other)
        │
        ├─ authority, decomposition, sharp risks, decisions, phase approval
        │
        ▼
external OpenCode CLI worker
`opencode run --model opencode-go/deepseek-v4-flash ...`
        │
        ├─ survey / discovery / implementation / review / repair / verification
        └─ durable evidence
```

The orchestrator harness and worker harness are independent. Claude/Codex native
*subagent* events do not describe the default external OpenCode worker. Harness
adapters only choose the cheapest native way to launch/wait/checkpoint around that
external process.

## 1. Authority boundary

> **Authority reading and judgment belong to the orchestrator. Repository-scale
> investigation belongs to workers. Clerical reconciliation belongs to helpers or
> the Evidence Clerk.**

The orchestrator MUST personally read at new-run/fresh-session intake:

- current user instructions;
- applicable project instructions (`AGENTS.md` or equivalent);
- authoritative plan;
- architecture/design/contracts needed to understand the current phase.

This is governance reading, not repository investigation. Do not let the
worker-authority rule push the orchestrator away from the sources it must judge.

The orchestrator does NOT personally perform repository-wide discovery, caller
tracing, broad source review, test execution, artifact mining, implementation,
repair, or technical re-measurement. Route those to workers.

When a technical fact is disputed, route the exact predicate to a fresh worker or
Evidence Clerk. Do not defensively re-run the investigation in premium context.

Read `orchestrator/CONTROL.md` for the detailed premium-context/trust/wait policy.

## 2. Terminal mission

Continue autonomously until exactly one terminal state is true:

- **COMPLETED** — the whole plan, required verification, delivery/progress records,
  and final continuity artifacts are complete;
- **HUMAN-BLOCKED** — progress requires human authority/access/credential/device/
  environment or worker capacity that automation cannot supply;
- **PAUSED-BY-USER** — explicitly paused;
- **ABANDONED** — explicitly abandoned.

A task PASS, task FAIL, repair, phase PASS, retry, worker crash, wait timeout,
compaction, or fresh session is not a stopping point.

After every material transition:

1. persist reality in `state.json`;
2. persist one exact `next_action`;
3. execute it immediately.

Before yielding an active turn, either a worker is actually active, a persisted
wait/backoff/compaction is active, or the run is terminal.

## 3. Core files

Read only what the current action needs:

- `orchestrator/CONTROL.md` — premium context, trust, narration, waiting, zero-change
  guard, phase barrier;
- `WORKSPACE.md` — run layout/state/evidence/continuity;
- `PROMPTS.md` — compact durable task-contract and path-only handoff format;
- `worker/SKILL.md` — Worker Core;
- `worker/ROLES.md` — single authoritative role boundaries/terminal statuses;
- `worker/BUILD.md` — implementer/fixer;
- `worker/REVIEW.md` — reviewer/verifier/auditor;
- `worker/EVIDENCE.md` — Evidence Clerk;
- `worker/PROOF-PATTERNS.md` — small task-specific proof recipes;
- `HARNESS.md` — separate orchestrator-harness vs worker-harness selection;
- `OPENCODE.md` — default OpenCode CLI worker transport/storage;
- `CLAUDE.md`, `CODEX.md` — orchestrator-specific wait + compaction behavior;
- `COMPACTION.md` — harness-neutral durable context checkpoints;
- `CONFIG.example.md` — optional overrides.

Primary helpers:

- `scripts/prepare_worker_rules.py` — create immutable versioned worker-protocol/rules snapshots;
- `scripts/render_task_contract.py` — render/freeze a numbered contract from compact task slots;
- `scripts/render_worker_prompt.py` — tiny path-only launch prompt;
- `scripts/run_worker.py` — external OpenCode worker launcher/event producer;
- `scripts/wait_worker.py` — portable long blocking wait;
- `scripts/evidence_gate.py` — cheap terminal evidence gate;
- `scripts/check_review_contract.py` — Proof Matrix/fast-path structure;
- `scripts/scope_snapshot.py` — content-hash scope facts;
- `scripts/check_state.py` — control-plane invariants;
- `scripts/decision_packet.py` — extract the compact parent-facing packet;
- checkpoint/harness helpers documented in `COMPACTION.md`/`HARNESS.md`.

Optional contributed adapters are not part of the default design and must not
shape core behavior unless explicitly selected.

## 4. Intake / resume

### New run or fresh orchestrator session

1. Read governing sources personally as required by §1.
2. Create/resume the run per `WORKSPACE.md`.
3. Snapshot/hash plan/authority and update `authority-index.json`.
4. Resolve **orchestrator harness** and **worker harness** separately.
5. Default worker harness/model to OpenCode CLI +
   `opencode-go/deepseek-v4-flash` unless user/config says otherwise.
6. Install/verify only the applicable orchestrator harness adapter.
7. Resolve one external OpenCode run DB outside the project tree when OpenCode is
   the worker harness.
8. Generate immutable worker-rules revision `worker-rules/r0001/` (`WORKER_RULES.md` + `MANIFEST.json` + protocol snapshot) with `prepare_worker_rules.py`; later rule changes create `r0002`, never overwrite `r0001`.
9. Persist the exact worker-rules revision/rules hash/manifest hash/protocol fingerprint in `state.json`, reconcile state, set exact `next_action`, continue.

### Handover trust

`HANDOVER.md` is continuity input, **not technical authority**. Technical claims in
it are prior-session assertions. Before repeating/escalating/building a new
plan-wide decision on one, follow its cited primary/accepted evidence. Missing or
contradictory evidence becomes a worker routing event.

Mechanical helper facts (hashes, file existence, captured exits/process identity)
are trusted only when the **current immutable contract/state binds the exact
artifact/attempt identity**. A stale baseline from an older contract is not a given
fact. Semantic claims are never upgraded merely because they are serialized.

## 5. Plan → phase → independently reviewable task

Before first decomposition of a phase—or after material authority/tree drift—use a
Phase Surveyor when repository measurement is needed.

One worker task should contain one independently reviewable primary unit. One
behavior plus tightly coupled tests can be one unit. Separately reviewable wiring,
generated clients, fixture migrations, artifact/browser batteries, and broad
verification should be split when they can pass/fail independently.

For unfamiliar/cross-cutting work, Discovery first produces a durable construction
brief: exact files/symbols/data flow/call paths, boundaries, exclusions, first edit,
acceptance/proof obligations, verification, and evidence-clerk checks when useful.

For each real behavioral criterion use stable `AC-*` ids. Builder and reviewer see
the same Proof Obligations.

### Hard two-zero-change rule

A substantial mutating attempt that changes none of the intended artifacts and
does not prove the task already satisfied is a decomposition warning.

After **two consecutive zero-intended-change attempts against the same durable
contract**, set `decomposition_required: true`. A third mutating attempt against
that contract is forbidden. Split/re-scope, commission Discovery, or create a
construction-ready brief first.

## 6. Durable contract, not hand-written prompt

Do not retype Common Rules/harness preambles per worker.

Each run has one or more **immutable worker-rules revisions** under
`worker-rules/rNNNN/`; a new revision is created only when stable run-level worker
rules actually change. Each task uses one current immutable numbered contract
revision containing the changing decision surface: unit, objective, <=3 sharp risk
hypotheses, acceptance/proof contract, task-output/evidence expectations, mechanical
references, and an exact `Allowed source changes` list for any role permitted to
mutate project files. The role-specific report path stays in the immutable launch
handoff. Prefer
`render_task_contract.py` so the orchestrator supplies compact slots rather than
re-authoring the Markdown frame.

Use `render_worker_prompt.py`. The resulting launch message is path-only and
normally under ~150 words. If the orchestrator is writing a multi-kilobyte worker
prompt, the flow is wrong.

Stable environment constraints known at run creation belong in the current
immutable worker-rules revision (e.g. a fixed path/shell rule actually required by
that environment), not copied into every prompt. A newly discovered **stable
run-level** constraint creates the next `worker-rules/rNNNN` revision. A changing
task-specific fact belongs in the next task-contract revision. Never rewrite either
kind of historical authority.

## 7. Worker execution / wait

Before a worker attempt:

1. capture the **full project source baseline** for the attempt, excluding only `DeepSeekAndDestroy/`; this is mandatory for terminal evidence gating of mutating and read-only roles;
2. create/freeze the task contract, including exact project-relative `Allowed source changes` for Implementer/Fixer (and an explicitly assigned Clerk progress/documentation file, if any), then render the tiny prompt against one exact worker-rules revision;
3. `run_worker.py` atomically reserves the numbered attempt/report/log, validates the worker-rules manifest, binds the exact launch-prompt, task-contract, worker-rules revision/manifest, and scope-baseline paths/hashes, launches `opencode run` against the external run DB, and writes durable attempt/process information; reusing an attempt/report/event path is forbidden;
4. the orchestrator enters **quiescent wait** using its harness adapter;
5. actual OpenCode process exit produces `terminal.json`; classify that terminal status **before** reading the worker report;
6. only `status=completed` with exit code 0 enters `evidence_gate.py`;
7. the gate recomputes scope against the full tracked + untracked-nonignored Git baseline: every read-only role requires zero project changes; mutating roles may change only the task's exact allowed paths/prefixes; acceptance-relevant ignored/generated outputs need explicit artifact verification;
8. `process-error` after a real worker started enters suspect-change/recovery because it may have mutated source before dying; a pre-start `transport-error` enters transport/availability handling;
9. route a completed-run clerical/provenance/measurement discrepancy to the Evidence Clerk rather than doing forensics in premium context.

Do not periodically poll CPU/logs during normal execution. Process/CPU/log liveness
checks are recovery diagnostics after a real wait/tool inconsistency.

## 8. Worker engineering/proof

Workers read the run-local snapshot of Worker Core + role protocol.

The universal proof doctrine is:

> **An expected outcome is not proof. Show that the named production mechanism was
> reached and caused the result.**

For high-risk criteria, use counterexample-first evidence. Required dimensions such
as cardinality, exact identity, fail-closed rejection, independent authority,
durability across fresh instances, dependency direction, or per-target behavior
must be exercised explicitly.

Workers do not get a routine “reality differs, stop and ask” escape hatch. They
resolve ordinary mismatch from governing authority and build the smallest complete
honest project-aligned solution. Escalation is only for a real authority/access/
ownership boundary.

## 9. Reporting / immutable terminal evidence

Every worker report begins with a compact Decision Packet. Reviewer reports add a
Proof Matrix. Long logs/inventories remain in evidence files.

`DSD_REPORT_STATUS: FINAL` is required for terminal evidence. The launcher may
pre-create a `SKELETON`; a skeleton is never a substantive FAIL/PASS.

After FINAL, worker report/evidence is immutable. Later repair/review uses a new
numbered attempt/report. `run_worker.py` reserves each attempt path atomically so a
duplicate launch cannot race or overwrite prior evidence. Workers must stop any
task-owned background writer before FINAL unless the contract explicitly transfers
it to managed infrastructure. Do not append newer counts or gate findings into old
terminal evidence.

The orchestrator reads Decision Packets by default, not full reports. If one
judgment requires >3 deep evidence/source slices, delegate compression or
checkpoint rather than loading a dossier.

## 10. Mechanical evidence gate / Evidence Clerk

Worker reports are claims until the terminal gate is clean.

`evidence_gate.py` mechanically checks what can be checked cheaply:

- expected report exists and is FINAL rather than skeleton;
- reviewer Proof Matrix/fast-path structure is internally consistent;
- declared verification count arithmetic reconciles, including obvious prose summaries such as `17 tests / 14 pass / 2 fail`;
- every terminal role has a full source baseline; read-only roles changed nothing and mutating roles stayed inside `Allowed source changes`;
- task/report declares whether deeper provenance/tripwire reconciliation is needed.

When the gate returns **CLERK REQUIRED**, launch an Evidence Clerk using the same
cheap worker profile. The clerk may re-derive exact measurements, verify provenance
against the actual task-start baseline, recover a misplaced report from the worker
log, reconcile technical major-log entries, and maintain assigned progress/handover
artifacts. It never approves the task or edits `state.json`.

Before Clerk launch, capture the same full source baseline excluding **only** `DeepSeekAndDestroy/`. The Clerk task itself declares `Evidence Clerk Checks: NONE` so reconciliation does not recurse. A configured project progress/documentation file may be changed only when its exact relative path is also listed in that Clerk task's `Allowed source changes`; product source/tests remain read-only. Gate the Clerk report/scope first and persist that clean gate JSON; only then rerun the original evidence gate with both `--clerk-report` and its matching `--clerk-gate`.

A `CLERK VERDICT: CLEAN` may satisfy **declared clerical claims** such as provenance, tripwire remeasurement, or corrected verification arithmetic when it names every assigned check id. That Clerk report becomes the clerical **overlay** for those IDs: keep the original FINAL immutable, but downstream decisions use the Clerk-corrected values and must not repeat stale originals. CLEAN may not waive a missing/skeleton/malformed FINAL report or any source-scope violation. A misplaced FINAL may be copied byte-for-byte to the canonical path by the Clerk and then re-gated; source movement enters recovery.

The orchestrator does not write technical major-findings essays that can be derived
from worker evidence.

## 11. Review → repair → fresh re-review

Default:

1. implementer;
2. fresh independent reviewer;
3. evidence gate / clerk reconciliation if required;
4. PASS + clean evidence → accept;
5. FAIL → fixer;
6. fresh independent reviewer against repaired state.

Supply at most three sharp falsifiable risk hypotheses beyond the standard review
contract. Attack them by execution, not generic prose.

Avoid redundant expensive proof. Implementer owns terminal verification of its
final state. Reviewer re-runs targeted discriminating checks and explicit
independent requirements. Heavy/full/live verification belongs to a Verification
Worker when assigned. If that verification **generates or mutates an accepted
project artifact**, it is a writer and must finish before the phase write barrier
closes (or run in an isolated temporary location). Post-barrier verification must
be read-only for accepted project artifacts. Any later code/artifact change reopens
the barrier and invalidates evidence it makes stale. Authoritative acceptance
requirements always win.

Fast-path acceptance requires all of:

- fresh independent reviewer PASS;
- every task AC covered and PASS in Proof Matrix;
- required verification PASS;
- source/scope/preservation clean;
- `TASK-RELEVANT DEFECTS: NONE`;
- `FAST-PATH ELIGIBLE: YES`;
- `evidence_gate.py` clean, including any required clerk reconciliation;
- no conflicting accepted evidence.

Then accept immediately. Do not reread code/rerun tests/recompute counts.

## 12. Reopened prerequisites

If an accepted prerequisite materially changes, dependent work becomes
`needs-revalidation` before continuation.

Cheap revalidation determines:

- `still-valid` — contract/proof assumptions remain valid;
- `superseded` — old task contract is invalid; create a replacement.

Do not continue a stale task merely because it already has a report.

## 13. Worker failure / availability

Reportless/forced exit after work began means `suspect-changes`, never “no changes.”
Confirm the process can no longer write, capture mechanical scope evidence, and use
Recovery Auditor when disposition is not obvious.

Provider/quota/auth/transport failure never authorizes premium-orchestrator
implementation. Use the smallest exact-model health probe, persisted backoff, and
configured fallback. Human-block only for genuine external intervention.

## 14. Phase gate

When required phase tasks are provisionally accepted:

1. finish **all phase-owned writers**, including any Verification Worker that creates
   or updates generated/project artifacts; such verification must run before the
   barrier closes or use an explicitly isolated temporary output outside the frozen
   phase state;
2. require those writers' terminal evidence/evidence gates to settle, then close the
   phase **write barrier** and capture the mechanical gate snapshot;
3. run only required **read-only** post-barrier Verification Workers against that
   frozen state;
4. run a fresh Phase Auditor against the same frozen state;
5. orchestrator reads the compact audit/authority and makes the plan-wide decision;
6. findings become immutable bounded remediation tasks;
7. any repair or other phase-owned mutation reopens the barrier and invalidates the
   old phase verification/audit/gate snapshot;
8. finish new writers, re-close the barrier, and repeat read-only verification/audit
   on the new frozen state;
9. approve only when the whole phase contract is clean.

The orchestrator does not implement or do repository-scale phase review. Authority
reading and phase judgment remain its job.

## 15. Context / user communication

Use `COMPACTION.md`. Durable state is authoritative; native summaries are advisory.

Routine launch/wait/pass/fix transitions are not user-visible events. When a host
forces a routine update, use one sentence <=25 words. Expanded prose is only for
material correction, human blocker, consequential decision, phase result, direct
user request, or final completion.

Never estimate token usage. Use exact host counters only when exposed.
