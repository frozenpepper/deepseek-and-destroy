# DSD Task Specs and Worker Handoffs

Cold reference. Normal parent operation should use the high-level helpers rather than recompose launch mechanics manually.

## Semantic task spec

Author one small JSON object and render it:

```bash
python3 <skill>/scripts/render_task_contract.py --spec <spec.json>
```

Typical spec:

```json
{
  "run_root": "/abs/project/DeepSeekAndDestroy/plans/p/runs/r",
  "phase_id": "phase-4",
  "task_id": "U17",
  "title": "Persist canonical media state",
  "objective": "Persist canonical media selection across a real restart.",
  "authority": ["docs/architecture.md"],
  "inputs": ["DeepSeekAndDestroy/.../discovery.md"],
  "extra_inventory": [".runtime/media"],
  "acceptance": [
    "selected media survives a fresh-process restart",
    "invalid persisted media fails closed to the canonical fallback"
  ],
  "proof_patterns": ["DURABILITY", "NEGATIVE-GATE"],
  "verification": ["npm test -- media"]
}
```

Keep only task-specific **deltas**. Point `authority` at readable plan/ADR/source or a recorded major decision (for example `D-039`) instead of copying it into `objective`. Empty optional fields may be omitted. Implementer/Fixer normally discover their own implementation files. Add `write_paths` only when authority already says the task is confined to specific files/directories; presence makes that boundary mechanically hard, and an explicit empty list means no project writes. `extra_inventory` is likewise optional for already-known ignored/load-bearing roots.

Acceptance/proof text guides capable workers and reviewers; Python does not parse it to judge engineering success. `AC-*` labels are optional readability aids and are assigned automatically when absent.

There is no task-level `Evidence Clerk Checks` field. Clerk is chosen on demand at a semantic consumption boundary, not recursively encoded in the technical task.

A contract revision becomes immutable at first launch. A mid-task parent decision that merely resolves an ambiguity within the existing task can be recorded durably and passed back as exact input when resuming the same role/session. Material changes to semantic authority/scope/acceptance still create a new numbered revision.

## Worker-rules snapshot

A run revision contains:

```text
WORKER_RULES.md                         # run facts/run-specific constraints
MANIFEST.json                           # cryptographic snapshot binding
protocol/COMMON.md                     # universal worker rules
protocol/roles/dsd-<role>/SKILL.md     # specialist doctrine
protocol/PROOF-PATTERNS.md              # optional recipe library
```

`WORKER_RULES.md` must not duplicate Common/role doctrine or changing task content.

## Tiny launch handoff

`render_worker_prompt.py`/`dsd_attempt.py launch` creates the handoff. Conceptually:

```text
DSD <ROLE> for <task>.
Read and obey:
1. <rules>/WORKER_RULES.md
2. <rules>/protocol/COMMON.md
3. <rules>/protocol/roles/dsd-<role>/SKILL.md
4. <task-contract>
5. <rules>/protocol/PROOF-PATTERNS.md   # only when the task names proof recipes
Prior evidence: <exact immutable paths/hashes, only when needed>
Report: <attempt>/report.md
```

Do not inline manuals, prior reports, or project history. Role selection is explicit; native skill discovery is not production authority. A role change gets a fresh session.

## Worker report

The report is natural technical evidence for another capable model, not a machine wire format. Ask for the conclusion first, then what was done/checked, decisive evidence, verification actually performed, defects/uncertainty/decision boundaries, and useful evidence paths.

No exact `Verdict:` line, finality token, Decision Packet, Proof Matrix grammar, AC-string repetition, defect section, or test-count syntax is required for mechanical acceptance.

If the bounded report surface is insufficient for the parent, use one read-only Evidence Clerk to interpret existing evidence. Missing technical proof goes to targeted Verification/Review, not report-format repair.

## Normal lifecycle

```bash
python3 <skill>/scripts/dsd_state.py bind-contract ...
python3 <skill>/scripts/dsd_attempt.py launch ...
# detached only: dsd_attempt.py wait ...
python3 <skill>/scripts/dsd_attempt.py gate ...              # mechanics only
# parent decision boundary only: add --surface
# optional only when semantic compression is useful:
python3 <skill>/scripts/dsd_attempt.py interpret ...
# then gate that Clerk attempt like any other worker
python3 <skill>/scripts/dsd_state.py accept-task ...
```

These helpers derive mechanical paths/state. The parent still chooses task semantics, role, routing, and acceptance.
