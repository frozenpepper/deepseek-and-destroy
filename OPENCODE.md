# DeepSeek and Destroy — OpenCode CLI Worker Adapter

This is the **default DSD worker transport** regardless of whether the premium
orchestrator runs in Claude Code, Codex, OpenCode, Kilo Code, or another harness.

Default worker:

- harness: OpenCode CLI;
- model: `opencode-go/deepseek-v4-flash`;
- fresh external process per worker attempt;
- one disposable external OpenCode DB per DSD run (one per concurrency lane only if
  deliberate parallel OpenCode workers are enabled).

## Why the worker DB is external and run-scoped

Do not use the user's normal OpenCode database: DSD can create many sessions and
should not pollute interactive history.

Do not put a worker DB anywhere inside the repository/project/worktree. Field
experience showed OpenCode project-copy/refresh can scan the project tree and hit
its own actively-written SQLite file, producing self-referential I/O failures.

Use one disposable run DB outside every project/worktree, for example:

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

Persist the resolved absolute path in `state.json`. All attempts in the run may share
the same external DB, but **normal role changes always start fresh worker sessions**.
Session continuation is reserved for trustworthy same-role transport/recovery cases.

If deliberate simultaneous OpenCode workers are enabled, use one external DB per
concurrency lane and keep resumed sessions on their original lane.

At terminal run cleanup, after all durable DSD evidence is preserved and no session
can resume:

```bash
rm -f "$DSD_OC_RUN_DB" "$DSD_OC_RUN_DB-wal" "$DSD_OC_RUN_DB-shm"
rmdir "$DSD_OC_RUN_DIR" 2>/dev/null || true
```

Do not delete the run DB after every task; later same-role continuation/recovery may need it.

## Path-only worker launch

The orchestrator does not hand-write the OpenCode command or a multi-kilobyte
prompt.

1. `prepare_worker_rules.py` creates an immutable run worker-rules revision such as
   `worker-rules/r0001/WORKER_RULES.md` plus `MANIFEST.json` and that revision's `protocol/` snapshot.
2. `contracts/rNNNN.md` is the immutable current task contract containing
   unit/objective/risks/acceptance/proof/deliverable, exact role-input references,
   and `Allowed source changes` for mutating roles.
3. capture the full Git-worktree attempt baseline excluding only
   `DeepSeekAndDestroy/`; this is later used by the evidence gate.
4. `render_worker_prompt.py` writes the small `launch-prompt.txt` against one exact
   worker-rules revision and task-contract revision.
5. `run_worker.py` owns OpenCode process construction, DB env, title, cwd, log,
   process identity, atomic attempt reservation, optional same-role continuation, report
   skeleton, and terminal event.

Example foreground wrapper:

```bash
python3 <skill-root>/scripts/run_worker.py \
  --project-root <project-root> \
  --run-root <run-root> \
  --task-id U4 --role reviewer --attempt 1 \
  --prompt-file <task-root>/attempts/reviewer-1/launch-prompt.txt \
  --task-contract <task-root>/contracts/rNNNN.md \
  --worker-rules <run-root>/worker-rules/rNNNN/WORKER_RULES.md \
  --scope-baseline <task-root>/attempts/reviewer-1/scope-baseline.json \
  --report <task-root>/review-1.md \
  --event-dir <task-root>/attempts/reviewer-1 \
  --log <task-root>/attempts/reviewer-1/worker.log \
  --db "$DSD_OC_RUN_DB" \
  --model opencode-go/deepseek-v4-flash
```

The wrapper uses OpenCode's project `--dir`, deterministic title, the configured
permission flag, and `OPENCODE_DB`. Before spawn it atomically creates `launch-reservation.json`, binding the exact
launch-prompt, task-contract, worker-rules revision/manifest, and scope-baseline paths/hashes;
reusing the same attempt/report/log is rejected. `launch-reservation.json` is the single immutable authority for that attempt.
`attempt.json` and `terminal.json` are lifecycle records bound back to the exact
reservation path/hash, so the evidence gate can reject post-launch authority or
baseline tampering without maintaining duplicate copies of every binding. The
wrapper writes `attempt.json` after the child exists and `terminal.json` when that
exact child exits. Historical v14 terminal records remain readable.

OpenCode supports `opencode session list --format json`; after exit the wrapper
best-effort resolves the deterministic title to a session id for possible same-role
continuation/recovery. A missing or ambiguous session id does not corrupt task
evidence; the normal next role starts fresh regardless.

## Completion / waiting

**Process exit is DSD's durable terminal event.** Under Worker Rules this is the
no-more-task-writes boundary: workers must not leave background/daemon/watcher
processes capable of mutating project source, generated deliverables, or terminal
evidence after the worker process reaches terminal completion. Discovery of such a writer invalidates the assumption and enters recovery.

How the premium orchestrator waits for that external process is harness-specific:

- Claude: detached wrapper + `asyncRewake` terminal-event hook; see `CLAUDE.md`;
- Codex: foreground wrapper when safe, otherwise detached wrapper + long blocking
  `wait_worker.py`; see `CODEX.md`;
- OpenCode/other orchestrator: foreground when safe or detached + long blocking
  `wait_worker.py`.

Detached example:

```bash
python3 <skill-root>/scripts/run_worker.py ... --detach
python3 <skill-root>/scripts/wait_worker.py --event-dir <attempt-dir>
```

A wait timeout is not evidence of a hung worker. It is a non-event; wait again.
When `terminal.json` appears, classify it before touching the report: successful
completion enters the evidence gate; a non-zero process exit enters suspect-change
recovery; a pre-start transport error enters availability handling.

### Why not poll CPU/logs normally?

Redirected worker output can be buffered and CPU can legitimately be quiet. More
importantly, every parent-side polling cycle spends premium orchestration attention
for almost no value. `wait_worker.py` blocks cheaply inside one helper process.

PID/CPU/log-growth inspection remains available only when a terminal/wait/tool
signal is inconsistent and recovery needs to determine whether the process is
still alive.

### OpenCode session events

Current OpenCode plugins expose `session.idle`, `session.error`, `session.status`,
and related events; the official notification example treats `session.idle` as
session completion:

https://opencode.ai/docs/plugins/

DSD deliberately does **not** require another worker-event plugin in the normal
path. The wrapper's actual process exit is simpler, portable across orchestrator
harnesses, and stronger as a no-more-writes boundary. Reconsider only if empirical
work shows a material benefit.

## Report skeleton / wrong path protection

Before launch, the wrapper creates the expected report only if absent and marks it:

`DSD_REPORT_STATUS: SKELETON`

Workers should replace the skeleton with substantive evidence and preferably mark
`DSD_REPORT_STATUS: FINAL` at truthful completion. The process terminal event, not
the magic word, is the durable no-more-writes boundary. A substantive report that
merely omitted canonical finality is a clerical normalization case.

If the canonical report is still the exact untouched launcher skeleton, however,
the Evidence Clerk must actually recover one unambiguous complete same-attempt
report from the exact log/declared output locations and canonicalize it
byte-for-byte. A Clerk cannot waive an absent report by assertion; ambiguity stays
MALFORMED.

## Same-role continuation

A **role change always starts a fresh worker session**. Reviewer → Fixer, Fixer →
Reviewer, Discovery → Implementer, and similar transitions carry context through
durable reports/evidence, not inherited chat state. This keeps each role skill's
reasoning prior clean and removes fuzzy "moderate versus heavy context" routing.

`run_worker.py --resume-session <id>` remains available only for trustworthy
same-role transport/session continuation or recovery. It preserves all other
transport invariants. If continuation cannot be established safely, start a fresh
same-role attempt instead.

## Provider health / recovery

Before burning repeated task attempts after banner-only/empty/auth/provider errors:

1. verify exact model id from `opencode models`;
2. run `scripts/opencode_probe.py` with a fresh external temporary DB, not the run
   DB;
3. classify provider availability separately from task failure;
4. persist backoff/relaunch/fallback state.

Do not infer exhausted billing from an error string alone.

## Credentials / snapshots

Credentials stay in OpenCode's normal auth/config location and are separate from
`OPENCODE_DB`.

For disposable DSD workers, disable OpenCode internal project snapshots when the
installed version supports it and project policy allows; DSD's content-hash scope
facts remain authoritative. Never put a worker DB inside the project to gain
persistence.

## OpenCode as the premium orchestrator

When the premium orchestrator itself is OpenCode, the worker is still a separate
OpenCode process/run DB. Use the same wrapper + long blocking wait semantics.

For orchestrator context compaction, install the existing project-local DSD
pre-compaction plugin with `install_harness_adapter.py --harness opencode` and
follow `COMPACTION.md`. The orchestrator compaction plugin and worker transport are
separate concerns.

Official references:

- CLI: https://opencode.ai/docs/cli/
- plugins/events: https://opencode.ai/docs/plugins/
