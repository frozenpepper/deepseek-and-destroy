# Worker Review and Evidence Protocol

Use this for reviewer, verification, recovery-audit, and phase-audit roles. Apply
only the sections relevant to the supplied role.

## Criterion-level causal proof

For each acceptance criterion in scope:

1. identify the production mechanism the criterion claims;
2. prove the decisive evidence actually reached that mechanism;
3. explain why the observed result was caused by that mechanism rather than an
   unrelated setup/harness/short-circuit condition;
4. exercise every required dimension;
5. apply relevant proof-pattern recipes;
6. name at least one plausible wrong implementation for high-risk criteria and
   determine whether current evidence would catch it.

Do not narrate every assertion. One compact Proof Matrix row per AC is enough when
supported by detailed evidence below.

## Wrong-reason evidence

Treat a test as insufficient or failing evidence when its expected result can be
explained by the wrong mechanism. Check relevant alternatives such as:

- empty/missing fixture or replay;
- exception/setup abort before target behavior;
- cap/limit prevents the path from executing;
- mock/stub bypasses production behavior;
- same-instance state masquerades as durable resume;
- vacuous/always-true condition;
- one shared predicate used as proof for two distinct contracts;
- authority/approval derived from the object being gated;
- aggregate counts hiding wrong per-entity mapping.

## Counterexample-first review

For high-risk ACs, explicitly state a plausible broken implementation that should
make the evidence fail. If current evidence would still pass, the criterion is not
proven even if every command is green.

## Consequence failures

A maintained-suite failure must be classified as:

- **hidden regression** → task FAIL;
- **intentional contract consequence** → concrete named closure task required and
  containing phase remains blocked;
- **unrelated/pre-existing** → defect ledger.

"Coordination", "known limitation", or "follow up later" without a concrete
closure is not a complete disposition.

## PASS integrity

A task-level PASS requires:

- every AC represented in the Proof Matrix;
- every required dimension exercised;
- no surviving counterexample undermining the evidence;
- no task-relevant correctness defect;
- clean required verification/scope/preservation evidence.

If any task-relevant defect exists, set `FAST-PATH ELIGIBLE: NO` regardless of how
small or well-documented it seems.
