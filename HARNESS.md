# DSD Parent Harness Router

Load exactly one parent adapter only when host-specific waiting/continuity is needed:
`CLAUDE.md`, `CODEX.md`, `KILO.md`, or the OpenCode/generic notes in `OPENCODE.md`.
The default technical worker remains external OpenCode + DeepSeek regardless of parent.

Universal invariant: waiting is quiescent. A host/tool wait timeout with no exact
`terminal.json` is a non-event—wait again without polling logs/CPU/repository or spending
a model turn diagnosing liveness. Process/transport errors trigger recovery/availability;
semantic worker outcomes are interpreted only after the mechanical gate.

Compaction is separate from worker waiting; load `COMPACTION.md` only when needed.
