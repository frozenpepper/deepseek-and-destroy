# DSD — Claude Code Parent Adapter

Load only when the premium parent runs in Claude Code.

Install the project adapter once when needed:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py --harness claude-code --project-root <project-root>
```

Normal workers are launched through `dsd_attempt.py launch`. The installed
`PostToolUse:Bash` + `asyncRewake` hook watches the returned exact `terminal.json` without
model polling and wakes Claude only when that external worker terminates. On wake, run
`dsd_attempt.py gate`; do not sample logs/CPU/repository merely for liveness.

If project hooks are unavailable, use the returned attempt directory with
`wait_worker.py --event-dir <attempt-dir>`. A host timeout without `terminal.json` is a
non-event: immediately wait again.

The adapter also installs checkpoint hooks. For compaction/restart details load
`COMPACTION.md`; when multiple runs are active, set exact `DSD_RUN_ROOT` rather than
letting hooks guess.
