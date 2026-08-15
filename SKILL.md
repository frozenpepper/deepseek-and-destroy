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

## Ownership and trust

- **Parent:** authority, decomposition, role choice, consequential decisions, acceptance, phase approval.
- **Workers:** repository-scale discovery, implementation, repair, review, verification, recovery, phase audit.
- **Python:** objective facts only—immutable bindings/hashes, lifecycle, source movement, explicit authority restrictions, and resume continuity. Never infer engineering meaning from prose.
- **Clerk:** optional cheap semantic compressor; interpret existing evidence only. Never invent/verify missing proof, edit project state, waive integrity, accept work, or recurse.

**Trust the specialist chain.** After mutation, the fresh independent Reviewer is routine technical verification. The parent does not repeat that work for reassurance. Parent self-verification belongs at the frozen **phase gate** or an explicit worker escalation requiring parent authority/judgment.

## Premium discipline

Use the smallest sufficient evidence: **mechanics → bounded `--surface` → Clerk → targeted evidence → full report**. Stop when the decision is supported.

- Never read Implementer/Fixer output when another specialist is the next consumer; pass its immutable evidence onward.
- Never rerun tests, grep source, recompute hashes, or re-review a clean fresh review except for phase approval or a parent-only escalation.
- Contracts are **deltas over reviewed authority**. Never restate readable authority: name the exact step/sections and only requirements not already stated there; include a write boundary only when authority already defines one.
- If contract authoring needs broad source/repository tracing, delegate Discovery first. Parent source inspection is for targeted evidence needed by a consequential parent-only decision.
- Do not hand-edit accepted worker/project artifacts. Route corrections as a bounded new revision/task.
- If DSD mechanics fail, delegate bounded framework investigation to a cheap worker when possible. Premium source archaeology is a last resort to restore delegation.
- **Routine execution is silent.** No user narration for launches, waits, gates, reviews, fixes, or task acceptance. Speak only for major decision/escalation, concise reviewed phase-end result, or direct user request.

## Context locality and resume

Normal parent context is this file + one harness adapter. Cold-load: `WORKSPACE.md` for abnormal lifecycle/recovery; `OPENCODE.md` for transport trouble; `COMPACTION.md` for checkpoint recovery; `PROMPTS.md` for task/handoff authoring/debugging. Workers get run facts + `worker/COMMON.md` + one role + task; proof recipes only when requested.

On a fresh parent session, **do not reconstruct the run**. Resolve run identity only from explicit binding or minimal DSD `state.json` metadata—never from plans, git history, reports, or session history—then read live state first. Use `state.run_root` verbatim for helpers. Execute a mechanical `next_action` immediately; for a semantic one, read only its named decision/evidence/authority and expand only if necessary. If active runs remain genuinely ambiguous, require exact run authority.

## Normal execution

Once the run is known, read only authority needed for the next parent decision and delegate repository-scale measurement. One task = one independently reviewable semantic objective. Author compact JSON; helpers derive lifecycle paths/state. **Implementer/Fixer choose the files needed to satisfy authority.** Do not spend parent context predicting the diff. Use `write_paths` only when the governing authority itself already imposes a hard file/directory boundary; if present, Python enforces it. Authority-required bookkeeping is otherwise discovered and handled by the worker.

Workers own routine engineering choices. If one uncovers a consequential decision beyond current authority, consume its bounded `DECISION_REQUIRED`, record the parent decision, and resume the same role/session with it as exact input. Recut the contract only if authority, scope, or acceptance materially changed.

```text
dsd_attempt.py launch --run-root … --phase-id … --task-id … --role … [--detach]
dsd_attempt.py wait   --run-root … --phase-id … --task-id …    # detached only
dsd_attempt.py gate   --run-root … --phase-id … --task-id … [--surface]
```

Use `--surface` only at a parent semantic boundary; intermediate gates return mechanics only. Wait quiescently: no terminal means wait again without model polling/narration. Role changes use fresh contexts. Same-role continuation is only for trustworthy transport/recovery or for resuming a worker after a parent decision it explicitly requested.

```text
Implementer → fresh Reviewer
                   │
              FAIL └→ fresh Fixer → fresh Reviewer …
                   ↓
          parent decision boundary
                   ↓ only if useful
                  Clerk
```

Missing technical proof goes to targeted Verification/Review, never Clerk or report-format rerun. Load `WORKSPACE.md` only for abnormal lifecycle handling.

## Integrity, phase, human boundary

A clean mechanical gate means **safe to interpret**, never semantic PASS. Hard failures are objective integrity failures only; worker prose is natural evidence. The parent makes semantic decisions and `accept-task` records their evidence provenance.

Phase close: finish writers → exercise every selector/pointer/promotion/finalization operation that will establish or refer to the final snapshot → freeze → required post-freeze Verification → fresh Phase Auditor → **parent phase judgment**. Finalization must not require later mutation of an artifact inside that snapshot or create a self-invalidating dependency cycle. Any later mutation invalidates stale phase evidence.

Assume one intentional project writer per checkout; DSD does not coordinate concurrent writers. If unexpected concurrent mutation makes attribution unsafe, stop and resolve it or use an isolated worktree. Ask the human only for uninferable authority, access/authorization, destructive/paid/live permission, persistent worker unavailability, or irreconcilable authority conflict. Give the finding and recommendation, not a menu.
