# DeepSeek and Destroy — Codex Orchestrator Adapter

Use this only when the **premium orchestrator** runs in Codex. The default worker is
still an external OpenCode CLI DeepSeek process; Codex native `wait_agent` semantics
from native-subagent workflows do not automatically apply to it.

## External OpenCode worker: quiescent wait

Preferred order:

1. If the current Codex shell/tool invocation can safely remain open for the
   expected worker duration, run `run_worker.py` in foreground and let tool
   completion be the wake event.
2. Otherwise launch `run_worker.py --detach`, then invoke:

   ```bash
   python3 <skill-root>/scripts/wait_worker.py \
     --event-dir <attempt-dir>
   ```

3. If the host/tool cuts off the wait before a terminal event, that is a
   **non-event**. Emit no prose, inspect no logs/state/repository, and immediately
   issue the same wait again. Do not make the model choose a polling interval.
4. A terminal event ends the wait. Read/classify `terminal.json` once. Only a
   successful `completed` exit enters `evidence_gate.py`; non-zero worker exits use
   suspect-change/recovery, and pre-start transport errors use availability logic.

Do not use periodic `ps`, `pgrep`, log-size reads, or short sleeps as the scheduler.
Those remain recovery diagnostics after a real inconsistency/error only.

If a future/user-selected Codex-native worker backend is used instead of OpenCode,
then native agent wait primitives may apply to that backend. Do not generalize them
to the default external worker.

## Compaction / continuity

Install the project-local Codex checkpoint adapter:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py \
  --harness codex \
  --project-root <project-root>
```

The adapter uses current Codex project-local compaction/session hooks where
available and copies the DSD checkpoint helper. Project-local hooks may require a
trusted project and may be disabled by managed policy; when unavailable, use the
generic manual/fresh-session protocol from `COMPACTION.md`.

When current Codex exposes the model context window/configurable auto-compact limit,
configure the DSD threshold only from real values; never invent a context size.
The optional `adapters/codex/config.fragment.toml` is a reference fragment for that
manual tuning; the installer does not guess or overwrite context-window values.

Official references:

- https://developers.openai.com/codex/hooks
- https://developers.openai.com/codex/config-reference
