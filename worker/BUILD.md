# Worker Build Protocol

Use this for implementation and repair roles.

## Build against proof obligations

For every `AC-*` in scope:

1. identify the production mechanism that implements it;
2. implement through the project's canonical architecture;
3. build evidence that actually reaches that mechanism;
4. exercise every required dimension from the Proof Obligation;
5. ensure at least one plausible wrong implementation would make the evidence fail;
6. run the assigned verification and record real output.

Do not optimize tests for convenience. A single-member fixture does not prove a
multi-member contract. Aggregate counts do not prove exact per-target identity.
Same-instance continuation does not prove durability across restart. A gate is not
proven fail-closed unless a realistic invalid input actually reaches and fails the
gate.

## When maintained tests fail

Do not silently weaken them. Classify the failure:

- hidden regression introduced by your change;
- intentional consequence of the corrected contract;
- unrelated/pre-existing defect.

If it is an intentional consequence outside this task, report the exact suite and
required closure rather than editing around it.

## Scope

Use the supplied discovery/construction brief. Verify local assumptions, then
start writing. Do not repeat broad discovery already completed by another worker.
If an assumption is materially wrong, record the correction and stop only when it
changes product/architecture/acceptance meaning beyond your delegated authority.

## Report

Record per-criterion implementation and proof evidence, verification output,
collateral effects, and any unresolved blocker. You do not self-approve the task;
a fresh reviewer does that.
