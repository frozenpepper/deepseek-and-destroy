# Worker Review / Verification Protocol

Use this for Reviewer, Verification Worker, Recovery Auditor, and Phase Auditor
roles. Role-specific task instructions still control the exact boundary.

## Independent proof

Reports and handovers are claims. Inspect the actual assigned implementation or
evidence and attack the supplied acceptance/proof contract independently.

For every reviewed `AC-*`, establish at criterion level:

- the named production mechanism was reached;
- required positive path works;
- required negative path works when applicable;
- every named dimension was exercised;
- a plausible wrong implementation was defeated;
- decisive evidence passed/failed for the intended reason.

Do not narrate every assertion. Do explain **why** the decisive evidence proves the
criterion.

## Falsifiable hypotheses

Execute the supplied task-specific hypotheses rather than merely discussing them.
A hypothesis should name a failure mode and discriminating attack. Generic concerns
already covered by this protocol do not need another prose review pass.

## Wrong-reason evidence

Explicitly look for tests that look green because of:

- empty/missing fixtures or replay;
- setup exception or early return;
- cap-limited dispatch;
- bypassing mocks/fakes;
- same-instance-only state;
- vacuous conditions;
- shared predicate used for distinct gates;
- self-attested authority;
- aggregate counts hiding identity/mapping errors.

Expected outcome + wrong mechanism is a finding.

## Verification ownership

Do not multiply expensive proof without reason. Inspect the implementer's terminal
verification. Re-run the targeted checks needed for independent discrimination and
the task's explicit independent requirements. Broad artifact/full-suite/live
verification belongs to a dedicated Verification Worker when assigned. A later code
change invalidates evidence it makes stale.

Authoritative project/plan requirements for independent repetition always win.

## Read-only integrity

Reviewer/Verifier/Auditor roles do not modify project source/tests. They may write
only their assigned DSD evidence/report artifacts (and explicitly authorized
project progress/handover files for an Evidence Clerk). For Git projects, the
preferred read-only tripwire is the supplied full-worktree content snapshot
excluding only `DeepSeekAndDestroy/`; it detects unexpected new files as well as
changes to known files. Mechanical before/after scope evidence wins over a worker
claim that it stayed read-only.

## Decision Packet / Proof Matrix

Reviewer reports contain one Proof Matrix row per task AC and a compact Decision
Packet. A PASS requires every row PASS and `TASK-RELEVANT DEFECTS: NONE`.

A task-relevant correctness defect cannot be relabeled as cleanup/technical debt.
An intentional downstream consequence requires a concrete closure task and keeps
the containing phase blocked until closure.

## Immutable final

After FINAL, do not edit the report or evidence. A repair or new review round gets a
new numbered artifact.
