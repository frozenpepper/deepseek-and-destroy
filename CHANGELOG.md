# Changelog

## Runtime reliability and claim-discipline revision

Based on extended orchestrator use:

- replace buffered OpenCode log-growth liveness with actual-process accumulated
  CPU-time sampling;
- add explicit `prepared` → `launching` → `in-progress` state transitions and a
  consistency invariant that catches intended-but-never-started spawns;
- add a preflight heuristic to split likely >30-minute tool-heavy tasks before
  the first worker launch;
- require inherited prompt audits to cover rules, criteria, commands, worktree,
  and every report/log/output path;
- add measurement-predicate discipline for counts, absence, completeness, and
  search claims;
- require material corrections to be surfaced, logged, propagated through state
  and decisions, and followed by continued execution.

## Autonomous-continuation and clarity revision

This revision restructures the skill around the primary execution contract:

- continue until the complete plan is finished or genuinely human-blocked;
- do not stop after tasks, reviews, or phases for routine acknowledgement;
- resolve ordinary decisions from the plan, project documentation, architecture,
  accepted evidence, and project ethos;
- escalate to humans only for major decisions, authorization/access, persistent
  worker availability, unsafe concurrency, or irreconcilable plan problems;
- never substitute the main orchestrator for unavailable workers;
- distinguish substantive escalation from worker availability and human escalation;
- persist one exact `next_action` after every meaningful transition;
- treat resume as continued execution rather than status reporting.

The formerly monolithic skill was split for clarity:

- `SKILL.md` — core mission, authority, loop, escalation, and gates;
- `WORKSPACE.md` — run namespaces, plan snapshots, concurrency, state, and logs;
- `PROMPTS.md` — exact worker prompts and Common Rules;
- `OPENCODE.md` — OpenCode-specific worker storage and launch behavior.

The existing multi-orchestrator run layout, immutable plan references, major
findings/fixes log, reviewer-led repair, fresh re-review, liveness checks,
transport separation, preservation baselines, defect ledger, and validation
independence remain in place.
