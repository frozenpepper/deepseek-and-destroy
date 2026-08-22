---
name: deepseek-and-destroy
description: "Premium judgment; cheap repository specialists; deterministic helpers for objective integrity."
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

**Trust the specialist chain.** After mutation, fresh Reviewer is routine technical verification; parent does not repeat it for reassurance. Parent self-verification belongs at the frozen **phase gate** or an explicit authority/judgment escalation.

## Premium discipline

Use smallest sufficient evidence: **mechanics → bounded `--surface` → Clerk → targeted evidence → full report**. Stop when supported.

- Do not consume Implementer/Fixer output to duplicate specialist judgment. Recovery/lifecycle/contract shaping may inspect bounded evidence to recover findings/pointers without re-reviewing.
- Do not duplicate specialist investigation/verification. A bounded source read/search may cheaply answer a contract-shaping/parent-only question; delegate broad tracing, proof, tests, and re-review.
- Contracts are **deltas over reviewed authority**: name exact steps/sections and only unstated requirements; add write bounds only when authority defines them.
- Do not hand-edit accepted worker/project artifacts. Route corrections as a bounded new revision/task.
- If DSD mechanics fail, delegate bounded framework investigation when possible; premium source archaeology is a last resort.
- **Routine execution is silent.** Do not yield merely to summarize: execute safe `next_action` first. Speak only for completion, real decision/block/escalation, reviewed phase-end, user pause/request, or material in-flight finding. When speaking, assume the user saw none of the worker output: give the current objective, material status and why it matters, recommendation/decision if any, and next action. Be concise; avoid unexplained internal shorthand.

## Context locality and resume

Parent hot context is this file + one harness adapter. Cold-load: `WORKSPACE.md` for lifecycle/recovery; `OPENCODE.md` for transport/session trouble; `COMPACTION.md` for checkpoint recovery; `PROMPTS.md` for task/handoff authoring/debugging. On the first abnormal lifecycle symptom load `WORKSPACE.md` before improvising; on the first transport/provider/session symptom load `OPENCODE.md` before diagnosing or retrying. Workers get run facts + `worker/COMMON.md` + one role + task; proof recipes only when requested.

On a fresh parent session, **do not reconstruct the run**. Resolve identity from explicit binding or minimal DSD `state.json` metadata—not plans/git/reports/session history—then read live state first. Use `state.run_root` verbatim. Execute a mechanical `next_action` immediately; for semantic action read only named decision/evidence/authority. If active runs stay ambiguous, require exact run authority.

## Normal execution

Once the run is known, read authority for the next parent decision and delegate repository-scale measurement. One task = one independently reviewable semantic objective. Sweep a recognizable same-root-cause family once inside that boundary. If writer orientation needs substantial discovery, measure first with read-only Discovery and pass its map forward. **Implementer/Fixer choose the files needed to satisfy authority.** Do not predict the diff; supply known entry points, symbols, invocations, findings, and evidence paths as orientation. `write_paths` is only for authority-imposed hard bounds; Python enforces it.

Repeated run-specific instructions belong in the next worker-rules revision; universal doctrine stays in the skill and task authority in the contract. Run rules may narrow, never contradict protocol or reintroduce report grammar.

Workers own routine engineering choices. If one uncovers a consequential decision beyond current authority, consume its bounded `DECISION_REQUIRED`, record the parent decision, and resume the same role/session with it as exact input. Recut the contract only if authority, scope, or acceptance materially changed.

```text
dsd_attempt.py launch --run-root … --phase-id … --task-id … --role … [--detach]
dsd_attempt.py wait   --run-root … --phase-id … --task-id …    # detached only
dsd_attempt.py gate   --run-root … --phase-id … --task-id … [--surface]
```

Use `--surface` only at a parent semantic boundary; intermediate gates return mechanics only. Wait quiescently: one timeout without terminal evidence is a non-event. Repeated timeouts plus a credible stall signal may trigger one bounded diagnosis; log age/size or recorded liveness are clues, never proof, and continuous model-visible polling stays forbidden. Role changes use fresh contexts. A terminal exit, including `0`, ends only that process turn; unfinished trustworthy same-role work should resume its recorded OpenCode session in a new attempt. See `OPENCODE.md`.

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

A clean mechanical gate means **safe to interpret**, never semantic PASS. Hard failures are objective integrity failures only. Worker prose is a claim/evidence index, not proof of artifact state; parent decides semantics and `accept-task` records provenance.

Phase close: finish writers → exercise finalization operations that establish/refer to the final snapshot → freeze → required post-freeze Verification → fresh Phase Auditor → **parent phase judgment**. Finalization must not require later mutation inside that snapshot or a self-invalidating dependency cycle; later mutation invalidates stale phase evidence. After approved close, perform adapter phase cleanup (`OPENCODE.md`).

Scope-observed mutation is exclusive per checkout: read-only attempts overlap only each other; no worker/parent may mutate observed project state while one is live. Parent project edits count. Writer + read-only requires isolated worktrees. Ask the human only for uninferable authority, access/authorization, destructive/paid/live permission, persistent worker unavailability, or irreconcilable authority conflict. Give finding and recommendation, not a menu.
