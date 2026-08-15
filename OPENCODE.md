# DSD OpenCode Worker Adapter

Cold reference for the default **worker transport**. The premium parent may run in any supported harness; external workers still use OpenCode unless configuration selects another backend.

Defaults:
- model `opencode-go/deepseek-v4-flash`;
- fresh worker session on normal role changes;
- one disposable OpenCode DB per DSD run, outside every project/worktree.

## External DB invariant

Never use the user's interactive OpenCode DB and never place a worker DB inside the repository. OpenCode project refresh can otherwise scan its own live SQLite file. Persist one absolute external run DB in `state.json`; deliberate parallel lanes may use one DB per lane.

Typical roots:

```text
macOS:  ~/Library/Caches/DeepSeekAndDestroy/opencode/<run-id>/workers.db
other:  ${XDG_CACHE_HOME:-~/.cache}/deepseek-and-destroy/opencode/<run-id>/workers.db
```

Delete the disposable DB only after the run is terminal and no same-role continuation/recovery can need it.

## Normal external-worker path

Do not hand-build OpenCode commands or attempt paths:

```bash
python3 <skill>/scripts/dsd_attempt.py launch \
  --run-root <run> --phase-id <phase> --task-id <task> --role <role> [--detach]

# detached only
python3 <skill>/scripts/dsd_attempt.py wait \
  --run-root <run> --phase-id <phase> --task-id <task>

python3 <skill>/scripts/dsd_attempt.py gate \
  --run-root <run> --phase-id <phase> --task-id <task> [--surface]
```

Use `--surface` only when the premium parent is about to interpret that result. Intermediate specialist gates should return mechanics only.

`dsd_attempt.py` derives the exact contract/rules/runtime, self-contained attempt directory, scope baseline, prompt/report/log paths, immutable launch reservation, OpenCode invocation, and state binding. Lower-level helpers are recovery/test primitives, not the normal parent interface.

## Lifecycle / waiting

`launch-reservation.json` is immutable attempt authority. `attempt.json` records the running child; `terminal.json` records the exact child process exit. Process exit proves the lifecycle ended, **not** that the report is semantically complete or correct.

Wait quiescently through the active parent adapter. A wait/tool timeout without `terminal.json` is a non-event: wait again. Do not spend premium turns polling logs, CPU, or repository state unless lifecycle evidence is contradictory and Recovery needs diagnosis.

After terminal completion:
- exit 0 → objective integrity gate;
- post-start nonzero/abnormal exit → preserve attempt and suspect changes for Recovery;
- clear pre-start/provider failure → availability handling.

Workers must not leave background writers capable of mutating project state after terminal exit. Discovery of one invalidates the no-more-writes assumption and enters Recovery.

## Report placeholder

The launcher pre-creates a byte-distinct report placeholder. If it remains unchanged at terminal exit, the gate reports **report recovery**, not semantic failure and never “no source changes.” Preserve the attempt; do not rerun a technical worker merely to satisfy formatting.

Worker reports otherwise remain natural language. No FINAL/verdict/table grammar is required.

## Sessions

Normal role change = fresh session. Durable reports/evidence carry context between roles.

`run_worker.py --resume-session` exists only for trustworthy **same-role** continuation: transport/recovery, or resuming a worker after a `DECISION_REQUIRED` parent decision. Pass the durable decision as exact input. If the decision materially changed task authority/scope/acceptance, bind the new contract revision first; session continuity may still be reused. If exact continuation is uncertain, start a fresh same-role attempt.

## Provider trouble

Before burning repeated task attempts on empty/banner/auth/provider failures:
1. verify the exact model id (`opencode models`);
2. use `scripts/opencode_probe.py` with a fresh external temporary DB;
3. classify availability separately from task failure;
4. persist backoff/fallback state.

Do not infer billing exhaustion from an error string alone. Credentials remain in OpenCode's normal auth/config locations, separate from `OPENCODE_DB`.

## OpenCode as premium parent

The parent OpenCode session and worker OpenCode processes remain separate concerns. Workers still use the external run DB above. Install the project-local DSD compaction adapter when desired and use `COMPACTION.md` only for context checkpoint/resume.
