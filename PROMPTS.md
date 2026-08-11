# DeepSeek and Destroy — Contracts and Path-Only Handoffs

DSD does not hand-author large repeated worker prompts. Durable files carry the
contract; launch prompts point to exact immutable paths.

For each attempt:

1. create/select one immutable task-contract revision with
   `render_task_contract.py`;
2. render the exact role handoff with `render_worker_prompt.py`;
3. capture scope baseline and launch through the selected backend (`run_worker.py` for default external OpenCode; adapter-bound native reserve/Task/finalize when explicitly selected);
4. wait quiescently using the active harness adapter;
5. gate terminal evidence before routing/acceptance.

## Task contract = changing semantic decision surface

The parent supplies only task-specific facts. Keep simple tasks simple. Typical
slots are:

- bounded objective;
- governing authority / prior evidence references when needed;
- exact `Allowed source changes`;
- stable `AC-*` and proof obligations;
- targeted verification;
- sharp risk hypotheses only when useful;
- explicit Evidence Clerk checks only when known in advance;
- task-specific outputs only.

The renderer omits empty optional sections. It does not repeat launch-derived report,
evidence, or lifecycle paths. `Allowed source changes` is always explicit because it
is a mechanical write boundary.

Example:

```markdown
# Task U17 — Persist canonical media state
Contract revision: r0003

## Objective
Persist canonical media selection across a real restart.

## Authority
- `/project/docs/architecture.md`

## Inputs
- `/project/DeepSeekAndDestroy/.../discovery.md`

## Allowed source changes
- `src/media/`
- `tests/media/`

## Risk hypotheses
1. Same-instance state may fake restart durability.

## Acceptance criteria
- AC-001 — selected media survives a fresh-process restart.
- AC-002 — invalid stored media fails closed to the canonical fallback.

## Proof Obligations
- AC-001 | DURABILITY | fresh-instance restart, exact identity
- AC-002 | FAIL-CLOSED | realistic invalid persisted value

## Verification
- `<targeted command>`

## Evidence Clerk Checks
- P-001 provenance: confirm fixture baseline against task-start authority
```

Pure Discovery/Clerk tasks may omit semantic ACs rather than inventing fake ones.

## Contract immutability

A revision becomes immutable at first launch. `state.json` records its path/hash.
Material change to scope, acceptance, user authority, dependency, or changing role
input creates the next numbered revision. Never rewrite historical contracts.

A mechanical artifact is authoritative only when the exact current contract/launch
reservation binds its identity/hash. Similarly named stale files are not givens.

## Run rules versus worker doctrine

`prepare_worker_rules.py` creates one immutable revision containing:

```text
WORKER_RULES.md              # run facts + run-specific constraints only
MANIFEST.json                # cryptographic binding of the full revision
protocol/COMMON.md           # universal worker behavior
protocol/PROOF-PATTERNS.md
protocol/roles/dsd-<role>/SKILL.md
```

Do not duplicate Common/role doctrine inside `WORKER_RULES.md`. Do not put changing
task details or secrets there. A stable run-wide rule change creates the next
revision.

## Tiny launch handoff

Canonical shape:

```text
DSD <ROLE> for <task-id>.
Read and obey, in order:
1. <worker-rules>/WORKER_RULES.md
2. <worker-rules>/protocol/COMMON.md
3. <worker-rules>/protocol/roles/dsd-<exact-role>/SKILL.md
4. <task-contract>
5. <worker-rules>/protocol/PROOF-PATTERNS.md
Report: <exact report path>
```

Only task-named proof patterns are mandatory. Do not restate the manuals or project
history in the launch prompt. DSD explicitly selects the role; native harness skill
discovery is not production authority.

A role change starts a fresh worker session. Durable report/evidence paths carry
context between roles. Resume an OpenCode session only for a same-role continuation
when it is actually useful.

## Terminal report: semantic requirement, preferred clerical shape

The worker must preserve a truthful terminal `Verdict` from its role vocabulary and
enough evidence for the next specialist. Preferred compact shape:

```markdown
## Decision Packet
DSD_REPORT_STATUS: FINAL
Verdict: <role terminal>
Goal/result: <one line>
Changed/read-only: <compact effect>
Verification: <result/counts/check>
Proof: <AC/objective coverage>
Task-relevant defects: NONE | <ids>
Clerk checks: NONE | REQUIRED <stable ids>
Evidence: <exact paths>
```

`Role:` and `Task:` may be included for readability but are not identity authority;
`launch-reservation.json` is. Workers never emit fast-path eligibility.

Numeric verification fields are optional; when present they must reconcile or route
to Evidence Clerk. Exact packet formatting and `DSD_REPORT_STATUS: FINAL` are
preferred conventions, not reasons to discard otherwise trustworthy semantic work.
The one non-negotiable semantic field is a role-valid terminal `Verdict`.

Reviewer reports should account for every AC and preferably include:

```markdown
## Proof Matrix
| AC | Mechanism reached | Positive | Negative | Dimensions | Counterexample | Result |
|---|---|---|---|---|---|---|
| AC-001 | ... | ... | ... | ... | ... | PASS |
```

If equivalent per-AC evidence is recorded non-canonically, Evidence Clerk may
normalize it (`RC-001`). Missing proof remains missing.

## Decision boundary

Workers resolve routine mismatch from governing authority and existing architecture.
Only a genuine authority/access/ownership boundary may return
`DECISION_REQUIRED`/`BLOCKED`; a menu of routine implementation scopes is not a
valid blocker.
