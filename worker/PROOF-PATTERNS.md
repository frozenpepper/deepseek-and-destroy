# DSD Proof Patterns

These are small recipes, not universal rules. Attach only patterns genuinely
relevant to the task. Discovery/Survey workers should recommend tags when useful.

## NEGATIVE-GATE

Use for authorization, approval, validation, eligibility, fail-closed behavior,
or similar gates.

Proof requires:

- one realistic allowed input that reaches and passes the gate;
- one realistic invalid input that reaches and is rejected by the gate;
- evidence that rejection came from the named gate rather than an earlier failure;
- authority independent of the object being gated.

A gate that cannot realistically say "no" is not proven. Self-attestation such as
copying an object's owner into `approvedByOwner` and comparing them is vacuous.

## CARDINALITY

Use when behavior varies with collection size, scale, batches, fan-out, or
multi-member creation.

Proof requires more than cardinality one. Exercise at least one relevant `>1`
case and assert individual mappings/relationships, not only totals or kind sets.
A plausible "last item wins" or "all children attach to one parent" bug must make
the evidence fail.

## IDENTITY

Use for persisted graphs, parent/child relationships, references, ownership, or
entity resolution.

Structural relationships must be derived from the project's canonical identity or
reference contract. Names, prefixes, order, proximity, or display labels are not
identity unless the schema explicitly defines them as such. Proof should assert
exact source/target identities where correctness depends on them.

## DURABILITY

Use for persistence, restart, resume, recovery, or crash guarantees.

Proof crosses the boundary named by the contract. For durable restart, instance A
writes, instance A is discarded, a fresh instance B starts against durable state,
and B reconstructs correctly. Same-instance continuation is insufficient.

## DERIVED-EVIDENCE

Use for generated status tables, dashboards, gate matrices, acceptance reports, or
other derived evidence.

Each distinct green claim must be backed by the predicate its contract names. One
scan/predicate may serve multiple cells only when those contracts are explicitly
identical. Per-kind/per-target requirements need per-kind/per-target evidence, not
an aggregate root-level green.
