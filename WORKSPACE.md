# DeepSeek and Destroy Workspace Contract

This file contains the detailed durable-state, plan-history, concurrency, and
engineering-log contract used by `SKILL.md`.

## Workspace layout

Use a visible project-root directory named `DeepSeekAndDestroy/`. It groups
history by plan and isolates every orchestrator execution in its own run. The
plan folder is for discovery and grouping; the **run directory is the only
mutable source of truth for that execution's durable orchestration artifacts**.

```
DeepSeekAndDestroy/
  plans/
    <plan-id>/
      runs/
        <run-id>/
          run-manifest.md                 # owner, worktree, status, resume identity
          plan/
            plan-reference.md             # authoritative path, snapshot, hashes/history
            snapshots/
              0001-intake-<original-name> # immutable copy at intake
              0002-<timestamp>-<name>      # later plan revision, never overwrite
          state.json                       # durable execution state for this run only
          authority-index.json             # governing paths, hashes, compact summaries
          HANDOVER.md                       # incrementally maintained compact continuity packet
          compactions/
            LATEST                         # latest immutable checkpoint sequence
            0001/
              CHECKPOINT.md
              resume-manifest.json
              state.snapshot.json
              HANDOVER.snapshot.md
              plan-reference.snapshot.md
              authority-index.snapshot.json
              native-compact-summary.md    # when exposed by the harness
          effective-configuration.md       # resolved configuration; no secrets
          major-findings-and-fixes.md      # append-only engineering rationale log
          out-of-scope-defects.md          # unrelated defects discovered during work
          phases/
            <phase-id>/
              current-state-audit.md       # Phase Surveyor output
              phase-audit.md               # latest Phase Auditor synthesis for hard gate
              phase-audits/                # preserved prior phase-audit rounds
              phase-remediation-1.md       # immutable orchestrator remediation plan
              phase-remediation-2.md       # additional gate cycles when needed
              verification/                # phase-level Verification Worker reports
              <task-id>/
                task.md
                discovery-spec.md          # discovery tasks only
                scope-baseline.json
                scope-diff.json
                preservation-baseline.md
                recovery-audit.md          # reportless-worker audit when needed
                implementer.log
                implementer-report.md
                verification-report.md     # verification-only tasks when used
                review-1.md   fix-1.md
                review-2.md   fix-2.md
                ... review-5.md
                reviewer-session-<n>.id
                run-<role>-<attempt>.log
                verdict.json
```

**Harness runtime state is not automatically a project artifact.** In particular,
OpenCode worker SQLite files MUST live outside the repository/project/worktree.
The external absolute path is recorded in `state.json`; see `OPENCODE.md`. Do not
create `<run-root>/ephemeral-db/` or otherwise place an active `OPENCODE_DB` under
the project tree. Field experience showed that OpenCode project-copy refresh can
scan such files while they are being written and create self-referential I/O
failures.

### Plan and run identity

- **Plan id:** use a readable slug plus a short unique suffix. Before creating a
  plan folder, inspect existing `plan-reference.md` files for an exact match to
  the same canonical project-relative source path. Reuse a plan grouping only
  when the match is unambiguous; otherwise create a new plan id. Duplicate plan
  groups are safer than merging unrelated histories.
- **Run id:** every new orchestrator execution gets a collision-resistant id,
  such as `<UTC timestamp>-<orchestrator-label>-<short-random-suffix>`. A new
  orchestrator must create a new run unless it was explicitly told to resume or
  take over an existing run.
- **Run ownership:** `run-manifest.md` records the run id, plan id, orchestrator
  identity/label, harness, creation time, status (`active`, `human-blocked`,
  `paused-by-user`, `completed`, or `abandoned`), project root, worktree, branch
  when applicable, and any parent or handoff run. Do not edit another active run's
  files.
- **Source-code concurrency:** isolated run folders prevent orchestration-artifact
  collisions, not code collisions. Concurrent orchestrators that may touch the
  same files must use separate VCS worktrees/branches or explicitly disjoint
  scopes. Never let two active runs modify overlapping files in the same working
  tree without deliberate coordination.
- **No shared mutable registry is required for correctness.** Discover runs by
  scanning their manifests. A plan-level index may be generated for convenience,
  but it must not be the sole resume authority or a concurrency bottleneck.

### Plan reference and snapshots

Each run owns `plan/plan-reference.md`. Record, clearly and human-readably:

- plan id and run id;
- authoritative plan path (project-relative whenever possible);
- original external/attachment path or source description when applicable;
- immutable snapshot path inside this run;
- SHA-256 or equivalent content hash at intake;
- intake timestamp and the orchestrator that captured it;
- whether execution currently follows the live source or the stored snapshot;
- every later plan revision, with old/new hashes, reason, timestamp, and a new
  immutable snapshot path.

Never overwrite a plan snapshot. On resume—and immediately whenever a plan change
is noticed mid-run—compare the current source with the recorded hash. Before any
new worker launch, record the old/new hashes, capture a new immutable snapshot,
and classify the effect on current scope, criteria, dependencies, and accepted
work. If the original source is unavailable, the stored snapshot preserves the
exact plan used, but the run must state that it is continuing from the snapshot
rather than pretending the live source was checked.

### Concurrent-orchestrator protocol

1. At startup, discover existing plan/run manifests before creating files.
2. Resume a run only when its exact run path/id is supplied or one candidate is
   unambiguously identified by a handoff. If multiple active candidates exist,
   do not guess or merge their state.
3. Before taking over a paused/interrupted run, record the handoff in
   `run-manifest.md` and confirm the prior worker processes can no longer write.
4. Never write state, logs, reports, or task artifacts into another run merely
   because it targets the same plan. Harness runtime resources such as an OpenCode
   run DB are also unique to that run and must not be shared across unrelated runs.
5. Before concurrent source edits, compare declared task scopes and worktrees. If
   overlap is possible, isolate with worktrees/branches or coordinate sequencing.
6. When one run depends on another, reference its run id and immutable artifacts;
   do not copy its mutable `state.json` into the current run.

Keep the workspace proportional. Preserve durable manifests, plan snapshots,
major rationale, reports, and evidence needed for recovery. Raw logs may be
trimmed or excluded according to project policy. Do not blanket-ignore the whole
`DeepSeekAndDestroy/` tree when its durable history is intended to be tracked.
OpenCode worker databases are external runtime state and must not be stored here.

Task directories use a stable, collision-resistant task uid recorded in state,
for example `<phase-id>-<seq>-<short-slug>-<4hex>`. Never derive a sibling task
path by appending one character to another task id. All prompts use the exact
stored path rather than reconstructing it from memory.

### state.json

```json
{
  "workspace_root": "DeepSeekAndDestroy",
  "plan_id": "example-plan--7f3a2c",
  "run_id": "20260803T162700Z-opus-a91f",
  "run_root": "DeepSeekAndDestroy/plans/example-plan--7f3a2c/runs/20260803T162700Z-opus-a91f",
  "run_manifest": "<run-root>/run-manifest.md",
  "plan_reference": "<run-root>/plan/plan-reference.md",
  "authoritative_plan_path": "DOCS/Plans/example.md",
  "plan_snapshot": "<run-root>/plan/snapshots/0001-intake-example.md",
  "plan_source_sha256": "<sha256>",
  "orchestrator_id": "claude-opus-main",
  "orchestrator": {
    "harness": "claude-code",
    "session_id": "abc123",
    "adapter": "CLAUDE.md",
    "checkpoint_mode": "hooked-native"
  },
  "project_worktree": "/abs/path/to/project-worktree",
  "authority_index": "<run-root>/authority-index.json",
  "handover": "<run-root>/HANDOVER.md",
  "effective_config": "<run-root>/effective-configuration.md",
  "major_log": "<run-root>/major-findings-and-fixes.md",
  "execution_status": "active",
  "terminal_condition": null,
  "next_action": "resume phase-1-task-1 reviewer round 1 as fixer",
  "decision_sources": ["DOCS/Plans/example.md", "AGENTS.md", "DOCS/Architecture.md"],
  "worker_availability": {
    "status": "available",
    "last_incident": null,
    "next_probe_at": null
  },
  "worker_runtime": {
    "opencode": {
      "storage_scope": "run",
      "run_db": "/Users/example/Library/Caches/DeepSeekAndDestroy/opencode/20260803T162700Z-opus-a91f/workers.db",
      "external_to_project": true,
      "cleanup": "terminal"
    }
  },
  "context_checkpoint": {
    "sequence": 3,
    "status": "resumed",
    "checkpoint_path": "<run-root>/compactions/0003/CHECKPOINT.md",
    "manifest_path": "<run-root>/compactions/0003/resume-manifest.json",
    "created_at": "2026-08-05T14:10:00Z",
    "resumed_at": "2026-08-05T14:12:00Z",
    "reason": "context-threshold",
    "context_percent": 67,
    "harness": "claude-code",
    "continuity_verified": true,
    "preserved_next_action": "launch phase-1-task-2 implementer"
  },
  "phases": {
    "phase-1": {
      "status": "in-progress",
      "tasks": {
        "phase-1-task-1": {
          "status": "in-progress",
          "task_type": "implementation",
          "prompt_path": "<run-root>/phases/phase-1/phase-1-task-1/task.md",
          "report_path": "<run-root>/phases/phase-1/phase-1-task-1/review-1.md",
          "role_profile": "DeepSeek Flash Worker",
          "transport_attempts": 1,
          "current_attempt": {
            "role": "reviewer",
            "attempt": 1,
            "pid": 48122,
            "launched_at": "2026-08-03T16:31:04Z",
            "log_path": "<run-root>/phases/phase-1/phase-1-task-1/run-reviewer-1.log",
            "liveness": "confirmed"
          },
          "rounds": 1,
          "last_verdict": "FAIL",
          "review_session_id": "svc_abc123",
          "review_independence": "independent",
          "fast_path_eligible": true,
          "evidence_resolution": {
            "status": "clear",
            "pending_question": null,
            "assigned_worker_report": null
          }
        }
      },
      "phase_review": {
        "status": "pending",
        "cycle": 0,
        "latest_audit": null,
        "latest_remediation": null,
        "findings": []
      }
    }
  }
}
```

When the worker harness is OpenCode, `worker_runtime.opencode.run_db` is the
single default run-level DB path. It MUST be absolute and resolve outside the
project root and every worktree. Tasks store session IDs, not duplicate per-worker
DB paths. A configuration that intentionally runs parallel OpenCode workers may
instead persist a `lane_dbs` map, with each session bound to its original external
lane DB. See `OPENCODE.md`.

State transitions must describe reality, not intention. Use these minimum states:

- **`prepared`** — the audited prompt/task file and exact launch `next_action`
  exist, but no worker attempt is claimed;
- **`launching`** — the process was actually started and its attempt number, PID or
  equivalent harness identity, launch time, profile, and log/report paths are
  recorded;
- **`in-progress`** — positive liveness was confirmed for that launched attempt;
- **`waiting-for-worker`** — a transient provider incident is being re-probed;
  `next_probe_at`, profile, attempt history, and relaunch `next_action` exist;
- **`process-exited`** — the worker has actually exited or the harness emitted a
  reliable completion signal; report files may still need validation;
- a later evidence state — a complete report/verdict exists and final hashes/diffs
  were captured after process exit.

Never mark a task or role `in-progress` merely because a spawn was intended. The
following consistency invariant is mandatory:

> `in-progress` requires `transport_attempts >= 1`, an existing audited `task.md`
> (or role prompt artifact), and either a currently live worker identity with
> confirmed liveness or a complete role report proving that the attempt ran.

After the process starts, update state immediately with its real identity; after
liveness is confirmed, transition to `in-progress`. On intake, resume, and before
trusting `next_action`, validate this invariant. If it fails, repair state and
reconstruct the missing transition instead of assuming the worker ran. A small
project-local consistency script may be used, but the invariant—not any specific
script—is authoritative.

After every meaningful transition, record the effective role profile, attempt,
report/log paths, verdict, session id, review independence, current plan hash,
major-log path, execution status, and one exact `next_action`. When OpenCode is the
worker harness, keep the run-level external DB path under `worker_runtime`, not in
each task. `state.json` is the source of truth **inside that run**; artifacts are
the evidence.

### External worker runtime storage

Harness runtime state required for resume may live outside the project while its
identity remains durable inside `state.json`.

For OpenCode:

- default to one external disposable DB per DSD run;
- never place the DB under the project/worktree or `DeepSeekAndDestroy/` tree;
- keep completed sessions during the run unless early deletion is useful and no
  future resume can need them;
- at `COMPLETED` or intentional abandonment/cleanup, preserve durable reports,
  confirm no worker can resume, then remove the run DB plus `-wal`/`-shm` sidecars;
- if the run resumes after an orchestrator crash, verify the recorded external DB
  still exists before attempting a session resume;
- if external runtime storage vanished, treat the child session as unavailable and
  use durable reports plus the fresh-worker fallback rather than reconstructing a
  session that no longer exists.

The external DB is disposable runtime state, not an evidence artifact. Durable
worker reports, Decision Packets, scope hashes, and major-log entries remain under
the run root.

### Authority cache, handover, and resume fast path

`authority-index.json` records every governing plan/document/config/prompt-library
path with its content hash and a concise authority summary.

`HANDOVER.md` is the small, live continuity packet. Maintain it incrementally
rather than reconstructing it at compaction time. It records:

- run/plan/worktree identity and authoritative snapshot;
- project ethos or non-regression rules easy to lose;
- user instructions introduced during this run;
- current phase/task/remediation cycle;
- recent accepted Decision Packet paths;
- important learned architecture or harness quirks;
- material corrections and major-log ids;
- active worker/session/report paths and external runtime identity when needed;
- open disputed facts or human requirements;
- one exact `next_action` and actions forbidden on resume.

Do not copy complete task reports, raw logs, large artifacts, or the full plan into
`HANDOVER.md`. Routine task transitions normally require only updating current
state and `next_action`; rewrite handover prose only when continuity meaningfully
changes.

On resume, read `HANDOVER.md`, `state.json`, `plan-reference.md`, and the relevant
Decision Packets first. Compare hashes mechanically. Re-read only files that
changed, lack a trustworthy summary, or are required verbatim for the next
plan-wide decision. Do not reload the unchanged plan, all architecture documents,
all task reports, the full major log, or all of `PROMPTS.md` merely because a new
orchestrator session began.

When a companion template file is unchanged, read only the required role section
or use its recorded template hash/version. This resume fast path is the default;
full-context reconstruction is reserved for missing, stale, or contradictory
state.

### Context checkpoints

Use `COMPACTION.md` for the full protocol and `HARNESS.md` for adapter selection.
Each checkpoint is an immutable directory under `compactions/`. The helper
snapshots live state, handover, plan reference, and authority index and writes a
small resume manifest. It does not replace the live run files.

Valid checkpoint states are:

- `prepared` — immutable checkpoint exists;
- `compacting` — native compaction was requested or started;
- `rehydration-required` — native compaction or session replacement completed;
- `resumed` — identity and continuity were verified;
- `compaction-failed` — checkpoint remains valid but native compaction failed.

While checkpoint status is `prepared`, `compacting`, or
`rehydration-required`, perform no project work. Complete compaction/rehydration
first. After rehydration, compare live hashes, revalidate active workers, run
`verify-resume`, and execute live `next_action` immediately.

Hooks must resolve the exact run through `DSD_RUN_ROOT`, a matching orchestrator
session id, or one unambiguous active run. They must not guess among multiple
active runs.

### Decision Packets and evidence loading

Every worker artifact begins with `## Decision Packet`. The orchestrator reads
that section first, preferably through `scripts/decision_packet.py`. Full reports,
raw logs, code, and large artifacts remain cold evidence and are opened only when:

- the packet is missing, malformed, or internally inconsistent;
- two independent packets conflict;
- scope/preservation evidence moved unexpectedly;
- review independence was lost;
- a material correction invalidates prior acceptance;
- a plan-wide decision genuinely requires detailed inspection.

For a fresh independent PASS with clean mechanical evidence and
`FAST-PATH ELIGIBLE: YES`, the packet is sufficient for task acceptance. Routine
importance is not a reason to duplicate the review.

### Turn-exit and next-action invariant

An active run may yield an orchestrator turn only when at least one is true:

- a recorded worker identity is live;
- the run is `waiting-for-worker` with a concrete persisted `next_probe_at` and
  relaunch action;
- a legitimate terminal state is recorded.

A future-tense note such as "launch task X next" is not enough. The process or
probe must already have started. A harness Stop hook may enforce this invariant.
The included `scripts/check_state.py` can support such a hook, but the invariant—not
the script—is authoritative.

### Phase current-state audit

Before first decomposition of a phase—or after material plan/tree drift—the
orchestrator commissions a fresh **Phase Surveyor** to create or update
`phases/<phase-id>/current-state-audit.md`. Reuse the existing audit after routine
accepted tasks; do not resurvey the phase merely because execution resumed. It is
a read-only measured inventory:

- required capabilities that already exist;
- which are actually wired/reachable versus merely present;
- unreviewed or partially written code/artifacts;
- unexpected changes and likely provenance when evidence supports it;
- missing or stale paths assumed by the plan;
- verification already available and verification still required;
- recommended independently reviewable task units.

The surveyor performs the repository-scale measurement and cites its predicates,
commands, files, and symbols. The orchestrator reads only the Decision Packet by
default, resolves conflicts against plan authority, and decides decomposition. It
must not personally reproduce the survey absent a recorded conflict trigger.

This audit prevents duplicate tasks and makes partial output from dead workers
visible before new work is scheduled.

### Scope baseline and crash-damage protocol

Before every mutating worker spawn, use `scripts/scope_snapshot.py`, equivalent
VCS/hash tooling, or a cheap bounded baseline worker to record a **new per-attempt
scope baseline** against the immediately previous accepted tree state. Never reuse
an older task baseline after another accepted task or fix has changed the tree.
Record:

- cryptographic hashes for every existing declared in-scope file;
- the expected path set, including expected new paths;
- hashes for relevant untracked files;
- a broader changed-path/diff inventory sufficient to detect unexpected edits
  outside the declared scope.

This is mechanical evidence collection. The orchestrator verifies the declared
scope and that a current baseline artifact exists; it should not manually hash and
inspect every file. Rolling scope baselines are disposable attempt evidence;
behavior-preservation baselines remain immutable and are not refreshed merely
because accepted implementation changed the tree.

`git status --porcelain` is useful only for discovering path names. Its status
letters do not prove content stability: an already-modified file remains `M`, and
an untracked file remains `??` after a full rewrite. Never use status letters as
the scope predicate.

If a worker exits without a complete report, is killed, times out, or loses
transport after beginning work:

1. mark the task `suspect-changes`;
2. wait until the process is confirmed exited;
3. mechanically capture the before/after hash and content-diff evidence;
4. when any non-obvious change exists, spawn a fresh **Recovery Auditor** to
   classify complete, partial, undeclared, baseline-moving, and unsafe changes;
5. have the Recovery Auditor recommend adopt-for-review, quarantine, revert, or
   additional evidence without modifying the tree;
6. let the orchestrator choose the disposition from the compact audit and project
   authority;
7. update the phase current-state audit;
8. only then retry, split, or schedule another task.

Never infer "no report" as "no code changes". The orchestrator owns the recovery
decision, not the volume forensic inspection.

### Phase audit evidence

Before the main-orchestrator hard gate, keep substantial verification reports
under `phases/<phase-id>/verification/` and have a fresh **Phase Auditor** write
`phases/<phase-id>/phase-audit.md`. The phase audit synthesizes task verdicts,
verification evidence, scope/preservation results, integration risks, relevant
defects, and plan fidelity. It does not approve the phase.

The orchestrator reads the Phase Auditor Decision Packet first and makes the final
approval decision from compact evidence. It does not inspect project code, rerun
phase verification, repeat reviewer measurements, or resolve factual uncertainty
itself. A conflict or missing fact becomes a fresh targeted worker assignment.
Raw multi-megabyte artifacts and long suite output remain in worker reports.

### Phase remediation cycles

When the orchestrator's phase gate finds a gap, it writes an immutable
`phase-remediation-<n>.md` rather than changing project files. The remediation plan
contains:

- the source phase-audit/finding ids and concise rationale;
- the governing plan or architecture decision;
- bounded independently reviewable worker tasks and dependencies;
- acceptance criteria, required verification, preservation tripwires, and
  explicit exclusions;
- the evidence required before the phase gate may be retried.

Every remediation task uses the normal worker implementation/review/repair loop.
After all remediation tasks pass, fresh Verification Workers rerun affected gates
and a new fresh Phase Auditor writes the next audit. Preserve previous audits and
remediation plans; never overwrite the evidence chain. The orchestrator then
repeats the plan-wide approval decision. It never implements or self-verifies a
phase remediation.

### Completion evidence

A report file appearing is a checkpoint, not a completion signal. Workers may
still be writing code, logs, major-log entries, or other artifacts. Capture final
hashes/diffs and assert missing artifacts only after process exit or a reliable
harness completion event.

### User-facing progress record

The run files are the detailed progress record. User-facing chat is not a mirror
of those files. For routine transitions, the orchestrator may provide one concise
status sentence containing task id, active role, and state. Long explanations of
worker findings, test counts, file paths, or engineering rationale stay in the
Decision Packet and major log.

A fuller user message is reserved for a material correction, human blocker, major
plan-level decision, phase completion, or final completion. Even then, summarize
and link the durable artifact instead of reproducing it.

### Major findings and fixes log

Every run owns one append-oriented file:

```
<run-root>/major-findings-and-fixes.md
```

Its purpose is not to duplicate every task report. It preserves the engineering
knowledge that a future worker or orchestrator would otherwise have to rediscover.
Log an item when it includes one or more of the following:

- a material defect, regression, integrity issue, or acceptance-threatening gap;
- a non-obvious root cause or important diagnostic discovery;
- a fix that changes architecture, contracts, data shape, compatibility, security,
  cross-task behavior, or future-phase assumptions;
- a consequential design decision or rejected alternative;
- invalidation or preservation of previously accepted evidence;
- an escalation, worker-availability incident, human blocker, or orchestrator
  phase-gate/remediation decision;
- a material correction to a previously reported claim, measurement, or decision;
- a major out-of-scope defect that affects planning or later work.

Do not clutter it with routine edits, formatting, ordinary test output, or every
minor review note. Record concise engineering rationale and evidence, **not hidden
chain-of-thought, private scratchpad, or raw internal deliberation**.

Use a stable heading/id and update one root-cause thread with linked finding,
decision, fix, and verification status rather than creating a new entry for every
routine follow-up. Consolidate closely related corrections/incidents when they
share the same root cause. Each entry should contain, as applicable:

```markdown
## <entry-id> — <short title>
- Time:
- Actor / role:
- Phase / task / review round:
- Type: finding | fix | decision | correction | escalation | availability | human-escalation | plan-change
- Status: open | fixed | deferred | accepted-risk | superseded
- Related entries:
- Evidence and affected artifacts:
- What happened and why it matters:
- Root cause / engineering rationale:
- Chosen action or fix:
- Alternatives considered and why rejected:
- Verification performed and result:
- Remaining risks / follow-up:
```

Workers append entries for major findings and fixes they discover or perform.
A reviewer that raises a major finding logs the finding; the resumed or fallback
fixer appends a linked fix entry. The main orchestrator logs its own phase-level
findings, plan changes, availability decisions, human escalations, remediation
plans, and the reasoning behind accepting or rejecting consequential solutions.
At each task and phase gate, the orchestrator checks that required entries exist
and link back to the detailed reports rather than trusting the log as a substitute
for evidence.

A material correction must identify the earlier claim, the corrected result, the
evidence that changed the conclusion, and any downstream state/tasks/decisions
that were repaired. Surface the correction to the user promptly, then continue
execution unless it creates a genuine human blocker.
