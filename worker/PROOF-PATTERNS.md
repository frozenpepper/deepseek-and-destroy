# DSD Proof Recipes

Load this file only when the task names a recipe under `## Proof patterns`.

## NEGATIVE-GATE
Prove one realistic allowed input reaches/passes the named gate and one realistic
invalid input reaches/is rejected **by that gate**, using authority independent of
the object being gated. A gate that cannot realistically say no is not proven.

## CARDINALITY
For collection/batch/fan-out behavior, exercise a relevant `>1` case and assert
individual mappings/relationships, not only totals. Evidence must fail for plausible
"last item wins" or "all children attach to one parent" defects.

## IDENTITY
Where correctness depends on references/ownership, assert the project's canonical
identities. Names, prefixes, order, proximity, and display labels are not identity
unless the governing schema explicitly makes them so.

## DURABILITY
Cross the actual persistence/restart boundary. For restart durability: instance A
writes, A is discarded, fresh instance B starts from durable state and reconstructs
correctly. Same-instance continuation is insufficient.

## DERIVED-EVIDENCE
For generated matrices/dashboards/gates, each distinct green claim needs the
predicate its contract names. One aggregate predicate may serve multiple claims only
when their contracts are truly identical.
