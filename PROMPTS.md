# DSD Contracts / Handoffs Reference

Normally use `render_task_contract.py --spec` and `dsd_attempt.py`; load this file only
when authoring/debugging a contract or exceptional handoff.

## Contract

A contract contains only the **changing semantic surface** of one bounded task. Omit
unused fields. Typical JSON:

```json
{
  "task_id": "U17",
  "revision": 3,
  "output": "phases/phase-2/U17/contracts/r0003.md",
  "unit": "Persist canonical media state",
  "objective": "Persist canonical media selection across a real restart.",
  "authority": ["/abs/project/docs/architecture.md"],
  "input": ["/abs/run/.../discovery/report.md"],
  "write_path": ["src/media", "tests/media"],
  "acceptance": [
    "AC-001 — selection survives a fresh-process restart.",
    "AC-002 — invalid persisted media fails closed."
  ],
  "proof": ["AC-001 — fresh instance must reconstruct exact identity."],
  "proof_pattern": ["DURABILITY"],
  "verification": ["npm test -- media"],
  "extra_inventory": ["runtime/locks"]
}
```

`DSD_RUN_ROOT` may supply `run_root`; relative `output` resolves beneath it. Authority,
input, and mechanical evidence paths are absolute. `write_path`/`extra_inventory` are
project-relative. `Allowed source changes` is always explicit (`NONE` when read-only).
Every semantic acceptance entry begins with stable `AC-*`.

Useful optional keys: `risk` (max 3), `expected_scope`, `excluded`, `mechanical`,
`task_output`, `major_log`, `progress_file`, `evidence_dir`. Legacy CLI slots remain for
compatibility; do not serialize a large contract into CLI arguments when JSON works.

A launched revision is immutable. Material changes to scope/AC/authority create the next
numbered revision. Role changes normally reuse the same semantic contract; pass prior
attempt evidence as launch evidence rather than rewriting the contract solely to carry a
report path.

## Launch evidence

`dsd_attempt.py launch --evidence <path>` adds an immutable prior-evidence file to the
tiny launch handoff. Its path + SHA-256 are embedded in the immutable prompt. Use this
for Reviewer/Fixer/Clerk/Recovery handoffs when they need a specific prior report/gate.
Evidence is not governing authority.

## Worker prompt

`render_worker_prompt.py` emits only exact paths to: run rules, Common, one role skill,
task contract, optional prior evidence, assigned report, and (only when named by the
contract) the proof-recipe library. Do not restate manuals/project history in chat.

## Worker report

Worker reports are prose evidence, not a wire protocol. Ask for concise conclusion,
work/findings, verification, AC/proof coverage when applicable, defects/uncertainty, and
evidence paths. `Verdict: <role status>` is useful but not a mechanical acceptance
requirement. A long/awkward report can be interpreted by Evidence Clerk; missing proof
cannot be normalized into existence.
