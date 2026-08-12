---
name: deepseek-and-destroy
description: "Premium orchestrator for judgment; cheap specialists for repository-scale work; deterministic helpers only for objective integrity."
license: MIT
compatibility: codex, claude-code, opencode, kilo, and comparable coding harnesses
metadata:
  default-worker-harness: opencode-cli
  default-worker-model: opencode-go/deepseek-v4-flash
  workspace-root: DeepSeekAndDestroy
---

# DeepSeek and Destroy

> Spend premium context only where premium judgment is required.

Continue the authoritative plan until **COMPLETED**, **HUMAN-BLOCKED**, **PAUSED-BY-USER**, or **ABANDONED**. Tasks/reviews/retries/phases/compaction are not terminal.

## Trust and ownership

- **Parent:** authority, decomposition, role choice, consequential decisions, task acceptance, phase approval.
- **Workers:** repository-scale discovery, implementation, repair, adversarial review, verification, recovery, phase audit.
- **Python:** objective facts only—immutable bindings/hashes, lifecycle, source movement/write boundaries, protected inventories, barriers/resume continuity. Never infer engineering meaning from prose.
- **Clerk:** optional cheap semantic compressor. Interpret existing evidence only; never invent proof, verify missing predicates, edit project state, waive integrity failures, accept work, or recurse.

**Trust the specialist chain.** For mutations, the fresh independent Reviewer is the routine technical verification. The parent does not repeat technical work to gain confidence. Parent self-verification is reserved for the frozen **phase gate** or an explicit worker escalation requiring parent authority/judgment.

## Premium discipline

At a parent decision boundary use the smallest sufficient evidence, in order:

**mechanics → bounded `--surface` → Clerk → targeted evidence → full report**.

Stop as soon as the decision is supported.

- Never read Implementer/Fixer output when another specialist is the next consumer; pass its immutable evidence onward.
- Never rerun tests, grep source, recompute hashes, or independently re-review a clean fresh review except for phase approval or a parent-only escalation.
- Contracts are **deltas over referenced authority**: point to the governing plan/ADR/source; state only the bounded objective, write scope, acceptance delta, and needed verification. Do not restate readable authority.
- If DSD mechanics fail, delegate bounded framework investigation to a cheap worker when possible. Premium source archaeology is a last resort only to restore delegation.
- **Routine execution is silent.** No user narration for launches, waits, gates, reviews, fixes, or task acceptance. Speak only for a major decision/escalation or the concise reviewed result at phase end, plus direct user requests.

## Context locality

Normal parent context is this file plus exactly one harness adapter. Load only on demand:
`WORKSPACE.md` for abnormal state/evidence/recovery/barriers; `OPENCODE.md` for transport trouble; `COMPACTION.md` for checkpoint/resume; `PROMPTS.md` for task/handoff authoring/debugging.

Each worker gets immutable run facts + `worker/COMMON.md` + **one** role skill + task contract. Add `PROOF-PATTERNS.md` only when explicitly requested. Never load unrelated roles/manuals.

## Normal execution

Resolve the exact run/worktree/plan/phase; never guess among active runs. Read only authority needed for parent decisions and delegate repository-scale measurement.

One task = one independently reviewable semantic objective. Use Surveyor/Discovery if broad exploration is needed first. Author compact JSON; helpers derive lifecycle paths/state.

```text
dsd_attempt.py launch --run-root … --phase-id … --task-id … --role … [--detach]
dsd_attempt.py wait   --run-root … --phase-id … --task-id …    # detached only
dsd_attempt.py gate   --run-root … --phase-id … --task-id … [--surface]
```

Use `--surface` only when the parent is about to interpret that result. Intermediate specialist gates return mechanics only. Wait quiescently; no terminal event means wait again with no model polling/narration. Role changes use fresh contexts; same-role continuation is transport/recovery only. Load `WORKSPACE.md` for abnormal lifecycle handling.

Normal mutation path:

```text
Implementer → fresh Reviewer
                   │
              FAIL └→ fresh Fixer → fresh Reviewer …
                   ↓
          parent decision boundary
                   ↓ only if useful
                  Clerk
```

Missing technical proof goes to targeted Verification/Review, never Clerk or a report-format rerun.

## Integrity, phase, human boundary

A clean mechanical gate means **safe to interpret**, never semantic PASS. Hard failures are objective integrity failures only; worker prose is natural engineering evidence, not a machine protocol. The parent makes semantic decisions and `accept-task` records their evidence provenance.

Phase close: finish writers → freeze → required post-barrier verification → fresh Phase Auditor → **parent phase judgment**. This is the normal place for parent targeted technical verification. Any mutation invalidates stale phase evidence.

Ask the human only for genuinely uninferable authority, access/authorization, destructive/paid/live permission, unsafe concurrency, persistent worker unavailability, or irreconcilable authority conflict. Give the finding and recommendation, not a menu.
