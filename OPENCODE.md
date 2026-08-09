# DeepSeek and Destroy — OpenCode Adapter

Read this when either the orchestrator or effective worker harness is OpenCode.
It defines DSD worker storage, launch/resume, liveness, provider recovery, and the
OpenCode orchestrator compaction adapter.

## Worker storage: one external database per DSD run

OpenCode writes sessions to SQLite. DSD must not pollute the user's normal
interactive OpenCode database, and an actively-written worker DB must never live
inside the project/worktree: OpenCode project-copy/project-refresh can scan project
files while the worker is writing its DB, creating self-referential I/O failures
that can look like provider/session failures.

> **Use one disposable OpenCode DB per DSD run, stored outside every project and
> worktree path.**

Default sequential execution shares that run DB across implementer/reviewer/fixer
sessions. Resume uses the same DB plus the recorded session ID. Unrelated DSD runs
never share one DB.

### External run DB path

`OPENCODE_DB` must be absolute. A configured `DSD_OPENCODE_STATE_ROOT` wins.
Reasonable defaults:

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

On Windows use a user-local cache/state directory such as `%LOCALAPPDATA%`.
Mandatory invariants:

- absolute path;
- outside repository/project and every active worktree;
- outside project-local `DeepSeekAndDestroy/`;
- persisted in `state.json` for resume;
- unique per unrelated run.

Compare resolved paths, not strings. Invalid project-contained paths are a launch
blocker.

### DB lifecycle

1. Resolve/create run DB once on first OpenCode worker.
2. Fresh worker uses `OPENCODE_DB="$DSD_OC_RUN_DB"`; record its session ID.
3. Resume uses the same DB and exact session ID.
4. Normally keep completed sessions until run end. If one will certainly never be
   resumed, optional `opencode session delete <session-id>` may remove it from the
   run DB.
5. At terminal cleanup, after durable DSD evidence is preserved and no worker can
   resume:

```bash
rm -f "$DSD_OC_RUN_DB" "$DSD_OC_RUN_DB-wal" "$DSD_OC_RUN_DB-shm"
rmdir "$DSD_OC_RUN_DIR" 2>/dev/null || true
```

Do not `VACUUM` or otherwise maintain the user's normal OpenCode DB as DSD cleanup.

### Parallel workers

Default DSD is sequential. If configuration deliberately enables simultaneous
OpenCode workers, use one **external DB per concurrency lane** and persist the lane
association. Sessions resume on their original lane DB.

### Credentials and snapshots

OpenCode auth/config remains in its normal location; no credential symlinks are
required. Disposable workers may disable OpenCode project snapshots when compatible
with the installed version. DSD content-hash scope/preservation evidence remains
authoritative regardless.

## Default worker profile

- Harness: OpenCode CLI
- Model: `opencode-go/deepseek-v4-flash`
- Endpoint: existing OpenCode provider configuration
- Storage: external run DB above
- Default execution: sequential

### Fresh launch

Expose the actual `opencode` PID. With Bash, process substitution keeps `$!` on the
OpenCode process rather than `tee`:

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

# Persist raw digits only. Do NOT write WORKER_PID=12345.
printf '%s\n' "$WORKER_PID" > "<pid-path>"
```

Immediately persist attempt number, raw PID, launch time, model/profile, session
when known, report/log paths, and run DB path in state.

### PID integrity and duplicate-launch prevention

PID files contain **only decimal digits**. Before using a recovered PID, validate
it rather than passing arbitrary file contents to `kill`:

```bash
PID_RAW=$(tr -d '[:space:]' < "<pid-path>" 2>/dev/null || true)
case "$PID_RAW" in
  ''|*[!0-9]*) echo "invalid PID record" >&2; exit 2 ;;
esac
WORKER_PID="$PID_RAW"
```

Do not treat an invalid/labeled PID record as proof the worker is dead. If process
identity is uncertain, reconcile process/session identity plus CPU and durable
log/report/checkpoint activity before relaunch.

> **Never launch a second worker for the same task/role while the first may still
> be alive.** A duplicate launch is an orchestration incident: reconcile the
> original process, state, and suspect changes before any retry.

Do not use `pgrep -f "<task-title>"`; a watcher may match itself. Prefer the exact
saved PID. If recovering without one, conservatively match a real `opencode run`
command and reject ambiguous results.

### Resume

```bash
OPENCODE_DB="<absolute-external-run-db-from-state>" opencode run \
  --model opencode-go/deepseek-v4-flash \
  --auto \
  --session "<session-id>" \
  --dir "<project-root>" \
  "<continuation-prompt>" 2>&1 | tee "<log-path>"
```

If a configured resume immediately reports missing session/process or equivalent
transient launch failure, retry the exact resume once after a short delay with the
same DB/session. If it fails again, use the configured fresh-fixer fallback rather
than burning the full transport budget.

## Liveness and completion

Redirected stdout may be block-buffered, so log-byte growth alone is invalid.
Use multiple signals:

- exact process existence;
- accumulated CPU delta;
- log/report/checkpoint growth;
- expected changed-path activity when relevant;
- elapsed time.

Example sampler:

```bash
sample_worker() {
  kill -0 "$WORKER_PID" 2>/dev/null || return 3
  CPU=$(ps -o time= -p "$WORKER_PID" | tr -d ' ')
  OUT=$(wc -c < "$LOG_PATH" 2>/dev/null || printf 0)
  NOW=$(date +%s)
  printf '%s %s %s\n' "$NOW" "$CPU" "$OUT"
}
```

Interpret conservatively:

- dead: process absent;
- alive/slow: meaningful CPU or durable output/checkpoint progress;
- probable wedge: substantial elapsed time plus repeated negligible CPU and
  durable progress;
- unknown: collect another window.

A report appearing is not completion. Wait for process exit or reliable harness
completion before final scope hashes, missing-artifact claims, or verdict capture.

Near a soft cap, prefer graceful completion. Use `SIGINT`, wait, then `SIGTERM` if
needed; reserve `SIGKILL` for a runaway process. Forced/reportless exits enter the
suspect-tree recovery protocol.

## Provider health probe and recovery

After repeated banner-only/empty/provider-style failures, verify the exact model ID
from `opencode models` and run the smallest `HEALTHCHECK OK` probe.

The probe DB must also be outside the project tree and should normally be a fresh
temporary external DB separate from the run DB. This separates provider health
from a corrupted/locked run DB. `scripts/opencode_probe.py` enforces the path rule.

Do not infer credit/billing exhaustion solely from error text. Probe configured
equivalent fallbacks. Transient incidents enter `WAITING-FOR-WORKER` with persisted
backoff, next probe, and relaunch action.

## Worker protocol injection

OpenCode workers receive the canonical role envelope from `PROMPTS.md`, compact
Worker Core from `worker/SKILL.md`, the appropriate Build/Review protocol, and only
task-relevant proof-pattern recipes. They do not need access to the skill folder at
runtime when those sections have been assembled into the prompt.

## Main-orchestrator context checkpoints

This section applies when the **main orchestrator** itself runs in OpenCode and is
separate from worker run-DB storage.

Use `COMPACTION.md` and the project-local OpenCode compaction adapter:

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --harness opencode \
  --project-root <project-root>
```

The adapter creates the external DSD checkpoint before native compaction. Native
summary is advisory. If `state.json.context_checkpoint.status` is `prepared`,
`compacting`, or `rehydration-required`, reload skill/run identity and execute
`verify-resume` before project work.

Default checkpoint threshold is 65%; compact at the next safe boundary before the
configured ceiling. When exact percentage is unavailable, use plugin/native hooks
plus periodic safe-boundary checkpoints from `COMPACTION.md`.

Official references:

- https://opencode.ai/v2/docs/compaction
- https://opencode.ai/docs/plugins/
- https://opencode.ai/docs/cli/#session
