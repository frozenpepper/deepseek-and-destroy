# DeepSeek and Destroy

DeepSeek and Destroy (DSD) is a plan-execution skill for using a strong premium model as
an **orchestrator** while delegating repository-heavy work to cheaper specialist models.
The design goal is high assurance with low premium-context and token waste.

## Core boundary

- **Premium parent:** authority, decomposition, routing, acceptance, architecture choices.
- **Technical workers:** discovery, implementation, fixing, review, verification, recovery.
- **Python helpers:** objective facts only—identity, hashes, lifecycle, scope movement,
  immutable bindings, write boundaries.
- **Evidence Clerk:** optional cheap semantic adapter for long/awkward worker evidence.

Worker prose is not a machine protocol. DSD does not accept/reject engineering work
because a model omitted a verdict marker, AC label, Markdown table, or exact wording.

## Normal lifecycle

The parent creates a small immutable JSON-backed task contract, chooses a role, then uses
one launch transaction:

```bash
python3 scripts/dsd_attempt.py launch \
  --state /abs/run/state.json --phase P1 --task U1 --role reviewer
```

A new attempt is self-contained:

```text
phases/<phase>/<task>/attempts/<role>-<n>/
  prompt.txt
  scope-baseline.json
  launch-reservation.json
  attempt.json
  report.md
  worker.log
  terminal.json
  scope-diff.json
  evidence-gate.json
```

After the exact terminal event appears:

```bash
python3 scripts/dsd_attempt.py gate \
  --state /abs/run/state.json --phase P1 --task U1
```

The gate verifies mechanical integrity and returns a bounded **non-authoritative report
surface**. The parent reads that small surface. If semantic mapping/compression is still
expensive, one Evidence Clerk turns the existing report + mechanical gate into a small
semantic packet. Missing technical proof becomes a targeted specialist task, not a rerun
of a long worker for formatting.

## Context economy

The always-loaded parent instructions live in `SKILL.md`. Everything else is lazy:

- `WORKSPACE.md` — recovery, state/provenance edge cases, phase barriers;
- `PROMPTS.md` — manual contract/helper reference;
- `CLAUDE.md`, `CODEX.md`, `KILO.md`, etc. — active parent harness only;
- `OPENCODE.md` — transport/provider/database troubleshooting only;
- `COMPACTION.md` — checkpoint/rehydration only.

A worker sees only:

1. immutable run rules;
2. `worker/COMMON.md`;
3. its single role skill;
4. its task contract;
5. optionally `PROOF-PATTERNS.md` **only when the contract names a recipe**;
6. explicitly supplied immutable evidence paths when needed.

It does not receive unrelated role manuals or the whole parent skill.

## Roles

- **Discovery:** bounded fact finding; no project writes.
- **Phase Surveyor:** phase-level dependency/scope map; no project writes.
- **Implementer:** bounded project mutation.
- **Fixer:** bounded repair after a demonstrated defect.
- **Reviewer:** fresh adversarial semantic review; no project writes.
- **Verification:** one bounded predicate; read-only unless the contract explicitly grants
  generated/project artifact paths.
- **Recovery:** read-only forensic disposition of interrupted/ambiguous work.
- **Phase Auditor:** fresh read-only whole-phase audit after the write barrier closes.
- **Evidence Clerk:** always project-read-only; interprets/compresses existing evidence.

Every accepted project mutation requires fresh independent review. No worker self-approves.

## Mechanical safety

`launch-reservation.json` is the immutable authority for an attempt. It binds role/task,
prompt, task contract, worker rules, scope baseline, report/log paths, and hashes.

Scope baselines cover tracked + untracked-nonignored Git content while excluding only
`DeepSeekAndDestroy/`. A task may declare ignored/load-bearing roots with `Extra scope
inventory`; those are recursively inventoried too. Read-only roles fail on project
movement. Writers fail on paths outside exact `Allowed source changes`.

These checks prove **what happened to bytes/processes**, not whether engineering prose is
convincing. Semantic adequacy remains an LLM/parent responsibility.

## Contracts and state

Prefer:

```bash
python3 scripts/render_task_contract.py --spec contract.json
```

Contracts should remain small. Use only fields needed for the task: objective, authority,
inputs, write scope, ACs, proof obligations, optional proof recipes, verification,
exclusions, and extra ignored-tree inventory.

Use `dsd_state.py` for routine state transitions instead of hand-written JSON mutations.
It validates a candidate with `check_state.py` before atomically replacing `state.json`.

## Report recovery

A completed worker whose report is missing or still the launcher skeleton is **not** an
engineering failure. Preserve the exact attempt evidence. Interpret recoverable evidence
with one Clerk when possible; use Recovery when technical/project state is ambiguous.
Do not rerun hours of technical work just to obtain preferred report formatting.

## Harnesses

Supported first-class parent adapters: Codex, Claude Code, OpenCode, and Kilo. Install
project-local hooks/plugins with `scripts/install_harness_adapter.py`; Kilo worker agents
use `scripts/install_kilo_workers.py`.

OpenCode worker databases must live outside the project tree to avoid project-copy/
SQLite interference. See `OPENCODE.md` only when transport details matter.

## Testing

The current regression suites separate mechanical integrity from semantic interpretation:

```bash
python3 -m unittest tests.test_v15_3_consolidation -v
python3 -m unittest tests.test_v15_2_simplification -v
python3 -m unittest tests.test_v15_integrity -v
python3 -m unittest tests.test_v15_helpers -v
python3 -m unittest tests.test_v15_1_harnesses -v
```

Some harness/plugin tests spawn child processes; run suites independently if a host shell
retains inherited pipes after unittest exits.

## License

MIT. See `LICENSE`.
