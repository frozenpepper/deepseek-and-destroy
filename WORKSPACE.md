# DeepSeek and Destroy Workspace Contract

This file contains the detailed durable-state, plan-history, concurrency, and
engineering-log contract used by `SKILL.md`.

## Workspace layout

Use a visible project-root directory named `DeepSeekAndDestroy/`. It groups
history by plan and isolates every orchestrator execution in its own run. The
plan folder is for discovery and grouping; the **run directory is the only
mutable source of truth for that execution**.

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
          effective-configuration.md       # resolved configuration; no secrets
          major-findings-and-fixes.md      # append-only engineering rationale log
          out-of-scope-defects.md          # unrelated defects discovered during work
          ephemeral-db/                    # opencode only; delete DBs after lifecycle
          phases/
            <phase-id>/
              <task-id>/
                task.md
                scope-baseline.json
                preservation-baseline.md
                implementer.log
                implementer-report.md
                review-1.md   fix-1.md
                review-2.md   fix-2.md
                ... review-5.md
                reviewer-session-<n>.id
                run-<role>-<attempt>.log
                verdict.json
```

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
  identity/label, harness, creation time, status (`active`, `human-blocked`, `paused-by-user`, `completed`, or
  `abandoned`), project root, worktree, branch when applicable, and any parent
  or handoff run. Do not edit another active run's files.
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

Never overwrite a plan snapshot. On resume, compare the current source with the
recorded hash. If it changed, determine whether the change is intentional before
continuing, record the decision, and capture a new snapshot. If the original
source is unavailable, the stored snapshot preserves the exact plan used, but the
run must state that it is continuing from the snapshot rather than pretending the
live source was checked.

### Concurrent-orchestrator protocol

1. At startup, discover existing plan/run manifests before creating files.
2. Resume a run only when its exact run path/id is supplied or one candidate is
   unambiguously identified by a handoff. If multiple active candidates exist,
   do not guess or merge their state.
3. Before taking over a paused/interrupted run, record the handoff in
   `run-manifest.md` and confirm the prior worker processes can no longer write.
4. Never write state, logs, reports, ephemeral DBs, or task artifacts into another
   run merely because it targets the same plan.
5. Before concurrent source edits, compare declared task scopes and worktrees. If
   overlap is possible, isolate with worktrees/branches or coordinate sequencing.
6. When one run depends on another, reference its run id and immutable artifacts;
   do not copy its mutable `state.json` into the current run.

Keep the workspace proportional. Preserve durable manifests, plan snapshots,
major rationale, reports, and evidence needed for recovery. Raw logs may be
trimmed or excluded according to project policy. Do not blanket-ignore the whole
`DeepSeekAndDestroy/` tree when its durable history is intended to be tracked;
ignore ephemeral DBs and oversized transient logs selectively.

Task-id convention: `<phase-id>-<seq>` or a short stable slug.

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
  "project_worktree": "/abs/path/to/project-worktree",
  "effective_config": "<run-root>/effective-configuration.md",
  "major_log": "<run-root>/major-findings-and-fixes.md",
  "execution_status": "active",
  "terminal_condition": null,
  "next_action": "resume phase-1-task-1 reviewer round 1 as fixer",
  "decision_sources": ["DOCS/Plans/example.md", "AGENTS.md", "DOCS/Architecture.md"],
  "worker_availability": { "status": "available", "last_incident": null },
  "phases": {
    "phase-1": {
      "status": "in-progress",
      "tasks": {
        "phase-1-task-1": {
          "status": "in-progress",
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
          "review_worker_db": "/abs/path/to/<run-root>/ephemeral-db/phase-1-task-1-review-1.db",
          "review_independence": "independent"
        }
      },
      "phase_review": { "status": "pending", "findings": [] }
    }
  }
}
```

`*_worker_db` fields are present only when the harness is opencode and must
always be absolute paths.

State transitions must describe reality, not intention. Use these minimum states:

- **`prepared`** — the audited prompt/task file and exact launch `next_action` exist,
  but no worker attempt is claimed;
- **`launching`** — the process was actually started and its attempt number, PID or
  equivalent harness identity, launch time, profile, and log/report paths are
  recorded;
- **`in-progress`** — positive liveness was confirmed for that launched attempt;
- a later evidence state — a complete report/verdict exists even if the process
  already exited.

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
report/log paths, verdict, session id, worker ephemeral DB path when applicable,
review independence, current plan hash, major-log path, execution status, and one
exact `next_action`. `state.json` is the source of truth **inside that run**;
artifacts are the evidence.

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
- an escalation, worker-availability incident, human blocker, or direct orchestrator intervention;
- a material correction to a previously reported claim, measurement, or decision;
- a major out-of-scope defect that affects planning or later work.

Do not clutter it with routine edits, formatting, ordinary test output, or every
minor review note. Record concise engineering rationale and evidence, **not hidden
chain-of-thought, private scratchpad, or raw internal deliberation**.

Use a stable heading/id and append finding and fix entries rather than rewriting
history. Each entry should contain, as applicable:

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
fixer appends a linked fix entry. The main orchestrator logs its own phase-level findings, plan changes,
availability decisions, human escalations, direct repairs, and the reasoning
behind accepting or rejecting consequential solutions. At each task and phase
gate, the orchestrator checks that required entries exist and link back to the detailed
reports rather than trusting the log as a substitute for evidence.

A material correction must identify the earlier claim, the corrected result, the
evidence that changed the conclusion, and any downstream state/tasks/decisions
that were repaired. Surface the correction to the user promptly, then continue
execution unless it creates a genuine human blocker.
