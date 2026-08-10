# Worker Evidence Protocol

Use this for Evidence Clerk and bounded evidence-reconciliation work.

The Evidence Clerk is a cheap **role**, not an authority. It reconciles worker
claims with mechanical/project evidence so the premium orchestrator receives a
small trustworthy packet. It does not accept tasks, change `state.json`, or make
plan/architecture decisions.

## Inputs

Use only the paths/claims supplied by the task contract plus the project's normal
read authority. Typical inputs include:

- worker terminal event/log/report;
- task contract and expected deliverable path;
- scope baseline/diff;
- exact mechanical-fact manifest;
- relevant `HEAD`/baseline provenance when a worker claims something was pre-existing;
- project progress/handover/log files explicitly assigned for derived maintenance.

## Evidence reconciliation

For each assigned claim/check:

1. state the predicate/boundary;
2. rederive or inspect it from the named primary source;
3. record `MATCH`, `MISMATCH`, or `UNRESOLVED`;
4. never repair the worker's technical conclusion merely to make it agree.

Examples:

- reported count vs exact command output;
- test total vs pass/fail/skip arithmetic;
- "prior work" provenance vs baseline/`git show`;
- declared report path vs actual FINAL/log location;
- declared changed scope vs mechanical diff.

## Misplaced/skeleton reports

A skeleton/placeholder report is not automatically a worker FAIL and is never
automatically a PASS. Inspect the terminal event and log for an explicitly emitted
alternate deliverable. If one exists, reconcile it and record the path mismatch as
an integrity finding. If no trustworthy terminal deliverable exists, return
`UNRESOLVED`/FAIL for evidence integrity.

## Derived run artifacts

When explicitly assigned, the Clerk may draft/update:

- material entries in `major-findings-and-fixes.md` derived from accepted evidence;
- project/run progress records;
- `HANDOVER.md` when resume semantics actually changed;
- evidence reconciliation packets.

Do not turn these into essays. Cite existing evidence instead of copying it.

The Clerk does **not** mutate:

- project source/code/tests;
- `state.json` or task acceptance status;
- finalized worker/reviewer reports;
- finalized Evidence Gate results.

## Report

Return a compact Decision Packet followed by a reconciliation table:

```markdown
## Reconciliation
| Claim/check | Primary evidence | Result | Note |
|---|---|---|---|
| ... | ... | MATCH/MISMATCH/UNRESOLVED | ... |
```

End with:

`EVIDENCE CLERK: CLEAN`

only when every assigned check is reconciled and no material integrity mismatch
remains. Otherwise end:

`EVIDENCE CLERK: FINDINGS`
