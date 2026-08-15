# DSD Optional Policy Examples

This file is **not parsed as a configuration schema**. It only shows optional choices a run may record in its own durable state/rules. Defaults live in `SKILL.md`; do not put credentials here.

## Worker backend

Default technical worker: external OpenCode using `opencode-go/deepseek-v4-flash`.

If OpenCode state must be relocated, keep it outside every project/worktree:

```text
DSD_OPENCODE_STATE_ROOT=/absolute/external/path
```

Parent harness and worker harness are independent; see `HARNESS.md` only when routing differs from the default.

## Stable run rules

Put genuine environment-specific constraints once in the immutable run worker-rules revision instead of repeating them in every task. Do not copy shell/path restrictions from another project unless they actually apply.

## Role routing

Roles normally share the cheap worker profile; behavior comes from the exact role skill + task contract. Reviewer/Fixer/Recovery/Phase Auditor use fresh contexts. Evidence Clerk is on-demand and always project-read-only.

Implementer/Fixer discover the implementation surface themselves. An explicit `Allowed source changes` section is exceptional authority supplied by the plan/user, not a list the parent should research for DSD.

## Context / narration

Use host-provided context percentages only when they are real. Otherwise rely on the checkpoint hooks described in `COMPACTION.md`. Routine worker transitions are silent; speak for consequential escalation, reviewed phase result, final completion, or direct user request.

## Kilo native workers

Kilo is a first-class parent harness. OpenCode/DeepSeek remains the default worker backend. If a run explicitly chooses Kilo-native workers, record that choice in the run state/rules and use the native attempt lifecycle from `KILO.md`.
