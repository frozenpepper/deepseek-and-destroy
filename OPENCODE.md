# DSD OpenCode Worker Adapter

Cold reference for default **worker transport**. Parent may use any supported harness; external workers use OpenCode unless configured otherwise.

Defaults: model `opencode-go/deepseek-v4-flash`; fresh session on role change; one external disposable DB for the active phase, reused for same-role continuation.

## External DB invariant

Never use the user's interactive OpenCode DB or place a worker DB inside the repository/run tree: project refresh can scan its own live SQLite file. Persist one absolute external path in `state.json`; isolated parallel lanes may use one DB each. Prefer an OS cache root such as `~/Library/Caches/DeepSeekAndDestroy/opencode/<run-id>/workers.db` or `${XDG_CACHE_HOME:-~/.cache}/deepseek-and-destroy/opencode/<run-id>/workers.db`.

The DB is **phase session state, not per-attempt trash**. Keep it through the active phase so healthy sessions survive CLI turn endings. After **approved phase close**, when no worker/monitor is live and no continuation/recovery needs those sessions, delete the DB plus SQLite `-wal`/`-shm`; the next launch recreates it at the configured path. Never rotate at attempt/task boundaries or while the phase may resume.

## Normal path

Do not hand-build OpenCode commands or attempt paths:

```bash
python3 <skill>/scripts/dsd_attempt.py launch --run-root <run> --phase-id <phase> --task-id <task> --role <role> [--detach]
# detached only
python3 <skill>/scripts/dsd_attempt.py wait   --run-root <run> --phase-id <phase> --task-id <task>
python3 <skill>/scripts/dsd_attempt.py gate   --run-root <run> --phase-id <phase> --task-id <task> [--surface]
```

Use `--surface` only at a parent interpretation boundary; intermediate gates return mechanics. `dsd_attempt.py` derives runtime, immutable attempt authority, baseline, fresh report/log paths, invocation, and state binding. Lower helpers are recovery/test primitives.

## Lifecycle / waiting

`launch-reservation.json` is immutable attempt authority; `attempt.json` records the running child; `terminal.json` records the exact child exit. **Exit 0 ends that CLI process turn only; it does not prove task completion.**

Wait quiescently. One wait/tool timeout without terminal evidence is a non-event. Repeated timeouts plus a credible stall signal permit one bounded diagnosis; log age/size and recorded liveness are clues, not proof. Never continuously poll logs, CPU, or repository state in premium context.

After terminal:
- exit 0 → objective integrity gate, then decide whether the task is actually finished;
- post-start nonzero/abnormal exit → preserve attempt and suspect changes for Recovery;
- clear pre-start/provider failure → availability handling.

A background writer surviving terminal invalidates the no-more-writes assumption and enters Recovery.

## Report placeholder

The launcher pre-creates a byte-distinct report placeholder. If unchanged at terminal, the gate reports **report recovery**, not semantic failure or “no source changes.” Preserve the attempt; never rerun merely for formatting. After terminal/reconciled incomplete lifecycle, inspect a bounded tail before relaunching when `worker.log` is substantial, to recover stranded findings/pointers; log prose remains claims, not semantic acceptance.

Reports remain natural language; no FINAL/verdict/table grammar is required.

## Sessions and benign early stops

Role change = fresh session; durable evidence carries context between roles. Same-role work should reuse a trustworthy session when useful.

OpenCode can normally exit `0` while the current contract is unfinished. Do **not** call that task success, transport failure, or a cold-rerun case. If `terminal.json.session_id` exists and the phase DB remains, launch a **new numbered same-role attempt** with `--resume-session <session-id>` and minimal exact input, e.g. `Continue the current contract from this session; finish outstanding work and write this attempt's self-contained report.` The new attempt still gets fresh immutable reservation/baseline/log/terminal/report evidence.

Use the same path after trustworthy transport/recovery or `DECISION_REQUIRED`. If authority/scope/acceptance materially changed, bind the new contract revision first. If session continuity is uncertain/unavailable, start a fresh same-role attempt.

## Provider trouble

Before burning attempts on empty/banner/auth/provider failures: verify the exact model id with `opencode models`; probe it using `scripts/opencode_probe.py` and a fresh external temporary DB; classify availability separately from task failure; persist backoff/fallback state. Do not infer billing exhaustion from an error string alone. Credentials stay in OpenCode's normal auth/config, separate from `OPENCODE_DB`.

## OpenCode as premium parent

Parent/worker sessions are separate. Workers use the external phase DB above. Install the project-local compaction adapter when desired; `COMPACTION.md` governs checkpoint/resume.
