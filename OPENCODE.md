# DeepSeek and Destroy — OpenCode Adapter

Read this file only when the effective worker profile uses OpenCode CLI. It
defines the built-in DeepSeek Flash worker profile and the required isolated
ephemeral database behavior.

### Ephemeral worker storage (opencode harness only)

This section applies **only when the effective worker harness is OpenCode CLI**.
Other harnesses (Codex, claude-code, custom) have their own session/storage
models and are unaffected by these rules. If the resolved harness is not
opencode, skip this entire section.

OpenCode has no built-in ephemeral/in-memory session mode. Every `opencode run`
writes to a shared SQLite database at `~/.local/share/opencode/opencode.db` by
default. Procedural DSD runs spawn many short-lived workers (implementer,
reviewer, fixer, re-reviewer) that accumulate sessions, messages, parts, diffs,
and snapshots — quickly reaching multi-GB database growth and making the session
history unusable for real interactive work.

To prevent this, every opencode worker spawn MUST use an isolated, disposable
database file via the `OPENCODE_DB` environment variable. Each worker gets its
own throwaway SQLite file; when the worker's lifecycle is complete, the file is
deleted. This keeps the main opencode database pristine for interactive use.

> **`OPENCODE_DB` must be an absolute path (or `:memory:`).** A relative value is
> resolved by opencode against its own data directory
> (`~/.local/share/opencode/`), **not** the current working directory, so a
> relative path would create/look up the DB in the wrong location and resume
> would fail to find the stored session. Always resolve `<run-root>` to an
> absolute path before building `WORKER_DB`, and store the
> absolute path verbatim in `state.json`.

The pattern:

1. **Before spawning a worker**, create a unique ephemeral DB path (absolute):
   ```bash
   # RUN_ROOT is the absolute path to this orchestrator run directory
   EPHEMERAL_DB_DIR="$RUN_ROOT/ephemeral-db"
   mkdir -p "$EPHEMERAL_DB_DIR"
   WORKER_DB="$EPHEMERAL_DB_DIR/<task-id>-<role>-<round>.db"
   # WORKER_DB is absolute and is what gets recorded in state.json
   ```

2. **Launch the worker** with `OPENCODE_DB="$WORKER_DB"` prefixed on the command.

3. **Resume the same worker** with the same `OPENCODE_DB="$WORKER_DB"` value
   (the absolute path recorded in `state.json`) so the session ID resolves in
   the worker's own database.

4. **After the worker's full lifecycle ends** (report extracted, verdict
   recorded, no further resume needed), delete the ephemeral DB:
   ```bash
   rm -f "$WORKER_DB" "$WORKER_DB-wal" "$WORKER_DB-shm"
   ```

Credentials (API keys) are stored in `~/.local/share/opencode/auth.json`, a
separate file outside the database. The worker process reads credentials from
the default data directory regardless of `OPENCODE_DB`, so no credential
symlinking is required.

In addition, the project `opencode.json` (or the orchestrator's effective
config) SHOULD include these settings to minimize per-worker disk growth when
using the opencode harness:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "snapshot": false,
  "compaction": { "auto": true, "prune": true }
}
```

- `snapshot: false` disables the internal git snapshot system that tracks file
  changes for undo/revert — the largest non-DB disk consumer. Workers do not
  need undo capability.
- `compaction.prune: true` removes old tool outputs from context to save tokens
  and reduce the `part` table growth.

### Default worker profile

- **Profile:** DeepSeek Flash Worker
- **Harness:** OpenCode CLI
- **Model:** `opencode-go/deepseek-v4-flash`
- **Endpoint:** the provider already configured in OpenCode
- **Ephemeral DB:** opencode-harness worker spawns use an isolated `OPENCODE_DB`
  file (see "Ephemeral worker storage" above). The DB path is recorded in
  `state.json` alongside the session ID so resume can reuse it. Non-opencode
  harnesses skip this.
- **Fresh launch:** use a shell form that exposes the actual `opencode` PID. With
  Bash, process substitution preserves tee output without making `$!` point at
  `tee`:

  ```bash
  WORKER_DB="<ephemeral-db-path>"
  LOG_PATH="<log-path>"
  OPENCODE_DB="$WORKER_DB" opencode run \
    --model opencode-go/deepseek-v4-flash \
    --auto \
    --title "<task-id>-<role>-<round>" \
    --dir "<project-root>" \
    "<full-self-contained-prompt>" \
    > >(tee "$LOG_PATH") 2>&1 &
  WORKER_PID=$!
  # Record WORKER_PID, launch time, attempt, profile, and paths immediately.
  ```

- **Resume:**

  ```bash
  OPENCODE_DB="<worker-db-path-from-state>" opencode run \
    --model opencode-go/deepseek-v4-flash \
    --auto \
    --session "<session-id>" \
    --dir "<project-root>" \
    "<continuation-prompt>" 2>&1 | tee "<log-path>"
  ```

- **Cleanup after worker lifecycle:**

  ```bash
  rm -f "<worker-db-path>" "<worker-db-path>-wal" "<worker-db-path>-shm"
  ```

- **Liveness:** redirected OpenCode stdout may be block-buffered, so a healthy
  worker can leave its log at zero bytes for minutes. **Do not use log growth or
  report growth as the built-in OpenCode startup-liveness test.** Use accumulated
  CPU time of the actual OpenCode process as the default positive signal:

  ```bash
  # WORKER_PID must be the actual opencode process, not tee or a wrapper shell.
  kill -0 "$WORKER_PID" 2>/dev/null || exit 1
  C1=$(ps -o time= -p "$WORKER_PID" | tr -d ' ')
  sleep 35
  kill -0 "$WORKER_PID" 2>/dev/null || exit 1
  C2=$(ps -o time= -p "$WORKER_PID" | tr -d ' ')

  if [ "$C1" != "$C2" ]; then
    echo "OpenCode worker liveness confirmed"
  else
    # One additional interval avoids declaring a slow startup/network pause dead.
    sleep 35
    kill -0 "$WORKER_PID" 2>/dev/null || exit 1
    C3=$(ps -o time= -p "$WORKER_PID" | tr -d ' ')
    [ "$C2" != "$C3" ] || exit 2
  fi
  ```

  Advancing accumulated CPU time confirms that the worker is doing work even when
  redirected output is buffered. Two consecutive unchanged samples within the
  configured grace mean liveness was not established: safely stop only that
  uniquely identified process and retry under the transport policy. A future
  OpenCode version may provide a stronger explicit worker-status API; use it only
  when verified reliable and configured as an override. A PID or session record
  alone remains insufficient.
- **Roles:** implementer, reviewer, resumed fixer, fresh re-reviewer, and
  phase-finding worker.

Default routing uses this profile for every worker role. The current main
orchestrator performs decomposition, plan-wide decisions, substantive escalation
decisions, and final phase approval. It is not a fallback worker when OpenCode is
unavailable. Default review budget is 5 substantive rounds; default immediate
transport budget is 5 launch attempts per role invocation. Execution is
sequential.
