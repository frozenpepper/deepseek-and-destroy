# DeepSeek and Destroy — OpenCode Adapter

Read this file when either the main orchestrator or an effective worker profile
uses OpenCode. It defines the built-in DeepSeek Flash worker profile, isolated
ephemeral worker databases, liveness/provider handling, and the OpenCode V2
orchestrator compaction adapter.

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
config) SHOULD disable snapshots for disposable workers:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "snapshot": false,
  "compaction": {
    "auto": true,
    "keep": { "tokens": 8000 },
    "buffer": 20000
  }
}
```

- `snapshot: false` disables the internal git snapshot system used for undo and
  revert. Disposable workers do not need it.
- In OpenCode V2, `compaction.keep.tokens` controls the retained recent tail and
  `compaction.buffer` controls how early automatic compaction is considered.
- Do not rely on `compaction.prune` for V2 disk or context reduction: the current
  V2 documentation states that it is accepted by the schema but has no runtime
  pruning effect.

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

- **Liveness and completion:** redirected OpenCode stdout may be block-buffered,
  so output bytes alone are unreliable. Classify the worker using three signals:
  process existence, accumulated CPU time, and output/report growth, together with
  elapsed time.

  Always prefer the exact PID captured at launch. Do not use
  `pgrep -f "<task-title>"`: a watcher whose own command line contains the title can
  match itself and report a dead worker as alive. When recovering without a saved
  PID, match the actual command conservatively, for example
  `ps -ax -o pid=,command= | grep "[o]pencode run" | grep -- "<exact-title>"` and
  reject ambiguous matches.

  ```bash
  # WORKER_PID is the actual opencode process captured at launch.
  sample_worker() {
    kill -0 "$WORKER_PID" 2>/dev/null || return 3
    CPU=$(ps -o time= -p "$WORKER_PID" | tr -d ' ')
    OUT=$(wc -c < "$LOG_PATH" 2>/dev/null || printf 0)
    NOW=$(date +%s)
    printf '%s %s %s\n' "$NOW" "$CPU" "$OUT"
  }

  read -r T1 C1 O1 < <(sample_worker)
  sleep 35
  read -r T2 C2 O2 < <(sample_worker)

  # Process absent => dead. CPU or output advancing => alive/slow; continue.
  # Process present with negligible CPU and no output over repeated windows after
  # the grace period => probable wedge; use the safe-stop/retry policy.
  ```

  Interpret the signals:

  - **dead:** process absent;
  - **alive/slow:** CPU accumulates materially or output/report/checkpoint grows;
  - **probable wedge:** substantial elapsed time, process still present, and both
    CPU progress and durable output remain negligible across repeated windows;
  - **unknown:** collect another window rather than guessing.

  Startup liveness and continued progress are different. CPU movement can prove a
  process started, but a tiny CPU crawl with no log, report, checkpoint, or changed
  path for a prolonged configurable window may still be a hung-but-alive worker.
  After startup, monitor rolling progress using all available signals: process
  existence, CPU delta, log/report/checkpoint growth, and expected changed-path
  activity. Default to another observation window when uncertain; classify a
  probable wedge only after repeated negligible progress, then use graceful stop,
  suspect-tree recovery, and task re-scope rather than waiting indefinitely.
  Do not use static log growth alone because redirected output may be buffered.

  A report file appearing is not completion. Wait for process exit or a reliable
  harness completion event before declaring logs/major entries absent or capturing
  final scope hashes.

- **Graceful cap behavior:** workers are prompted to draft reports early. A time or
  context cap is a degradation point, not permission to `kill -KILL` and discard
  evidence. Near the configured soft cap, use the harness's graceful completion
  method when available. For the built-in CLI, prefer `SIGINT`, wait for exit, then
  `SIGTERM` only if necessary; reserve `SIGKILL` for a runaway process that cannot
  be stopped safely. After any forced or reportless exit, apply the suspect-tree
  protocol in `WORKSPACE.md`.

- **Resume retry:** when a configured `--session` launch immediately reports
  `process absent`, missing session, or an equivalent transient launch failure,
  retry the exact resume once after a short delay with the same absolute
  `OPENCODE_DB` and session id. If the second attempt fails, treat continuation as
  unavailable and use the configured fresh-fixer fallback. Do not spend the full
  transport budget repeatedly probing a session that cannot be resolved.

- **Provider health probe and recovery:** before spending repeated task attempts on
  similar banner-only, empty, or provider errors, verify the exact model identifier
  from `opencode models` and run a trivial isolated probe asking for exactly
  `HEALTHCHECK OK`. Use a fresh ephemeral DB. Do not infer billing or exhausted
  credit solely from an error string. Probe the configured fallback profile too;
  reroute automatically when it is equivalent and healthy. For a transient outage,
  persist `waiting-for-worker`, `next_probe_at`, and the relaunch action, then
  re-probe on schedule instead of waiting for a human continuation message. The
  included `scripts/opencode_probe.py` implements the isolated exact-model probe;
  orchestration policy still decides backoff, fallback, and relaunch.

- **Roles:** discovery worker, implementer, verification-only worker, reviewer,
  resumed fixer, fresh re-reviewer, and phase-finding worker.

Default routing uses this profile for every worker role. The current main
orchestrator performs decomposition, plan-wide decisions, substantive escalation
decisions, and final phase approval. It is not a fallback worker when OpenCode is
unavailable. Default review budget is 5 substantive rounds; default immediate
transport budget is 5 launch attempts per role invocation. Execution is
sequential.


## Main-orchestrator context checkpoints in OpenCode V2

This section applies when the **main orchestrator** itself runs in OpenCode. It is
separate from the ephemeral worker-database rules above.

OpenCode V2 provides automatic/manual compaction and an
`experimental.session.compacting` plugin hook. It does not currently document a
post-compaction hook equivalent to Codex or Claude Code `SessionStart compact`.
Therefore the best protocol is:

1. keep `HANDOVER.md` incrementally current;
2. install the project-local pre-compaction plugin;
3. create the external checkpoint before OpenCode generates its summary;
4. inject exact checkpoint/run paths into the compaction prompt;
5. rely on the live skill plus `state.json.context_checkpoint` to force
   rehydration before further project work.

Install the adapter:

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --harness opencode \
  --project-root <project-root>
```

This copies:

- `.opencode/plugins/dsd-compaction.ts`;
- `DeepSeekAndDestroy/tools/context_checkpoint.py`.

Restart or reload OpenCode so the project-local plugin is active.

When exact context usage is visible, prepare at the configured threshold
(default 65%) and request `/compact` at the next safe boundary. OpenCode also
supports a session-compaction API. When exact usage is unavailable, rely on the
plugin plus the periodic safe-boundary checkpoints in `COMPACTION.md`.

OpenCode's generated checkpoint is lossy and is presented as historical context,
not as fresh instructions. The external DSD checkpoint remains authoritative.
After compaction, if `state.json.context_checkpoint.status` is `prepared`,
`compacting`, or `rehydration-required`, the orchestrator's first action is to
reload the skill/run files and execute `verify-resume`. It must not continue
project work from the native summary alone.

Official references:

- https://opencode.ai/v2/docs/compaction
- https://opencode.ai/docs/plugins/
