# DeepSeek and Destroy — Kilo Code Adapter

Use this when the **premium orchestrator** runs in Kilo Code, or when the run
explicitly selects Kilo-native workers. The default DSD worker backend remains
external OpenCode + DeepSeek unless configuration says otherwise.

Kilo support has two independent pieces:

1. **orchestrator continuity** — project-local compaction plugin + DSD checkpoint
   helpers;
2. **optional native workers** — Kilo subagents with the same immutable DSD
   task/report/evidence lifecycle as external workers.

## Orchestrator adapter

Install project-locally:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py \
  --harness kilo \
  --project-root <project-root> \
  --skill-root <skill-root>
```

The installer copies the canonical plugin to:

```text
.kilo/plugin/dsd-compaction.ts
```

and installs the normal DSD checkpoint helpers under
`DeepSeekAndDestroy/tools/`. Restart/reload Kilo so the project-local plugin is
active. The plugin prepares a durable checkpoint before native compaction and
injects the DSD resume instruction into compaction context; `verify-resume`
remains the authority before new project work.

If the local Kilo build/plugin loading is uncertain, use the manual/fresh-session
fallback in `COMPACTION.md`. Do not infer continuity merely because Kilo produced
its own summary.

## Optional Kilo-native worker backend

Kilo supports isolated project subagents. DSD provides two capability wrappers:

- `dsd-mutating-worker` — Implementer/Fixer, plus an Evidence Clerk only when its
  exact task contract authorizes a project documentation write;
- `dsd-readonly-worker` — Reviewer, Verification, Discovery, Phase Surveyor,
  Recovery, Phase Auditor, and evidence-only Evidence Clerk.

Install them project-locally:

```bash
python3 <skill-root>/scripts/install_kilo_workers.py \
  --project-root <project-root>
```

The default model is `deepseek/deepseek-v4-flash`; the installer validates the
configured model against `kilo models` unless `--skip-model-verify` is explicitly
used. Project agents are installed under `.kilo/agents/`. Global installation is
opt-in only.

### Native attempt lifecycle

Native Task delegation must still produce the same DSD launch authority and
terminal evidence as every other worker backend. It does **not** bypass scope or
evidence gates.

Immediately before invoking the Kilo Task tool:

```bash
python3 <skill-root>/scripts/native_worker_attempt.py reserve \
  --harness kilo \
  --project-root <project-root> \
  --run-root <run-root> \
  --task-id <task-id> \
  --role <role> \
  --attempt <n> \
  --prompt-file <absolute-launch-prompt> \
  --task-contract <absolute-contract> \
  --worker-rules <absolute-WORKER_RULES.md> \
  --scope-baseline <absolute-scope-baseline> \
  --report <absolute-report> \
  --event-dir <absolute-attempt-dir> \
  --log <absolute-worker-log>
```

Then invoke exactly one installed Kilo subagent with the tiny path-only launch
prompt. Select the wrapper from the task's actual write capability, not just its
semantic role name.

After the Task tool returns normally:

```bash
python3 <skill-root>/scripts/native_worker_attempt.py finalize \
  --event-dir <absolute-attempt-dir> \
  --status completed
```

If the native Task invocation itself fails, finalize with `process-error` or
`transport-error` and record the error. A semantic Reviewer `FAIL` is still a
**completed transport**; semantic verdict belongs in the worker report and is
handled by `evidence_gate.py`.

The native Task return is the terminal boundary for this backend. Do not fabricate
`completed` while the subagent is still active.

After finalization, run the ordinary DSD evidence/scope gate exactly as for an
external worker. `launch-reservation.json` remains the immutable attempt authority.

## Fresh role boundaries

Normal role changes always start a fresh Kilo subagent session. Pass the immutable
report/evidence path to the next role. Same-role session continuation is only for
an explicit trustworthy transport/recovery case.

## Read-only independence

The read-only Kilo wrapper denies edit operations outside `DeepSeekAndDestroy/**`.
It may execute verification commands when the task requires them, but its prompt
also forbids using shell commands as an alternate write channel. Any unexpected
project-source movement is independently caught by the full DSD scope gate and
invalidates read-only independence.

## Health / setup failures

For suspected Kilo/provider setup trouble, use a trivial cheap health check before
burning repeated substantive attempts. Authentication/setup failures are
availability problems; malformed/empty outputs are transport/report problems; a
well-formed semantic FAIL enters the ordinary repair loop.

Kilo-native workers do not use `OPENCODE_DB`. External OpenCode workers continue to
use the run-scoped DB policy in `OPENCODE.md`.
