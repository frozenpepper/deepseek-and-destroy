# DeepSeek and Destroy Configuration Example

Optional overrides. Omitted values inherit `SKILL.md`. Do not put credentials here.

## Default worker

```text
worker_harness: opencode-cli
worker_model: opencode-go/deepseek-v4-flash
worker_parallelism: 1
```

OpenCode worker storage is one external disposable DB per run. Set an external root
only when desired:

```text
DSD_OPENCODE_STATE_ROOT=/absolute/path/outside/every/project/worktree
```

If explicit parallel OpenCode workers are enabled, use one external DB per
concurrency lane; see `OPENCODE.md`.

## Orchestrator harness

```text
orchestrator_harness: auto   # claude-code | codex | opencode | kilo | custom
```

This controls wait/compaction behavior, not the worker model. See `HARNESS.md`.

## Stable worker rules

Do not repeat stable environment constraints in every prompt. Pass them when
creating an immutable run worker-rules revision such as
`worker-rules/r0001/WORKER_RULES.md`, e.g.:

```text
worker_stable_rules:
  - launcher working directory is authoritative; do not cd to compensate for path mistakes
  - use exact run/report paths supplied by the task
  - <project-specific shell restriction only if actually required>
```

Do **not** blindly copy a shell rule from another project. Rules such as “no
heredocs” belong here only when the actual environment requires them.

## Role routing

All roles normally use the same cheap OpenCode/DeepSeek profile; role behavior comes
from the run-local protocol snapshot and task contract:

```text
phase-surveyor -> DeepSeek worker
discovery      -> DeepSeek worker
implementer    -> DeepSeek worker
reviewer       -> fresh DeepSeek worker
fixer          -> fresh DeepSeek worker
verification   -> DeepSeek worker (read-only unless exact generated-artifact writes are declared)
evidence-clerk -> DeepSeek worker (always project-read-only)
recovery       -> fresh DeepSeek worker
phase-auditor  -> fresh DeepSeek worker
```

No role is allowed to silently fall back to the premium orchestrator for technical
execution. Every attempt uses the project scope baseline; writer changes are additionally constrained by the contract's exact `Allowed source changes`.

## Reviewer attack budget

```text
review_risk_hypotheses_max: 3
```

Use sharp falsifiable hypotheses with an executable attack; do not spend the budget
on generic concerns already covered by Worker Core.

## Evidence Clerk

Default is conditional, not ceremonial:

```text
evidence_clerk: on-demand
```

Run it only at a parent semantic-consumption boundary when the bounded source report is too long/unclear to interpret cheaply. Implementer/Fixer normally flow directly to fresh Reviewer. Clerk interprets existing evidence only, is project-read-only, and never owns `state.json` or acceptance.

## User narration

```text
routine_user_update_words: 25
```

Routine transitions are silent unless the host requires an update; then use one
sentence. Expanded prose only for material correction, human blocker, consequential
decision, phase result, final completion, or direct user request.

## Context checkpoints

```text
checkpoint_due_percent: 65
compact_before_percent: 75
hard_ceiling_percent: 80
```

Use exact percentages only when the host exposes real context usage. Otherwise use
native hooks/safe-boundary fallback from `COMPACTION.md`.

## Kilo Code

Kilo is a first-class orchestrator harness. The default worker backend remains
OpenCode/DeepSeek. To explicitly select Kilo-native workers, install the project
subagents and use the native attempt lifecycle in `KILO.md`; native delegation does
not bypass DSD scope/evidence gates. A run that opts into the native backend records
that choice explicitly, for example:

```text
worker_harness: kilo-native
worker_model: deepseek/deepseek-v4-flash
```
