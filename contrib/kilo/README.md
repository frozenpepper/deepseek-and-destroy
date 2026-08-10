# DeepSeek and Destroy — Kilo Code Adapter

This is an **optional contributed adapter**. Read it only when the user/config explicitly selects Kilo Code. It is not part of the default DSD topology, which uses external OpenCode CLI DeepSeek workers.

Kilo workers use native subagent delegation rather than OpenCode-style external worker processes.

## Worker model

DSD keeps two Kilo subagents because mutation capability is the meaningful safety
boundary:

- `dsd-mutating-worker` — Implementer/Fixer;
- `dsd-readonly-worker` — Survey, Discovery, Verification, Reviewer, Recovery
  Auditor, Phase Auditor.

Install them project-locally:

```bash
python3 <skill-root>/contrib/kilo/install_agents.py \
  --project-root <project-root>
```

The installer resolves/validates the configured model (default
`deepseek/deepseek-v4-flash`) against `kilo models`, renders the templates under
`contrib/kilo/agents/`, and installs them under `.kilo/agents/`. Global install is
explicit opt-in only.

## Prompt contract

Kilo uses the same **durable path-only contract** as v13; it must not resurrect the
old inline Common-Rules prompt assembly. Generate an immutable
`worker-rules/rNNNN/WORKER_RULES.md` revision plus its protocol snapshot, an
immutable numbered task contract, and the tiny handoff with the normal DSD helpers.

Conceptually:

```text
task(agent="dsd-mutating-worker", prompt="<tiny path-only launch prompt>")
task(agent="dsd-readonly-worker", prompt="<tiny path-only launch prompt>")
```

The child reads the exact worker-rules revision, exact task-contract revision,
role protocol, and applicable proof patterns named by the handoff. Native delegation removes OpenCode PID/DB/wait
bookkeeping for **Kilo-selected workers**; it does not remove DSD state/report/
evidence-gate obligations.

## Read-only independence

The read-only template denies project edits and permits only
`DeepSeekAndDestroy/**` report/spec writes. Verification commands are allowed by
the role contract, but the worker must not use shell commands to mutate project
source. Any unexpected source mutation invalidates review independence and enters
normal recovery.

## Repair

When a Reviewer FAILs, use native child-session resume only when the current Kilo
tooling demonstrably supports the needed continuation path. The robust fallback is
a fresh mutating Fixer given the durable review findings, followed by a different
fresh read-only Reviewer.

## Health and failure classification

For suspected provider trouble, run a trivial delegated `HEALTHCHECK OK` before
burning repeated substantive attempts. Auth/setup errors are availability/setup
problems; malformed/empty outputs are transport/report failures; a well-formed
FAIL is substantive and enters repair.

Do not infer billing exhaustion from an error string alone.

## Orchestrator compaction

When the main orchestrator itself runs in Kilo, install the project-local adapter:

```bash
python3 <skill-root>/contrib/kilo/install_compaction.py \
  --project-root <project-root>
```

It copies the contributed `.kilo/plugins/dsd-compaction.ts` and the DSD checkpoint/state helpers project-locally.
Before relying on automatic Kilo compaction for an irreplaceable long run, perform a
live acceptance where a real compaction produces a DSD checkpoint and the resumed
orchestrator completes `verify-resume` before project work.

Until that live-fire behavior is proven in the local Kilo version, the durable
manual/fresh-session path remains authoritative:

1. keep HANDOVER current;
2. prepare a DSD checkpoint at a safe boundary;
3. compact/start a fresh orchestrator session;
4. reload skill/state/checkpoint identity;
5. run `verify-resume`;
6. execute persisted `next_action`.

Kilo worker execution itself requires no OpenCode `OPENCODE_DB`. OpenCode workers
now use one disposable **external run-level DB**, as documented in `OPENCODE.md`;
older per-worker project-local DB guidance is obsolete.
