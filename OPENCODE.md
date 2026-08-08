# DeepSeek and Destroy — OpenCode Adapter

Read this file when either the main orchestrator or an effective worker profile
uses OpenCode. It defines the built-in DeepSeek Flash worker profile, disposable
run-level worker storage, liveness/provider handling, and the OpenCode V2
orchestrator compaction adapter.

## Worker storage: one external database per DSD run

This section applies **only when the effective worker harness is OpenCode CLI**.
Other harnesses have their own session/storage models.

OpenCode writes sessions to SQLite. DSD can create many worker sessions, so using
the user's normal OpenCode database would pollute interactive history and can make
that database very large. Earlier DSD revisions solved this with one disposable DB
per worker under `<run-root>/ephemeral-db/`. Field experience exposed two problems
with that design:

1. OpenCode project-copy/project-refresh logic may scan the project tree. An
   actively-written `OPENCODE_DB` located anywhere beneath the project/worktree can
   therefore be scanned by the same worker that is writing it, producing
   self-referential I/O failures or apparent provider/session failures.
2. One DB per worker is unnecessary overhead when the normal DSD execution model
   is sequential and OpenCode sessions already have stable session IDs.

The built-in policy is now:

> **Use one disposable OpenCode worker database per DSD run, stored outside every
> project/worktree path. Never put an OpenCode worker DB under
> `DeepSeekAndDestroy/`, the repository root, a Git worktree, or another directory
> OpenCode may treat as project input.**

The database isolates DSD from the user's normal OpenCode history while allowing
all worker sessions for one run to share one storage file. Reviewer → fixer resume
uses the same run DB plus the recorded session ID. Fresh reviewers create new
sessions in the same run DB.

### Choosing the external run DB path

`OPENCODE_DB` must be an absolute path. Choose an OS cache/state location outside
the project tree. A user/configured `DSD_OPENCODE_STATE_ROOT` wins. Reasonable
shell defaults are:

```bash
if [ -n "${DSD_OPENCODE_STATE_ROOT:-}" ]; then
  DSD_OC_ROOT="$DSD_OPENCODE_STATE_ROOT"
elif [ "$(uname -s)" = "Darwin" ]; then
  DSD_OC_ROOT="$HOME/Library/Caches/DeepSeekAndDestroy/opencode"
else
  DSD_OC_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/deepseek-and-destroy/opencode"
fi

DSD_OC_RUN_DIR="$DSD_OC_ROOT/<run-id>"
mkdir -p "$DSD_OC_RUN_DIR"
DSD_OC_RUN_DB="$DSD_OC_RUN_DIR/workers.db"
```

On Windows, use a user-local cache/state directory such as `%LOCALAPPDATA%`, not
the repository. Harness-specific wrappers may choose another location, but the
following invariants are mandatory:

- path is absolute;
- path is outside the project root and every active worktree;
- path is outside the visible `DeepSeekAndDestroy/` run tree when that tree lives
  under the project;
- the path is persisted in `state.json` so a later orchestrator can resume worker
  sessions;
- unrelated DSD runs do not share the same DB.

Before first use, compare resolved paths rather than strings. If the DB resolves
inside the project/worktree, treat configuration as invalid and choose a safe
external location before launching a worker.

### Run DB lifecycle

1. **Create/resolve the run DB once** when an OpenCode-backed run first needs a
   worker. Persist its absolute path as the run's OpenCode worker DB.
2. **Fresh worker:** launch with `OPENCODE_DB="$DSD_OC_RUN_DB"` and record the
   resulting session ID, role, task, round, PID, and report/log paths.
3. **Resume:** use the same `OPENCODE_DB` and the exact recorded `--session` ID.
4. **Completed session:** normally keep it until the run ends. If disk pressure or
   history size makes early cleanup useful and the session will definitely never
   be resumed, `OPENCODE_DB="$DSD_OC_RUN_DB" opencode session delete <session-id>`
   may remove that one session and its data.
5. **Run completion/abandon cleanup:** once no worker can resume and durable DSD
   reports/evidence have been preserved, delete the disposable run DB and SQLite
   sidecars, then remove the empty run-storage directory:

   ```bash
   rm -f "$DSD_OC_RUN_DB" "$DSD_OC_RUN_DB-wal" "$DSD_OC_RUN_DB-shm"
   rmdir "$DSD_OC_RUN_DIR" 2>/dev/null || true
   ```

Do not delete the DB on ordinary task completion: later reviewer/fixer resumes may
still need sessions in it. Do not `VACUUM` the user's normal OpenCode DB as part of
DSD cleanup. DSD's default worker sessions never need to enter that DB.

### Parallel OpenCode workers

Default DSD execution is sequential, so one run DB is the simplest model. If a
configuration deliberately enables simultaneous OpenCode workers, do not assume a
single SQLite writer is the right concurrency primitive. Use one **external DB per
concurrency lane** (for example `lane-1.db`, `lane-2.db`) and persist each lane's
DB path. Sessions that may resume must stay on their original lane DB. Lane DBs
are still outside the project tree and are cleaned at run completion.

### Credentials and worker snapshots

Credentials remain in OpenCode's normal auth/config locations and are separate
from `OPENCODE_DB`; no credential symlinking is required.

For disposable workers, the effective OpenCode configuration SHOULD disable
OpenCode's internal project snapshots when compatible with the installed version:

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

DSD's own scope/preservation hashes remain authoritative regardless of OpenCode's
snapshot setting.

## Default worker profile

- **Profile:** DeepSeek Flash Worker
- **Harness:** OpenCode CLI
- **Model:** `opencode-go/deepseek-v4-flash`
- **Endpoint:** the provider already configured in OpenCode
- **Worker storage:** the run-level external `OPENCODE_DB` described above
- **Fresh launch:** expose the actual `opencode` PID. With Bash, process
  substitution preserves tee output without making `$!` point at `tee`:

  ```bash
  DSD_OC_RUN_DB="<absolute-external-run-db-from-state>"
  LOG_PATH="<log-path>"
  OPENCODE_DB="$DSD_OC_RUN_DB" opencode run \
    --model opencode-go/deepseek-v4-flash \
    --auto \
    --title "<task-id>-<role>-<round>" \
    --dir "<project-root>" \
    "<full-self-contained-prompt>" \
    > >(tee "$LOG_PATH") 2>&1 &
  WORKER_PID=$!
  ```

- **Resume:**

  ```bash
  OPENCODE_DB="<absolute-external-run-db-from-state>" opencode run \
    --model opencode-go/deepseek-v4-flash \
    --auto \
    --session "<session-id>" \
    --dir "<project-root>" \
    "<continuation-prompt>" 2>&1 | tee "<log-path>"
  ```

- **Session cleanup:** optional during the run and only when no resume will be
  needed. Prefer deleting the whole disposable run DB at terminal cleanup.

### Liveness and completion

Redirected OpenCode stdout may be block-buffered, so output bytes alone are
unreliable. Classify workers using process existence, accumulated CPU time,
output/report/checkpoint growth, expected changed-path activity, and elapsed time.

Always prefer the exact PID captured at launch. Do not use
`pgrep -f "<task-title>"`; the watcher itself can match that string. If recovering
without a saved PID, conservatively match the real `opencode run` command and
reject ambiguous matches.

```bash
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
```

Interpret the signals:

- **dead:** process absent;
- **alive/slow:** CPU accumulates materially or durable output/checkpoints move;
- **probable wedge:** substantial elapsed time, process still present, and both CPU
  progress and durable output remain negligible across repeated windows;
- **unknown:** collect another observation window.

A report file appearing is not completion. Wait for process exit or a reliable
harness completion event before asserting final scope, missing artifacts, or
verdict completeness.

### Graceful cap behavior

Workers draft reports early. Near a soft cap, prefer a graceful completion signal.
For the built-in CLI, use `SIGINT`, wait for exit, then `SIGTERM` only when needed;
reserve `SIGKILL` for a runaway process. Any forced/reportless exit invokes the
suspect-tree recovery protocol in `WORKSPACE.md`.

### Resume retry

If `--session` immediately reports process/session absence or an equivalent
transient launch failure, retry that exact resume once after a short delay using
the same run DB and session ID. If the second attempt fails, use the configured
fresh-fixer fallback. Do not spend the full transport budget probing an
unrecoverable child session.

### Provider health probe and recovery

Before repeating expensive task launches after banner-only/empty/provider errors,
verify the exact model ID from `opencode models` and run a trivial
`HEALTHCHECK OK` probe.

**The probe DB must also be outside the project tree.** Prefer a fresh temporary
external DB separate from the run DB; this distinguishes provider health from a
corrupted/locked run DB. `scripts/opencode_probe.py` rejects explicitly supplied
probe DB paths that resolve inside the project root.

Do not infer exhausted credit solely from an error string. Probe configured
fallback profiles when appropriate; transient incidents enter
`WAITING-FOR-WORKER` with persisted backoff/relaunch state.

### Roles and routing

Default routing uses this profile for phase survey, discovery, implementation,
verification, review, fixing, re-review, recovery audit, and phase audit. The main
orchestrator owns decomposition, plan-wide decisions, escalation decisions, and
phase approval; it is never an implicit worker fallback.

## Main-orchestrator context checkpoints in OpenCode V2

This section applies when the **main orchestrator** itself runs in OpenCode. It is
separate from worker run-DB storage.

OpenCode V2 provides automatic/manual compaction and an
`experimental.session.compacting` plugin hook. The DSD protocol remains:

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

This copies `.opencode/plugins/dsd-compaction.ts` and
`DeepSeekAndDestroy/tools/context_checkpoint.py`. Restart/reload OpenCode so the
project-local plugin is active.

When exact context usage is visible, prepare at the configured threshold (default
65%) and request compaction at the next safe boundary. When exact usage is
unavailable, rely on the plugin plus the periodic safe-boundary checkpoints in
`COMPACTION.md`.

OpenCode's generated checkpoint is lossy and advisory. If
`state.json.context_checkpoint.status` is `prepared`, `compacting`, or
`rehydration-required`, the first post-compaction action is to reload the skill and
run files and execute `verify-resume`. Do not continue project work from the native
summary alone.

Official references:

- https://opencode.ai/v2/docs/compaction
- https://opencode.ai/docs/plugins/
- https://opencode.ai/docs/cli/#session
