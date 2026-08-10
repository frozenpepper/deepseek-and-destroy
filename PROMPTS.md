# DeepSeek and Destroy Task Contracts and Path-Only Handoffs

DSD does **not** hand-author large repeated worker prompts. Durable files carry the
contract; the launch prompt points to them.

At run creation, generate immutable
`<run-root>/worker-rules/r0001/WORKER_RULES.md` plus its immutable `MANIFEST.json` and run-local `protocol/`
snapshot with `scripts/prepare_worker_rules.py`. If a stable run-wide rule later
changes, create the next revision (`r0002`, ...); never rewrite historical worker
authority.

For each worker attempt:

1. create/select the current **immutable task-contract revision** (for example `contracts/r0003.md`); prefer `scripts/render_task_contract.py` so the orchestrator supplies compact slots instead of re-authoring the frame, and create a new revision rather than rewriting one already launched;
2. use `scripts/render_worker_prompt.py` to render the tiny launch prompt against that exact revision;
3. use `scripts/run_worker.py` to run the external OpenCode worker;
4. wait quiescently using the orchestrator harness adapter;
5. run `scripts/evidence_gate.py` before consuming/accepting terminal evidence.

## Task contract: the changing decision surface

The premium orchestrator should normally author only five semantic slots. `render_task_contract.py` owns the fixed headings/path validation/hash output:

1. **Unit** — the independently reviewable unit;
2. **Objective** — the concrete outcome;
3. **Risk hypotheses** — at most three sharp falsifiable attacks when useful;
4. **Acceptance / proof contract** — stable AC ids and Proof Obligations;
5. **Deliverable expectations** — task outputs/evidence expectations; the exact role report path is assigned by the immutable launch handoff, not baked into the shared semantic contract.

Everything else should be durable/mechanical references rather than re-authored
boilerplate.

Recommended immutable contract-revision shape:

```markdown
# Task <id> — Contract r<n>
Contract revision: <n>

## Unit
<one independently reviewable unit>

## Objective
<bounded outcome>

## Authority
Plan: <exact path>
Project instructions: <exact paths>
Architecture/contracts: <exact paths/sections when applicable>
Discovery/construction spec: <path | NONE>

## Inputs
Prior report/review/gate/findings: <exact path(s) | NONE>

## Scope
Expected: <paths/subsystem>
Excluded: <explicit exclusions>
Preservation baseline: <path | NONE>
Mechanical facts: <exact current-bound artifact path + identity/hash | NONE>

## Allowed source changes
NONE
<!-- or exact project-relative path prefixes for IMPLEMENTER/FIXER, and only an
explicit assigned project progress/documentation path for EVIDENCE-CLERK. This is a
mechanical write boundary, not permission to broaden the semantic task. -->

## Risk hypotheses
1. <Claim | Failure mode | Attack | Discriminating evidence>
2. <...>
3. <...>

## Acceptance criteria
- AC-001 — <criterion>
- AC-002 — <criterion>

## Proof Obligations
| AC | Mechanism | Paths | Required dimensions | Counterexample to defeat | Patterns |
|---|---|---|---|---|---|
| AC-001 | ... | positive + negative | scale>1, exact identity | last-wins mapping | CARDINALITY, IDENTITY |

## Verification
- <targeted command/check or referenced verification spec>

## Evidence Clerk Checks
NONE
<!-- or concise exact checks such as:
- M-001 measurement: rerun `<exact command>`; predicate `<boundary>`
- P-001 provenance: verify `<path>` against `<task-start baseline/commit>`
-->

## Deliverables
Task outputs:
- <task-level output/deliverable expectation | NONE>
Role report: ASSIGNED BY IMMUTABLE LAUNCH HANDOFF
Evidence directory: <path>
Major log: <path>
Configured progress file: <path | NONE>
```

A contract with no semantic ACs (for example a pure Discovery or Evidence Clerk unit)
may use role-appropriate completion criteria instead of forcing fake ACs.

## Contract immutability

A contract revision becomes immutable when its first worker attempt is launched.
`state.json` records the exact revision path and SHA-256. If review findings, user
authority, dependencies, or scope materially change the contract, create the next
numbered revision and update state before launching against it. Never rewrite an
old revision: old attempt prompts must continue to resolve to the instructions they
actually received. Role-specific changing inputs (for example a prior review path)
are references in the new revision, not edits to old evidence.

Mechanical helper facts are trusted only when this exact immutable contract/state
binds the artifact/attempt identity (and hash/fingerprint when available). A stale
baseline or helper output from another attempt is merely a file, not a given fact.

## Versioned run-level worker rules

Stable rules belong in one immutable worker-rules revision, not in every prompt.
Each revision records an immutable `MANIFEST.json` binding `WORKER_RULES.md` and every snapshotted protocol file, plus:

- exact project/run roots;
- governing authority paths;
- run-local worker protocol paths;
- stable harness/project execution rules;
- report/finality/immutability rules;
- default worker model/profile;
- any user-approved environmental constraints.

Do not paste changing task-contract details into worker rules. Do not put secrets
there. Later attempts may use a newer worker-rules revision only when a real stable
run-wide constraint changed; old attempts continue to point to their historical
revision.

Environment-specific rules such as fixed working-directory behavior, absolute-path
requirements, or shell constructs known to be unsafe belong here **only when they
are actually true for the run**. Do not universalize one project's shell quirk.

## Tiny launch handoff

`render_worker_prompt.py` produces the canonical handoff. Its content is deliberately
small and equivalent to:

```text
DSD <ROLE> for <task-id>.
Read and obey, in order:
1. <run-root>/worker-rules/rNNNN/WORKER_RULES.md
2. <run-root>/worker-rules/rNNNN/protocol/CORE.md
3. <run-root>/worker-rules/rNNNN/protocol/ROLES.md — matching role section only.
4. <task-root>/contracts/rNNNN.md
5. <run-root>/worker-rules/rNNNN/protocol/<optional family protocol>.md when applicable
6. <run-root>/worker-rules/rNNNN/protocol/PROOF-PATTERNS.md entries named by the contract.
Report: <exact report path>.
Resolve ordinary ambiguity from authority; do not ask for routine scope choices.
Final stdout <=3 lines: FINAL <role-terminal-status>, report path, optional one-line result.
```

Do not expand this into a restatement of Worker Core, the role protocol, harness
preamble, or project history.

## Role contracts

Role behavior is authoritative in `worker/ROLES.md`, which is snapshotted into each
immutable worker-rules revision and selected by the launch role; the semantic task contract itself stays role-neutral so Implementer, Reviewer, and Fixer can share the same AC/proof authority. `BUILD.md`, `REVIEW.md`, and `EVIDENCE.md` add only
shared mechanics for role families; they do not replace the role boundary. Keep
role semantics in one place to prevent prompt/rendering drift.

## Decision Packet

Every terminal worker report starts with:

```markdown
## Decision Packet
DSD_REPORT_STATUS: FINAL
Role: <role>
Task: <id>
Verdict: <role terminal status from worker/ROLES.md>
Goal/result: <one line>
Changed/read-only: <compact path groups/effect>
Verification: PASS|FAIL; total=<n?>; passed=<n?>; failed=<n?>; skipped=<n?>; check=<name/path>
Proof: <AC coverage / verification objective>
Scope/preservation: CLEAN | FINDING <id>
Task-relevant defects: NONE | <ids>
Major log: NONE | UPDATED <ids> | REQUIRED
Clerk checks: NONE | REQUIRED <ids>
Evidence: <exact paths>
FAST-PATH ELIGIBLE: YES|NO — <reason>
```

Keep the packet normally <=15 lines. Numeric verification fields are optional when
the runner does not expose them, but when supplied their arithmetic must reconcile.

Reviewer reports then include the Proof Matrix:

```markdown
## Proof Matrix
| AC | Mechanism reached | Positive | Negative | Dimensions exercised | Counterexample defeated | Result |
|---|---|---|---|---|---|---|
| AC-001 | YES: <why> | PASS | PASS/N/A | <evidence> | YES: <how> | PASS |
```

Detailed logs/inventories go to the task evidence directory and are cited; do not
copy them into the parent-facing packet.

## Impossibility / decision boundary

Workers do not get a generic “if reality differs, stop and ask” escape hatch.
Ordinary mismatch is resolved from governing authority and existing architecture.
Build the smallest complete honest project-aligned solution and record corrected
facts.

Only a genuine authority/access/ownership boundary may return
`DECISION_REQUIRED`/`BLOCKED`. A menu of implementation scopes that project
authority can already resolve is not a valid blocker.
