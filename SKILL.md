---
name: deepseek-and-destroy
description: "Execute complex implementation plans with a premium orchestrator for judgment and cheap specialist workers for repository-scale work. Mechanical helpers protect objective integrity; LLMs interpret engineering meaning."
license: MIT
compatibility: codex, claude-code, opencode, kilo, and comparable coding harnesses
metadata:
  default-worker-harness: opencode-cli
  default-worker-model: opencode-go/deepseek-v4-flash
  workspace-root: DeepSeekAndDestroy
---

# DeepSeek and Destroy

> Premium context decides. Cheap workers do technical volume. Python proves only objective facts.

Continue the authoritative plan until **COMPLETED**, **HUMAN-BLOCKED**, **PAUSED-BY-USER**, or **ABANDONED**. Tasks, reviews, retries, phases, compaction, and fresh sessions are not terminal.

## Boundary

- **Parent:** user/project/plan authority, decomposition, role choice, consequential decisions, task acceptance, phase approval.
- **Technical workers:** repository-scale survey/discovery, implementation, repair, adversarial review, verification, recovery, phase audit.
- **Python:** immutable bindings/hashes, lifecycle, report-byte existence, exact source movement/write boundaries, ignored-tree inventory, barriers/resume continuity. Never infer PASS/FAIL, AC completeness, proof quality, defects, arithmetic, or engineering meaning from prose.
- **Evidence Clerk:** optional cheap semantic adapter when the parent would otherwise digest a large/unclear report. Interpret existing evidence only; never invent proof, perform missing verification, edit project state, waive integrity failures, accept work, or recurse.

## Context economy

This file is normal parent context. Load only when needed:
- `WORKSPACE.md` — state/evidence/recovery/concurrency/barriers;
- exactly one parent harness adapter;
- `OPENCODE.md` — worker transport diagnosis/recovery;
- `COMPACTION.md` — checkpoint/resume;
- `PROMPTS.md` — task/handoff authoring or debugging.

Each worker gets only immutable run facts + `worker/COMMON.md` + **one** role skill + task contract. Add `PROOF-PATTERNS.md` only when the task explicitly names a recipe. Never load unrelated roles/manuals.

## Run and task

Resolve the exact run/worktree/plan/phase/project instructions; never guess among active runs. Read authority needed for decisions, but delegate repository-scale measurement. Bind immutable worker rules and one exact `next_action`; durable state/evidence outrank chat/handover claims.

One task = one independently reviewable semantic objective. If scoping it requires broad exploration, delegate Surveyor/Discovery first. Author a compact JSON task spec and render/bind its immutable contract. Parent chooses semantics and exact project write scope; helpers derive attempt/report/log/state paths. Repeated no-progress writer attempts are a reasoning signal to re-scope—not a Python retry counter.

## Normal loop

External OpenCode path:

```text
dsd_attempt.py launch --run-root … --phase-id … --task-id … --role … [--detach]
dsd_attempt.py wait   --run-root … --phase-id … --task-id …    # detached only
dsd_attempt.py gate   --run-root … --phase-id … --task-id …
```

`launch` creates one self-contained attempt, scope baseline, path-only handoff and immutable reservation, then binds the live attempt **before waiting**. Before a role change it verifies the prior attempt is terminal and moves it to bounded `last_attempt`. A terminal-less prior attempt blocks launch unless exceptional Recovery explicitly uses `--supersede-incomplete` after establishing it cannot still write. `gate` proves objective integrity. Add `--surface` only when the parent is about to consume that worker result; intermediate specialist gates return no worker prose. Native adapters use the same reserve/finalize boundary.

Wait quiescently. No terminal event means wait again; do not spend model turns polling logs/CPU/repository. A role change starts a **fresh** context; same-role continuation is transport/recovery only.

Roles: **Phase Surveyor** (current state), **Discovery** (construction brief), **Implementer** (bounded change), **Fixer** (bounded repair), **Reviewer** (fresh adversarial read-only review), **Verification** (one predicate; writes only when exact generated/project paths are authorized), **Recovery** (suspect-change disposition), **Phase Auditor** (frozen-phase audit), **Evidence Clerk** (read-only semantic compression).

Normal mutation flow:

```text
Implementer → fresh Reviewer
                   │
              FAIL └→ fresh Fixer → fresh Reviewer …
                   ↓
        parent reads bounded surface
                   ↓ only if useful
             Evidence Clerk
                   ↓
            parent accepts/routes
```

Do not insert Clerk between specialists when the parent is not consuming the result. Missing technical proof goes to targeted Verification/Review—not Clerk and never a report-format rerun.

## Integrity vs meaning

Deterministic hard failures are only objective facts:
- immutable contract/rules/evidence or attempt identity broke;
- lifecycle is not trustworthy;
- a read-only role moved project state;
- a writer moved unauthorized paths;
- required ignored/load-bearing scope was not compared;
- post-start/reportless changes are suspect until Recovery resolves them;
- mutating work lacks fresh independent Reviewer provenance;
- phase evidence no longer describes the frozen source state.

A clean gate means only **safe to interpret**. It is never semantic PASS.

Worker reports are natural engineering evidence, not a machine protocol: no Verdict marker, finality token, Proof Matrix, AC-string repetition, defect heading, or arithmetic syntax is mechanically required.

At a parent decision boundary, gate with `--surface` and use that bounded report prefix if sufficient. Otherwise run one read-only Clerk over the exact contract/report/gate. Clerk may reconcile/compress what existing evidence establishes; missing proof remains missing. The parent makes the semantic decision. `dsd_state.py accept-task` binds the exact clean source gate and semantic report actually consumed (Reviewer directly or Clerk), validating provenance/hashes only.

## Exceptional / phase / human boundary

Load `WORKSPACE.md` for suspect changes, reconstruction, concurrency, barriers, or acceptance provenance; transport/compaction docs only for those events. Worker/provider trouble never turns the premium parent into the implementation worker.

Phase close: finish writers → freeze barrier/snapshot → required read-only post-barrier verification → fresh Phase Auditor → parent judgment. Any mutation invalidates stale phase evidence.

Ask the human only for genuinely uninferable product/architecture authority, access/authorization, destructive/paid/live permission, persistent worker availability, unsafe concurrency, or irreconcilable authority conflict. Give the finding and recommendation, not a menu.

Stay quiet between gates. Surface material findings, decisions, blockers, phase results, direct requests, and completion—not routine launch/wait bookkeeping.
