# DSD — Codex Parent Adapter

Load only when the premium parent runs in Codex. Default workers remain external
OpenCode processes.

Launch through `dsd_attempt.py launch`, then wait quiescently on the exact terminal event
(returned attempt directory) with `wait_worker.py` when the tool cannot remain open. A
host timeout without `terminal.json` is a non-event: wait again; no periodic `ps`, log,
CPU, or repository checks. On terminal completion run `dsd_attempt.py gate`.

Install project-local checkpoint integration only when needed:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py --harness codex --project-root <project-root>
```

If hooks are unavailable, use `COMPACTION.md` manual/fresh-session recovery. Native Codex
agent waiting applies only when a run explicitly selects a native worker backend; never
confuse it with the default external-worker lifecycle.
