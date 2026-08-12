# DSD — OpenCode Worker Transport Reference

Load this only for default-worker transport/configuration/recovery. Normal launches use
`dsd_attempt.py`; do not hand-compose `opencode run`.

## External run DB

Use a disposable **run-scoped OpenCode DB outside every project/worktree**. Never use the
interactive user DB and never place SQLite under the project: OpenCode project refresh can
scan its own actively-written DB and produce self-referential I/O failures.

Typical roots: macOS `~/Library/Caches/DeepSeekAndDestroy/opencode/<run-id>/workers.db`;
other systems `${XDG_CACHE_HOME:-~/.cache}/deepseek-and-destroy/opencode/<run-id>/workers.db`.
Persist the absolute path in `state.json`. Deliberate concurrent lanes may use one DB per
lane; same-role resumed sessions stay on their lane. Remove DB/WAL/SHM only after the run
is terminal and no session can resume.

## Lifecycle

`run_worker.py` is the low-level transport used by `dsd_attempt.py`. It owns cwd/model/DB,
immutable `launch-reservation.json`, report skeleton, log, process identity, and
`terminal.json`. Actual child-process exit is the no-more-writes boundary. Role changes
start fresh sessions; `--resume-session` is only for trustworthy same-role continuation.

Wait using the parent harness adapter. A wait timeout without terminal evidence is not a
hung-worker diagnosis. Successful transport enters the mechanical gate; a post-start
process failure is suspect state/Recovery, while pre-start provider/auth/transport trouble
uses availability/backoff.

The launcher skeleton is recognized by its reserved hash, not magic report prose. A
completed attempt whose report is missing/still-skeleton goes to exact-attempt Clerk/log
recovery first; do not rerun the technical worker solely for report representation.

## Provider trouble

Before repeated task attempts after empty/auth/provider failures: verify the exact model id
with `opencode models`, use `opencode_probe.py` with a fresh external temporary DB, and
classify availability separately from task semantics. Persist bounded backoff/fallback;
do not infer billing/quota state from one error string.

Credentials remain in normal OpenCode auth/config and are separate from `OPENCODE_DB`.
