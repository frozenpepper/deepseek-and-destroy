# Worker Build Protocol

Use this for implementation and repair roles.

## Work from the durable contract

Read the task's unit, objective, acceptance criteria, Proof Obligations, scope,
exclusions, construction/discovery reference, preservation baseline, and mechanical
facts. Verify only the local semantic assumptions needed to start; do not redo a
completed repository survey.

For every `AC-*` in scope:

1. identify the production mechanism that implements it;
2. implement through the canonical project architecture;
3. build evidence that actually reaches that mechanism;
4. exercise every required proof dimension;
5. ensure at least one plausible wrong implementation would make the evidence fail;
6. run the assigned terminal verification after the final code change.

A single-member fixture does not prove a multi-member contract. Aggregate counts do
not prove exact identity. Same-instance continuation does not prove restart
durability. A fail-closed gate needs a realistic invalid input that reaches and
fails the intended gate.

## Scope disagreement

Do not use ordinary repository reality as an excuse to ask which scope to choose.
Resolve normal mismatch from project authority and implement the smallest complete
honest solution. If a supplied path/owner/count was wrong, correct the claim in the
report and continue when the acceptance meaning remains clear.

Stop only at the real authority boundaries listed in Worker Core. If completion
requires a materially new independently reviewable unit, finish what is safely
complete, record the exact new unit/why, and return `DECISION_REQUIRED` rather than
silently swallowing a second task.

## Maintained test failures

Classify failures as:

- hidden regression introduced by your change;
- intentional consequence of the corrected contract;
- unrelated/pre-existing defect.

Do not edit around an intentional consequence outside task scope. Record the exact
closure needed.

## Terminal report

Record per-criterion implementation/proof evidence, final verification summary,
collateral effects, and remaining blockers. Update the major log for a material
root cause/fix when the evidence is trustworthy. You do not self-approve the task;
a fresh reviewer does.
