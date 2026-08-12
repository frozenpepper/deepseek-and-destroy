# DSD — Kilo Code Parent / Native Worker Adapter

Load only when the premium parent runs in Kilo or the run explicitly selects Kilo-native
workers. Default workers otherwise remain external OpenCode.

Install parent continuity integration when needed:

```bash
python3 <skill-root>/scripts/install_harness_adapter.py --harness kilo --project-root <project-root>
```

For optional native workers install the two capability wrappers:

```bash
python3 <skill-root>/scripts/install_kilo_workers.py --project-root <project-root>
```

Choose wrapper by **actual immutable write capability**, not role name:

- mutating: Implementer/Fixer; Verification only when `Allowed source changes` is nonempty;
- read-only: Reviewer, Discovery, Phase Surveyor, Recovery, Phase Auditor, all Evidence
  Clerks, and read-only Verification.

Native Task calls must still use `native_worker_attempt.py reserve` before invocation and
`finalize` immediately after the Task returns, then the normal mechanical evidence gate.
The native Task return is the terminal boundary; semantic FAIL is still completed
transport. Never fabricate completion while the subagent is live.

Role changes start fresh native sessions. Read-only wrappers deny project edits; the DSD
scope gate independently catches shell/write-channel drift. For compaction load
`COMPACTION.md`; for external OpenCode workers load `OPENCODE.md` only on transport issues.
