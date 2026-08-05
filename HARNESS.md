# DeepSeek and Destroy Orchestrator Harness Selection

This file selects the context-checkpoint adapter for the **main orchestrator**.
It is independent from the harness used to launch worker agents.

## Assessment sequence

1. Use an explicit user/config value when present:
   `orchestrator_harness: codex | claude-code | opencode | custom`.
2. Otherwise inspect the current session/system context.
3. Run the conservative detector:

   ```bash
   python3 <skill-root>/scripts/detect_harness.py --json
   ```

4. Never choose a harness merely because its CLI is installed. If detection is
   ambiguous, use the harness identified by the current session or ask only when
   that identity genuinely cannot be established.
5. Record the result and capabilities in `effective-configuration.md` and
   `state.json.orchestrator`.

## Capability matrix

| Orchestrator harness | PreCompact | PostCompact | Context reinjection after compact | Best adapter |
|---|---:|---:|---:|---|
| Codex | yes | yes | `SessionStart` source `compact` | `CODEX.md` |
| Claude Code | yes | yes | `SessionStart` matcher `compact` | `CLAUDE.md` |
| OpenCode V2 | plugin pre-compaction hook | no documented post hook | skill/state invariant plus injected compaction context | `OPENCODE.md` |
| Other/unknown | unknown | unknown | manual/fresh-session handoff | `COMPACTION.md` |

## Project-local installation

Prefer project-local adapters. Do not modify user-global harness configuration
without explicit authorization.

Run:

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --harness auto \
  --project-root <project-root>
```

The installer:

- detects or uses the explicit orchestrator harness;
- copies `context_checkpoint.py` to
  `DeepSeekAndDestroy/tools/context_checkpoint.py`;
- installs/merges the project-local Codex or Claude hooks, or the OpenCode plugin;
- backs up modified JSON configuration files;
- writes `DeepSeekAndDestroy/compaction-adapter-installation.md`.

After installation, perform the harness-specific activation step described by the
adapter file. Never assume hooks are active merely because files were written.

## Runtime modes

Select the strongest available mode:

1. **Hooked proactive mode:** exact context use is visible; checkpoint at 65%,
   compact at the next safe boundary, and use hooks for rehydration.
2. **Hooked native mode:** exact percentage is unavailable; keep HANDOVER current
   and let PreCompact create the immutable checkpoint automatically.
3. **Manual mode:** write a checkpoint and invoke native `/compact` or equivalent.
4. **Fresh-session mode:** create the checkpoint and start a new orchestrator
   session from it when native compaction is unavailable or unreliable.

All modes use the same durable checkpoint and post-resume verification contract.
