# DeepSeek and Destroy

> **Give an expert orchestrator a plan. Cheap specialist workers do the repository
> work until the plan is actually finished.**

DeepSeek and Destroy (DSD) is a long-horizon coding orchestration skill built around
one economic rule:

> **Spend premium context on authority and consequential judgment, not repository
> ingestion, worker polling, clerical normalization, or repetitive execution.**

The default worker transport is an external OpenCode CLI process using
`opencode-go/deepseek-v4-flash`. The premium orchestrator may run in Codex, Claude
Code, OpenCode, Kilo Code, or another capable harness.

## Architecture

```text
premium orchestrator
  reads user/project/plan authority
  decomposes work and makes consequential decisions
          │
          │ tiny explicit-path handoff
          ▼
cheap specialist worker
  COMMON + exact role skill + task contract + proof patterns
          │
          ▼
durable semantic report/evidence
          │
          ▼
mechanical integrity/scope gate
       ┌──┴───────────────┐
       │                  │
     clean          clerical ambiguity
       │                  │
       │           Evidence Clerk
       │          reconcile/normalize
       └──────────┬───────┘
                  ▼
        compact decision surface
                  │
                  ▼
         premium orchestrator
```

The Evidence Clerk is deliberately first-class: cheap context may be spent
reconciling large or imperfect worker evidence so the premium parent does not have
to ingest it. The Clerk may normalize facts that already exist; it may never invent
technical proof or waive an integrity failure.

## v15 design

### One instruction owner per concern

- `SKILL.md` is the parent/orchestration doctrine. The duplicate
  `orchestrator/CONTROL.md` manual is gone.
- `worker/COMMON.md` contains only universal worker behavior.
- each specialist role has an Agent-Skill-compatible
  `worker/roles/dsd-<role>/SKILL.md`.
- `WORKER_RULES.md` contains run facts and run-specific constraints, not another
  copy of common/role doctrine.
- task contracts contain task semantics; launch-derived report/log/evidence paths
  are not repeated as task prose.

Production DSD explicitly selects the exact snapshotted role skill. It never relies
on probabilistic native skill discovery, although the role skills remain suitable
for standalone native-skill testing.

### Long workers own semantics, not clerical perfection

A worker should produce a clear canonical Decision Packet, Proof Matrix, and
`DSD_REPORT_STATUS: FINAL` when practical. Those conventions make evidence cheap to
consume, but useful long-running work is not discarded merely because its final
Markdown is imperfect.

The launcher already owns attempt identity, so worker-authored `Role:` and `Task:`
lines are optional. Workers do not declare `FAST-PATH ELIGIBLE`; the evidence gate
derives routing eligibility from trusted facts.

Clerk-normalizable examples include noncanonical report finality, an equivalent
per-AC review written outside the preferred table, or declared test arithmetic that
needs reconciliation. Non-waivable examples include forbidden source movement,
mutated immutable authority, genuinely missing proof, or an untouched launcher
report skeleton. An absent report must actually be recovered, not waved through.

### Fresh role boundaries

A normal role change starts a fresh worker session. Reviewer → Fixer, Fixer →
Reviewer, and Discovery → Implementer transfer knowledge through durable evidence,
not inherited chat state. Same-role session continuation remains available only for
trustworthy transport/recovery cases.

### One immutable attempt authority

For new v15 attempts, `launch-reservation.json` is the single immutable authority
binding role/task identity, prompt, contract, worker-rules snapshot, scope baseline,
report, and log. `attempt.json` and `terminal.json` are lifecycle records bound to
that reservation path/hash instead of duplicating every authority field. Historical
v14 terminal evidence remains readable.

### Quiescent waiting

The default external worker emits `terminal.json` when the actual child process
exits. An explicitly selected supported native backend reserves the same immutable
attempt before its Task call and finalizes the same terminal event after the Task
returns. Transport completion never substitutes for semantic review.

For external workers the premium parent waits through the harness-native mechanism
or one blocking `wait_worker.py` call. A host/tool timeout with no terminal event is
a non-event: issue the same wait again without repository inspection, log polling,
or progress narration.

### Resume continuity is mechanically checked

Compaction checkpoints record the governing plan-reference, authority-index,
effective-config, and plan-source hashes. `verify-resume` checks those immutable
governing artifacts and fails closed on drift. Mutable task/worker state is then
revalidated separately because legitimate workers may finish during compaction.

## Correctness model

DSD keeps the proof discipline introduced in earlier versions:

> **An expected outcome is not proof. Establish that the intended production
> mechanism was reached and caused the result.**

Meaningful behavioral acceptance criteria use stable `AC-*` identifiers and explicit
proof obligations. Reviewers independently try to disprove them and should provide
mechanism, positive evidence, negative/discriminating evidence, required dimensions,
and counterexamples where appropriate.

The canonical Proof Matrix remains the preferred compact representation; equivalent
semantic evidence can be normalized by the Evidence Clerk. Missing semantic proof
cannot.

Reusable proof patterns include:

- `NEGATIVE-GATE`
- `CARDINALITY`
- `IDENTITY`
- `DURABILITY`
- `DERIVED-EVIDENCE`

## Core safeguards retained

v15 deliberately does **not** simplify away the protections earned from field
failures:

- premium parent owns authority, decomposition, routing, and consequential decisions;
- distinct specialist worker roles remain distinct;
- fresh independent review follows source mutation;
- exact `Allowed source changes` plus full per-attempt Git-worktree baseline;
- immutable accepted contracts/evidence and atomic launch reservation;
- reportless/suspect-change Recovery instead of blind retry or blind acceptance;
- external run-scoped OpenCode DB outside the repository;
- real process terminal event and no-background-writer invariant;
- quiescent/no-model polling;
- two-consecutive-zero-change decomposition guard;
- phase write barrier and frozen audit state;
- durable `state.json`, `HANDOVER.md`, and exact `next_action` continuity.

## Worker roles

The role mini-skills are intentionally separate reasoning priors:

- **Implementer** — build one bounded change.
- **Fixer** — repair explicit accepted findings without broad redesign.
- **Reviewer** — fresh adversarial read-only acceptance review.
- **Verification** — establish bounded technical facts/read-only verification.
- **Discovery** — investigate an uncertain area and produce cited findings.
- **Phase Surveyor** — establish current phase state before decomposition/audit.
- **Recovery** — reconstruct trustworthy state after abnormal execution/evidence.
- **Phase Auditor** — evaluate a frozen phase against governing authority.
- **Evidence Clerk** — reconcile, normalize, compress, and maintain evidence without
  inventing technical facts.

Each worker normally reads only:

```text
WORKER_RULES.md                 run facts
worker/COMMON.md                universal worker rules
worker/roles/<role>/SKILL.md    exact specialist role
contracts/rNNNN.md              exact task semantics
worker/PROOF-PATTERNS.md        when named/applicable
```

## Typical task flow

```text
Discovery / Survey if needed
        ↓
small immutable task contract
        ↓
Implementer
        ↓
terminal event → evidence/scope gate
        ↓
fresh Reviewer
        ↓
terminal event → evidence gate
       ↙                         ↘
    PASS                      clerical issue
      │                            ↓
      │                      Evidence Clerk
      │                            │
      └──────────────┬─────────────┘
                     │
              semantic FAIL
                     ↓
                fresh Fixer
                     ↓
                fresh Reviewer
```

At phase completion, all writers finish, the phase write barrier closes, required
post-barrier verification/audit is read-only, a fresh Phase Auditor evaluates the
frozen state, and the premium parent makes the plan-wide decision. Any repair
reopens the barrier and invalidates the previous gate snapshot.

## Default OpenCode storage

DSD uses one disposable OpenCode DB per run (or per deliberate concurrency lane)
outside every repository/worktree. This avoids polluting the user's interactive
history and prevents OpenCode project-refresh logic from scanning its own live
SQLite file. Different roles use fresh sessions in that run DB; same-role session
continuation is exceptional, not normal routing.

See `OPENCODE.md`.

## Run tree

```text
DeepSeekAndDestroy/plans/<plan-id>/runs/<run-id>/
  state.json
  HANDOVER.md
  authority-index.json
  worker-rules/
    r0001/
      WORKER_RULES.md
      MANIFEST.json
      protocol/
        COMMON.md
        PROOF-PATTERNS.md
        roles/dsd-*/SKILL.md
  compactions/
  phases/
    <phase>/<task>/
      contracts/r0001.md
      attempts/<role>-1/
        launch-prompt.txt
        launch-reservation.json
        attempt.json
        scope-baseline.json
        worker.log
        terminal.json
        evidence-gate.json
      implementer-report-1.md
      review-1.md
```

## Install / start

Install this directory in the skill location used by the premium harness. OpenCode
must already be configured for the selected worker model.

Then tell the orchestrator to use DeepSeek and Destroy against the authoritative
project plan. During intake DSD resolves project authority and creates its durable
run state.

A worker-rules snapshot can be created mechanically with:

```bash
python3 <skill-root>/scripts/prepare_worker_rules.py \
  --project-root <project> \
  --run-root <run-root> \
  --plan <authoritative-plan> \
  --project-instruction <project>/AGENTS.md
```

Install the active parent-harness continuity adapter when needed:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py \
  --project-root <project> \
  --harness <codex|claude-code|opencode|kilo>
```

When Kilo-native workers are explicitly selected, install their project subagents
and follow `KILO.md`; the normal default remains external OpenCode workers.

## Important files

```text
SKILL.md                         parent mission/authority/flow
WORKSPACE.md                     durable state/evidence/continuity details
PROMPTS.md                       task contract + path-only handoff conventions
CONFIG.example.md                optional run/harness configuration examples
worker/COMMON.md                 universal worker invariants
worker/roles/*/SKILL.md          focused role mini-skills
worker/PROOF-PATTERNS.md         reusable proof recipes
scripts/_roles.py                mechanical role capability registry
HARNESS.md                       parent/worker harness routing
OPENCODE.md                      default external worker transport/storage
CLAUDE.md / CODEX.md / KILO.md   parent-harness adapters; Kilo also documents optional native workers
COMPACTION.md                    durable checkpoint/resume protocol
scripts/prepare_worker_rules.py  immutable run instruction snapshot
scripts/render_task_contract.py  semantic task-contract renderer
scripts/render_worker_prompt.py  tiny explicit-path handoff renderer
scripts/run_worker.py            default external worker lifecycle
scripts/native_worker_attempt.py native Task reservation/finalization lifecycle
scripts/wait_worker.py           quiescent blocking wait
scripts/evidence_gate.py         integrity/scope/clerical classification gate
scripts/check_review_contract.py reviewer proof/normalization checker
scripts/decision_packet.py       compact canonical/noncanonical decision surface
scripts/check_state.py           control-plane invariant checker
scripts/install_compaction_adapter.py legacy compatibility wrapper for harness installer
scripts/scope_snapshot.py        worktree content-hash baseline/compare
```


## License

MIT. See `LICENSE`.
