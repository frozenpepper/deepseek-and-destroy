# DSD — Codex Parent Adapter

Cold-load only when the premium parent is Codex. The default worker remains external OpenCode/DeepSeek.

Normal task commands are the shared high-level interface:

```bash
python3 <skill>/scripts/dsd_attempt.py launch ... --detach
python3 <skill>/scripts/dsd_attempt.py wait   --run-root <run> --phase-id <phase> --task-id <task>
python3 <skill>/scripts/dsd_attempt.py gate   --run-root <run> --phase-id <phase> --task-id <task>
```

If a foreground tool call can safely stay open for the worker duration, omit `--detach` and let tool completion be the wake event. Otherwise use the long blocking `wait` helper. One host cutoff before `terminal.json` is a non-event. After repeated cutoffs, a credible stall signal may justify one bounded lifecycle/transport diagnosis; log age/size and recorded process liveness are clues, not proof, and continuous model-visible polling remains forbidden.

Native Codex agent wait semantics apply only if the run explicitly selected a Codex-native worker backend; they do not describe the default external worker.

For compaction/continuity install the project adapter and load `COMPACTION.md` only when needed:

```bash
python3 <skill>/scripts/install_harness_adapter.py --harness codex --project-root <project>
```
