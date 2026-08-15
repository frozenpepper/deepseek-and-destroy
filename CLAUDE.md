# DSD — Claude Code Parent Adapter

Cold-load only when the premium parent is Claude Code. The default technical worker remains external OpenCode/DeepSeek.

Install the project adapter once:

```bash
python3 <skill>/scripts/install_harness_adapter.py --harness claude-code --project-root <project>
```

Normal detached task launch uses the shared interface:

```bash
python3 <skill>/scripts/dsd_attempt.py launch ... --detach
```

The installed `PostToolUse:Bash` async-rewake helper watches the exact attempt `terminal.json` and wakes Claude only when the external worker is terminal. On re-wake run:

```bash
python3 <skill>/scripts/dsd_attempt.py gate --run-root <run> --phase-id <phase> --task-id <task>
```

If project hooks are unavailable, use:

```bash
python3 <skill>/scripts/dsd_attempt.py wait --run-root <run> --phase-id <phase> --task-id <task>
```

A host timeout without terminal evidence is a non-event: wait again without model-visible polling/diagnostics.

The same adapter installs Claude compaction hooks. Its project-local Python files are tiny shims into the installed skill, so a normal skill upgrade does not leave stale copied control-plane code behind. Rerun the installer only if the hook/plugin definition itself changed. On a fresh session follow `SKILL.md`'s resume fast path; load `COMPACTION.md` only when checkpoint state requires it. Claude-native subagent hooks are relevant only when a Claude-native worker backend is explicitly selected.
