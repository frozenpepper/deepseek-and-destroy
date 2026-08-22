# Optional DSD Proof Patterns

Load this file only when the task contract names a pattern. These are reasoning recipes, not parser grammar.

- **DURABILITY** — prove state with a genuinely fresh instance/process/restart; same-instance memory is not enough.
- **FAIL-CLOSED** — exercise a realistic invalid/partial input and show the intended safe behavior rather than merely an exception path.
- **INTEGRATION** — reach the real public/runtime wiring, not only an isolated helper.
- **EXCLUSIVITY** — demonstrate both allowed and forbidden/competing paths when the claim is “only/never/exactly one”.
- **IDEMPOTENCE** — repeat the operation and show the second execution preserves the contract.
- **CONCURRENCY** — challenge ordering/race/duplicate invocation with evidence that distinguishes serialized success from accidental timing.
- **PRESERVATION** — compare accepted before/after behavior/artifacts without silently rewriting expected evidence.
- **PROVENANCE** — establish that evidence came from the claimed attempt/source rather than a stale/copied artifact.
- **REGISTERED-BASELINE** — when introducing a conformance gate over known debt, register each accepted violation by stable identity; fail on new unregistered violations and on unexplained disappearance of registered entries. Repairs deliberately remove only entries proven resolved. Never gate only on an aggregate count.

Use only patterns relevant to the task. Prefer one discriminating counterexample over many weak checks.
