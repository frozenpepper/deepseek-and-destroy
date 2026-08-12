# DSD Configuration Example

Optional overrides only; omitted values inherit `SKILL.md`. Never store credentials here.

```text
worker_harness: opencode-cli
worker_model: opencode-go/deepseek-v4-flash
worker_parallelism: 1
orchestrator_harness: auto   # claude-code | codex | opencode | kilo | custom
review_risk_hypotheses_max: 3
checkpoint_due_percent: 65
compact_before_percent: 75
hard_ceiling_percent: 80
```

OpenCode state must be outside every project/worktree, e.g.
`DSD_OPENCODE_STATE_ROOT=/absolute/external/cache`; deliberate parallel lanes use separate
DBs. See `OPENCODE.md` only for transport details.

Stable environment/project constraints belong once in an immutable worker-rules revision,
not repeated task prompts. Do not copy shell restrictions from unrelated projects.

All roles normally use the same cheap worker model; behavior comes from Common + one role
skill + task contract. Role changes start fresh sessions. Evidence Clerk is on-demand and
always project-read-only. Verification is read-only unless its contract explicitly grants
generated/project paths. No role silently falls back to premium technical execution.

Use exact context percentages only when the host exposes real counters; otherwise rely on
`COMPACTION.md` safe-boundary/hook behavior. Kilo-native workers are opt-in and still use
the same immutable attempt/scope lifecycle (`KILO.md`).
