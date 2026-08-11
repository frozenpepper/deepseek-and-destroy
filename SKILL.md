---
name: deepseek-and-destroy
description: "Continuously execute a complex implementation plan with a token-frugal expert orchestrator and cheap external worker agents until completion or a genuine human blocker. Defaults to DeepSeek V4 Flash through OpenCode CLI, durable path-only task contracts, specialist role skills, independent review/proof, mechanical evidence gates, and harness-adaptive quiescent waiting."
license: MIT
compatibility: codex, claude-code, opencode, kilo, and comparable coding harnesses
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

> Spend premium context on authority, decomposition, and consequential judgment.
> Make cheap specialist workers and mechanical helpers own the volume.

DSD continuously executes a complex plan until the plan is complete or a genuine
human blocker exists. The parent harness and worker harness are independent; the
default worker is an external OpenCode + DeepSeek process whose role DSD selects
explicitly.

## 1. Parent authority and economy

The premium orchestrator personally owns:

- current user intent/corrections and applicable project instructions;
- the authoritative plan and governing architecture/contracts needed for the
  current phase;
- decomposition, task boundaries, consequential decisions, task acceptance, and
  phase approval.

It does **not** personally do repository-wide discovery, implementation, repair,
source review, test execution, artifact mining, or technical remeasurement. Cheap
workers own that volume. Mechanical/provenance/reconciliation work belongs to
helpers or Evidence Clerk. When a technical predicate is disputed, commission the
exact cheap check rather than re-investigating in premium context.

Continue until exactly one terminal state is true: **COMPLETED**,
**HUMAN-BLOCKED**, **PAUSED-BY-USER**, or **ABANDONED**. Task results, repairs,
worker failures, wait timeouts, compaction, and fresh sessions are not terminal.
After every material transition persist reality plus one exact `next_action` and
execute it. An active turn yields only while a worker/wait/backoff/compaction is
actually active.

## 2. Load only what the current actor needs

Parent-facing:

- `WORKSPACE.md` — durable run/state/evidence/recovery/barrier details;
- `PROMPTS.md` — task contracts and explicit-path handoffs;
- active harness adapter (`CODEX.md`, `CLAUDE.md`, `KILO.md`, etc.);
- `OPENCODE.md` only for worker transport/recovery details;
- `COMPACTION.md` only for checkpoint/resume details.

Worker doctrine is not parent doctrine:

- `worker/COMMON.md` — universal worker invariants;
- `worker/roles/dsd-<role>/SKILL.md` — one focused role skill;
- `worker/PROOF-PATTERNS.md` — optional proof recipes named by task.

Role files are Agent-Skill-compatible, but production DSD does not rely on native
skill discovery. Every launch names the exact immutable role-skill path.

## 3. Intake / resume

For a new run or fresh parent session:

1. identify project root, authoritative plan, project instructions, and parent
   harness;
2. personally read enough governing authority to understand/decompose the current
   phase—this is governance reading, not repository surveying;
3. create/bind the durable run under `DeepSeekAndDestroy/`;
4. install/use the active harness adapter when needed;
5. snapshot immutable worker rules with `prepare_worker_rules.py`; a stable run-rule
   change creates the next revision, never rewrites historical authority;
6. delegate repository mapping to Discovery/Phase Surveyor when needed;
7. persist current phase/task and exact `next_action`.

`state.json` plus accepted primary evidence are execution authority. HANDOVER,
progress prose, old chat, and summaries are continuity claims. Reconcile conflicts
cheaply against durable state/evidence; do not rebuild project history in premium
context.

## 4. Decompose into independently reviewable tasks

One task = one bounded semantic objective a fresh Reviewer can prove/disprove
without reviewing the whole phase. The parent defines the semantic contract;
workers may supply discovery facts, AC suggestions, or proof obligations but do not
silently redefine plan authority.

Use `render_task_contract.py`. As applicable the immutable contract carries:
objective/authority/inputs, exact `Allowed source changes`, stable `AC-*`, proof
obligations/pattern tags, targeted verification, exclusions/mechanical references,
and explicit Clerk checks. Keep it role-neutral where possible so Implementer,
Reviewer, and Fixer share one acceptance/proof authority.

Use `render_worker_prompt.py`; do not hand-compose a large worker prompt.

### Two-zero-change guard

After two consecutive substantial Implementer/Fixer attempts against the same
contract produce zero intended changes and do not prove already-satisfied behavior,
set `decomposition_required: true`. No third mutating launch is valid until
Discovery/splitting/rescoping or a materially revised immutable contract resolves
why the task is not landing. Keep the second chance; do not launch hopeful loops.

## 5. Worker instruction composition

Each immutable worker-rules revision snapshots:

```text
WORKER_RULES.md              # run facts/run-specific constraints
protocol/COMMON.md
protocol/PROOF-PATTERNS.md
protocol/roles/dsd-<role>/SKILL.md
```

A worker reads only: exact `WORKER_RULES.md`, exact `COMMON.md`, its exact role
skill, exact task contract, and proof patterns (only contract-named patterns are
mandatory). Do not expose other role manuals merely because they exist.

A **role change starts a fresh worker session**. Pass durable evidence paths instead
of carrying role residue from Reviewer→Fixer, Discovery→Implementer, etc. Session
resume is reserved for same-role transport/session continuation when genuinely
useful.

## 6. Execute, wait quiescently, gate mechanically

For each attempt:

1. capture the full tracked + untracked-nonignored Git worktree baseline, excluding
   only `DeepSeekAndDestroy/`;
2. freeze task contract and explicit-path prompt against one worker-rules revision;
3. create immutable `launch-reservation.json`; that reservation is the single
   authority for prompt/contract/rules/baseline/report identity;
4. create the safe report skeleton and launch the selected backend. Default external
   OpenCode uses `run_worker.py`; a supported native backend uses its adapter plus
   `native_worker_attempt.py` reserve/finalize;
5. wait quiescently for the backend's real terminal boundary (external child process
   exit or native Task return);
6. classify the resulting `terminal.json` once;
7. only successful `completed` transport enters `evidence_gate.py`;
8. pre-start transport failure uses availability/backoff; a post-start failure is
   `suspect-changes` and may require Recovery.

Do not poll logs/CPU/repository to reassure yourself. A normal wait returning with no
terminal event means immediately wait again without premium narration. Diagnostics
are for an actual wait/tool inconsistency or recovery case.

## 7. Routine specialist routing

```text
(optional Discovery / Phase Surveyor)
              ↓
         Implementer
              ↓
       evidence gate
              ↓
      fresh Reviewer
          ↙       ↘
       PASS       FAIL
        │          ↓
        │      fresh Fixer
        │          ↓
        └──── fresh Reviewer
```

Use Verification for bounded independent reproduction, Evidence Clerk for clerical/
provenance/report reconciliation, Recovery for untrustworthy interrupted state, and
Phase Auditor for a frozen whole phase.

The parent should not consume full Implementer/Fixer dossiers during routine
routing when the next cheap specialist can read the durable evidence directly. At
real decisions consume compact Decision Packets, Clerk overlays, and audit packets.
Fresh review after every mutation remains mandatory; no Fixer self-approval.

## 8. Evidence: semantics versus clerical representation

Long workers own **semantic work**, not perfect serialization. Their terminal report
must preserve a truthful role `Verdict` and enough evidence for the next specialist.
The canonical Decision Packet, FINAL marker, verification summary, defects summary,
and Proof Matrix are preferred because they make routing cheap, but clerical defects
do not erase otherwise trustworthy long-horizon work.

`evidence_gate.py` separates:

- **integrity/semantic failures** — non-waivable: wrong immutable authority,
  source-scope drift, read-only source movement, missing/invalid role verdict,
  explicit semantic contradictions, corrupted attempt identity, etc.;
- **Clerk-normalizable defects** — arithmetic, FINAL/formatting defects, recoverable
  report location, or Reviewer proof represented non-canonically while underlying
  evidence may exist.

`Role:`/`Task:` report lines are readability only; launch reservation owns identity.
Workers do not declare fast-path eligibility. The gate derives
`fast_path_eligible` from Reviewer PASS + clean proof/mechanics + resolved Clerk
work.

Evidence Clerk may reorganize/reconcile **existing** evidence and provide an
immutable overlay. It may not invent semantic proof, reinterpret a real failure as
success, waive source-scope/integrity failures, decide architecture, or transition
state. Clerk itself cannot recurse into another Clerk. An unchanged launcher
skeleton/missing canonical report must actually be recovered before originating
evidence can pass.

Terminal evidence is immutable. Repairs/reviews use new numbered attempts.

## 9. Task acceptance / reopened prerequisites

Accept a task only when the deterministic decision surface is clean: fresh
independent Reviewer PASS; all AC proof established; required verification clean;
source/scope/preservation clean; zero task-relevant defects; evidence gate clean
including any Clerk overlay; and no conflicting accepted evidence.

When clean, accept without rereading code or rerunning tests in premium context.

If an accepted prerequisite materially changes, dependents become
`needs-revalidation`. Cheap bounded revalidation yields still-valid or superseded;
do not continue stale contracts because they once passed.

## 10. Exceptional outcomes

A reportless/forced exit after work began is `suspect-changes`, never proof of “no
changes”. Establish that writes stopped, capture scope delta, let Evidence Clerk
recover exact-attempt report material when possible, and use Recovery for non-obvious
source disposition.

Provider/quota/auth/transport failure never authorizes premium implementation. Use
exact-model health probes, persisted backoff, and configured fallback; human-block
only for genuine external intervention.

Detailed exceptional mechanics live in `WORKSPACE.md` / `OPENCODE.md`.

## 11. Phase gate

When phase tasks are provisionally accepted:

1. finish and gate every phase-owned writer, including artifact-mutating verification;
2. close the phase write barrier and capture the frozen mechanical snapshot;
3. run required post-barrier Verification read-only against that state;
4. run a fresh Phase Auditor against the same frozen state;
5. parent reads compact audit + governing authority and makes the phase decision;
6. remediation becomes bounded immutable tasks;
7. any phase-owned mutation reopens the barrier and invalidates stale post-barrier
   verification/audit evidence;
8. re-close/re-audit until whole phase contract is clean.

## 12. Context / communication

Use `COMPACTION.md`. `verify-resume` mechanically checks governing plan/config/
authority continuity; live worker state is revalidated separately. Durable state is
authoritative and native summaries are advisory.

Routine launch/wait/pass/fix transitions are not user-visible events. When a host
forces an update, keep it short. Expand only for material correction, blocker,
consequential decision, phase result, direct user request, or completion.

Never estimate token usage; use exact host counters only when exposed.
