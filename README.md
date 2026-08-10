# DeepSeek and Destroy

> **Give an expert orchestrator a plan. Cheap DeepSeek workers do the repository
> work until the plan is actually finished.**

DSD is a long-horizon coding orchestration skill built around one economic rule:

> **Spend premium context on authority and judgment, not repository ingestion,
> prompt boilerplate, worker polling, arithmetic, or progress narration.**

The default worker is `opencode-go/deepseek-v4-flash` launched through the OpenCode
CLI as an external process. The premium orchestrator may run in Claude Code, Codex,
OpenCode, or another capable harness.

## Architecture

```text
                 premium orchestrator
              (Claude / Codex / OpenCode)
                         │
          authority + decomposition + decisions
                         │
              tiny path-only task handoff
                         │
                         ▼
              OpenCode CLI + DeepSeek worker
                         │
      inspect / implement / test / review / repair
                         │
                         ▼
                  durable report/evidence
                         │
              mechanical evidence gate
                         │
            ┌────────────┴─────────────┐
            │                          │
          clean                  discrepancy/clerical
            │                          │
            │                    Evidence Clerk
            │                    (cheap worker)
            └────────────┬─────────────┘
                         ▼
                 compact Decision Packet
                         │
                         ▼
                    orchestrator
                 route / decide / approve
```

## What v13 changes

### No hand-written worker dossiers

Stable worker/project/harness rules are snapshotted into immutable versioned
`worker-rules/rNNNN/` revisions with a manifest binding the rules and protocol files. Each task uses a small immutable numbered contract
revision containing the changing unit, objective, <=3 sharp risk hypotheses,
acceptance/proof contract, task-output/evidence expectations, and exact `Allowed
source changes` for mutating roles. The role-specific report path is assigned by the immutable launch handoff so one semantic contract can be shared by Implementer, Reviewer, and Fixer.

`scripts/render_task_contract.py` renders/freezes the fixed contract frame from compact slots. `scripts/render_worker_prompt.py` renders a tiny path-only launch prompt. If the
orchestrator is repeatedly writing 2–4 KB prompts, the flow is wrong.

### External worker waiting is event-driven

The default worker is an external `opencode run` process, not a Claude/Codex native
subagent. `scripts/run_worker.py` wraps that process and writes a durable
`terminal.json` when the actual child exits.

The premium harness then uses its best native wait:

- **Claude Code:** launch the wrapper detached; a project `asyncRewake` hook waits
  cheaply on its terminal event and wakes idle Claude only when the worker exits;
- **Codex:** foreground wrapper when safe, otherwise one long blocking
  `wait_worker.py` call;
- **OpenCode/other:** foreground or detached wrapper + long blocking wait.

No routine CPU/log polling. A plain wait timeout is a non-event: wait again without
reading the repository or narrating “still running.”

### Evidence gate before premium judgment

Worker reports are claims until cheap mechanical checks are clean.

`evidence_gate.py` catches:

- missing/misplaced/non-final report skeletons;
- inconsistent verification arithmetic when counts are declared;
- malformed reviewer Proof Matrix/fast-path contract;
- any read-only source movement;
- mutating changes outside the task's exact `Allowed source changes`;
- task/report requests for provenance/tripwire reconciliation.

Ambiguity goes to the **Evidence Clerk** (the normal cheap worker in a read-only
project role), not to the premium orchestrator. The clerk can re-derive tripwire
numbers, check provenance against the real task-start baseline, recover misplaced
reports from logs, and maintain technical logs/progress/handover when assigned.

### Authority reading is mandatory

“Orchestrator does not investigate” no longer means “orchestrator skips the plan.”
At a new run or fresh parent session, the orchestrator personally reads current
user instructions, project instructions (`AGENTS.md` or equivalent), the
authoritative plan, and relevant architecture/contracts.

Repository-scale tracing/testing stays worker-side.

`HANDOVER.md` restores continuity but its technical claims are prior-session
assertions, not authority. Claims used for a new decision must point to governing or
accepted evidence.

### Hard economy rules

- routine user transitions are silent; if the host forces an update, one sentence,
  target <=25 words;
- parent normally reads Decision Packets only;
- >3 substantive deep slices for one parent decision triggers worker compression or
  a fresh parent context;
- technical major-findings prose is written by evidence-owning workers or the
  Evidence Clerk, not the premium parent;
- two consecutive zero-intended-change mutating attempts forbid a third attempt on
  the same contract until it is split/re-prescribed;
- terminal reports/evidence are immutable; repairs create new numbered attempts;
- every terminal worker attempt gets a full Git-worktree baseline; mutating roles
  may change only declared `Allowed source changes`, read-only roles none;
- phase audit/gating uses a write barrier so nobody audits a moving tree.

## Correctness model

DSD v12 introduced explicit worker proof discipline and v13 keeps it:

> **An expected outcome is not proof. Show that the intended production mechanism
> was reached and caused the result.**

Meaningful behavioral acceptance criteria use stable `AC-*` ids and Proof
Obligations. Reviewer reports contain a Proof Matrix. For risky criteria, reviewers
attack sharp falsifiable counterexamples rather than merely “reviewing carefully.”

Small proof recipes cover common failure classes without turning the worker prompt
into a universal checklist:

- `NEGATIVE-GATE`
- `CARDINALITY`
- `IDENTITY`
- `DURABILITY`
- `DERIVED-EVIDENCE`

A required-dimension defect is FAIL, not a “known limitation.”

## Default OpenCode storage

DSD uses one disposable OpenCode DB **per run**, outside every repository/worktree.
This avoids polluting the user's normal OpenCode history and avoids OpenCode
project-refresh scanning its own actively-written SQLite file.

All worker sessions in a sequential run share that external DB. Reviewer → fixer
resume uses the recorded session id when trustworthy. Terminal cleanup deletes the
whole disposable DB.

See `OPENCODE.md`.

## Run tree

```text
DeepSeekAndDestroy/plans/<plan-id>/runs/<run-id>/
  state.json
  HANDOVER.md
  worker-rules/
    r0001/
      WORKER_RULES.md
      MANIFEST.json
      protocol/
  authority-index.json
  major-findings-and-fixes.md
  plan/
  compactions/
  phases/
    <phase>/
      <task>/
        contracts/
          r0001.md
        attempts/
          reviewer-1/
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

## Worker flow

```text
Survey/Discovery when needed
        ↓
independently reviewable task contract
        ↓
Implementer
        ↓
terminal event → evidence gate
        ↓
fresh Reviewer + sharp hypotheses
        ↓
terminal event → evidence gate / Clerk if needed
       ↙ ↘
    PASS  FAIL
      │     │
   accept  Fixer
             │
          fresh review
```

At the phase boundary, all implementation/fix writers **and any verification that
mutates accepted project artifacts** finish first. Then the write barrier closes,
post-barrier verification/audit is read-only, a fresh Phase Auditor synthesizes
proof, and the premium parent makes the plan-wide phase decision. Repairs reopen
the barrier and invalidate the old gate snapshot.

## Install

Clone/copy this directory into the skill location used by your orchestrator. For
example:

```bash
git clone https://github.com/frozenpepper/deepseek-and-destroy.git \
  ~/.agents/skills/deepseek-and-destroy
```

The exact skill directory is harness-specific.

OpenCode must already be configured with the default DeepSeek provider/model, or
configure another worker profile explicitly.

## Start a run

Tell the orchestrator to use DSD against an authoritative plan. During intake it
will resolve the project authority and create the durable run tree.

The run-level worker rules/protocol snapshot can be created mechanically:

```bash
python3 <skill-root>/scripts/prepare_worker_rules.py \
  --project-root <project> \
  --run-root <run-root> \
  --plan <authoritative-plan> \
  --project-instruction <project>/AGENTS.md
```

## Important files

```text
SKILL.md                         core mission/flow/authority boundary
orchestrator/CONTROL.md          premium-token economy, trust, wait, gate rules
WORKSPACE.md                     durable state/evidence/continuity
PROMPTS.md                       task contract + path-only handoff format
worker/SKILL.md                  Worker Core
worker/ROLES.md                  role-specific authority/boundaries
worker/BUILD.md                  implementation/fix doctrine
worker/REVIEW.md                 review/verification/audit doctrine
worker/EVIDENCE.md               Evidence Clerk doctrine
worker/PROOF-PATTERNS.md         compact proof recipes
HARNESS.md                       orchestrator vs worker harness selection
OPENCODE.md                      default worker transport/storage
CLAUDE.md                        Claude wait + compaction adapter
CODEX.md                         Codex wait + compaction adapter
COMPACTION.md                    durable context checkpoint protocol
scripts/prepare_worker_rules.py  immutable versioned run worker-rules snapshot
scripts/_rules_snapshot.py        shared worker-rules manifest integrity checks
scripts/render_task_contract.py   fixed contract renderer
scripts/render_worker_prompt.py  tiny launch prompt
scripts/run_worker.py            OpenCode process wrapper + terminal event
scripts/wait_worker.py           long blocking portable wait
scripts/evidence_gate.py         pre-acceptance mechanical gate
scripts/check_review_contract.py reviewer proof contract checker
scripts/check_state.py           control-plane invariant checker
scripts/scope_snapshot.py        mechanical content-hash facts
```

Optional contributed integrations may also exist in the repository. They are
inactive unless explicitly selected and are intentionally not part of the default
DSD read/routing path.

## License

MIT. See `LICENSE`.
