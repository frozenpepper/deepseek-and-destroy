# DSD — Parent Harness Routing

Cold routing reference.

Parent harness and worker harness are independent. Default technical workers are external OpenCode/DeepSeek even when the premium parent is Codex, Claude Code, Kilo, or OpenCode.

Prefer explicit harness configuration/session identity; use `detect_harness.py` only as a conservative hint. Load exactly one parent adapter:

- `CODEX.md`
- `CLAUDE.md`
- `KILO.md`
- `OPENCODE.md` when OpenCode is also the parent

Universal invariant: waiting is quiescent. External workers wake on exact `terminal.json`; supported native workers finalize the same DSD lifecycle when their native Task returns. Transport completion never implies semantic PASS.

Install the selected project-local continuity adapter once. Its Python hook shims execute the currently installed skill, so ordinary skill upgrades do not copy stale control-plane code into the project. Rerun the idempotent installer only when installing into a new project or when harness hook/plugin definitions change:

```bash
python3 <skill>/scripts/install_harness_adapter.py --project-root <project> --harness <codex|claude-code|opencode|kilo>
```

Load `COMPACTION.md` only when checkpoint/resume behavior is relevant.
