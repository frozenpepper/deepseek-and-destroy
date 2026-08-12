# DSD Kilo-native Worker Backend

Cold reference. Load only when configuration explicitly selects Kilo-native subagents instead of the default external OpenCode workers.

## Install

```bash
python3 <skill>/scripts/install_kilo_workers.py --project-root <project>
```

Agents install under `.kilo/agents/`:
- `dsd-mutating-worker` — Implementer/Fixer; Verification only with exact authorized writes;
- `dsd-readonly-worker` — Reviewer, Discovery, Phase Surveyor, Recovery, Phase Auditor, Evidence Clerk, read-only Verification.

The default model is `deepseek/deepseek-v4-flash`. The installer validates against `kilo models` unless `--skip-model-verify` is deliberately used.

## Native attempt boundary

A native Task call must use the same immutable attempt lifecycle as external workers.

Before invoking the Kilo subagent, derive/capture the attempt prompt, scope baseline and paths, then reserve it:

```bash
python3 <skill>/scripts/native_worker_attempt.py reserve \
  --harness kilo --project-root <project> --run-root <run> \
  --task-id <task> --role <role> --attempt <n> \
  --prompt-file <prompt> --task-contract <contract> \
  --worker-rules <WORKER_RULES.md> --scope-baseline <baseline> \
  --report <report> --event-dir <attempt-dir> --log <log>
```

Invoke exactly one installed subagent with the tiny path-only prompt. Choose the wrapper from actual task write capability, not merely the role name.

When the Task tool returns:

```bash
python3 <skill>/scripts/native_worker_attempt.py finalize \
  --event-dir <attempt-dir> --status completed
```

A semantic Reviewer failure is still transport `completed`; meaning belongs in the report. If the native Task invocation itself fails, finalize `process-error` or `transport-error`. Never fabricate completion while the subagent is active.

Then run the ordinary objective DSD gate against that attempt. `launch-reservation.json` remains immutable attempt authority.

## Capability rules

Read-only wrappers deny project edits outside DSD evidence and prompts also forbid shell-command write bypasses; the independent scope gate is the final objective enforcement.

Verification uses the mutating wrapper only when its immutable contract explicitly grants exact generated/project paths. Evidence Clerk is always project-read-only. Normal role changes start fresh subagent sessions; durable evidence carries context.

Kilo-native workers do not use `OPENCODE_DB`.
