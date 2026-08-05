# DeepSeek and Destroy — Kilo Code Adapter

Read this file when either the main orchestrator or an effective worker
profile uses Kilo Code. It defines the role-separated native-subagent worker
profile and the (experimental, unverified) Kilo orchestrator compaction
plugin. Other harnesses (OpenCode, Codex, claude-code, custom) have their own
adapters and are unaffected by this file.

## Why the worker side looks different from OPENCODE.md

OpenCode workers are separate OS processes: the orchestrator shells out to
`opencode run`, tracks a PID, polls CPU/output to infer liveness, and manages
an isolated ephemeral SQLite database per worker so throwaway sessions don't
bloat the interactive database. None of that applies here.

Kilo Code's CLI (`kilo`) has a **native subagent system**: a primary agent
(the orchestrator) calls its own `task` tool to delegate a unit of work to a
named subagent, in-process, synchronously. The call returns when the
subagent's turn is done. There is no detached process to track, no PID to
capture, no redirected log to poll, and no ephemeral database to create or
clean up.

Kilo owns subprocess and child-session **runtime** management. It does
**not** own DSD's own orchestration state and evidence obligations — this
adapter still requires attempt id, role, agent name, resolved model, launch
time, completion time, report path, and invocation outcome recorded in
`state.json` exactly as `WORKSPACE.md` specifies for every other harness.
Native delegation removes process/PID/database bookkeeping; it does not
remove DSD's own bookkeeping.

(Kilo's CLI is itself built on OpenCode's engine — its own logs and internal
docs reference `opencode` directly, and its bundled runtime references the
same plugin hook names — which is why global flags like
`--model provider/model` and the compaction plugin interface below look
familiar. That lineage is suggestive, not proof: verify anything below marked
experimental against a real Kilo session before depending on it.)

## Prerequisites

Before this profile can be used:

1. `kilo` CLI installed (`npm install -g @kilocode/cli`) — version should
   match the Kilo Code extension in use, if any.
2. The role-separated subagents installed:

   ```bash
   python3 <skill-root>/scripts/install_kilo_agents.py \
     --project-root <project-root>
   ```

   This resolves the effective worker model (default
   `deepseek/deepseek-v4-flash`; override with `--model provider/model`),
   **verifies that exact id against `kilo models` before writing anything**,
   and installs `dsd-mutating-worker` and `dsd-readonly-worker` to
   `<project-root>/.kilo/agents/`. Pass `--global` to additionally install to
   `~/.config/kilo/agents/` — this is never done silently; global install is
   opt-in only. Verify with `kilo agent list`: both agents should appear as
   `(subagent)`.
3. A DeepSeek credential configured in Kilo (`kilo auth`) so the resolved
   model actually resolves. The default `deepseek/deepseek-v4-flash` is a
   **direct DeepSeek provider model**, not the `kilo/deepseek/...`
   gateway/credits namespace — cost is governed by DeepSeek's own pricing,
   not Kilo credits, unless you deliberately resolve a `kilo/`-prefixed
   model instead. Never place the API key in a prompt, config file, or
   anywhere this skill's state/log files might capture it — `kilo auth`
   stores it directly.
4. If the main orchestrator itself runs as Kilo, it needs a **primary** agent
   with `task` and `skill` permissions. Kilo ships a built-in `orchestrator`
   primary agent that already qualifies (`kilo --agent orchestrator run ...`
   or launch it as the default interactive agent); a custom primary agent
   works equally well as long as those two permissions are not denied.

If either subagent is not registered or the model does not resolve, this is
a setup gap, not a transport failure: do not retry — apply the Human
escalation gate ("required credentials... are unavailable").

## Default worker profile

- **Profile:** DeepSeek Flash Worker (role-separated)
- **Harness:** Kilo Code native subagent
- **Agents:**
  - `dsd-mutating-worker` — Implementer, Fixer. Can edit files.
  - `dsd-readonly-worker` — Phase Surveyor, Discovery Worker, Verification
    Worker, Reviewer, Recovery Auditor, Phase Auditor. `edit: deny` at the
    permission level, not merely by instruction — an independent reviewer
    that can silently patch its own findings is not independent.
- **Model:** resolved and verified at install time by
  `scripts/install_kilo_agents.py`, pinned into each agent's own frontmatter
  (default `deepseek/deepseek-v4-flash`). Do not hand-edit the model in an
  installed agent file; re-run the installer with `--model` so the id gets
  re-verified against `kilo models`.
- **Endpoint:** the DeepSeek provider already configured via `kilo auth`.
- **Ephemeral storage:** none required. Kilo owns subagent session storage;
  there is nothing to isolate or delete.

### Delegating a unit of work

Pick the agent by whether the role mutates files, then call the orchestrator's
own `task` tool with a full self-contained prompt built per `PROMPTS.md`'s
Common Rules and the exact role template — same content contract as any other
harness, just a native tool call instead of a constructed shell command:

```
task(agent="dsd-mutating-worker", prompt="<full IMPLEMENTER/FIXER prompt from PROMPTS.md>")
task(agent="dsd-readonly-worker", prompt="<full role prompt from PROMPTS.md>")
```

For manual testing or debugging outside an orchestrator session, the
equivalent standalone invocation is:

```bash
kilo run --agent dsd-mutating-worker "<full self-contained role prompt>"
kilo run --agent dsd-readonly-worker "<full self-contained role prompt>"
```

**The prompt passed at call time is the worker's actual instructions.** Each
agent's own static system prompt only establishes identity and the
permission boundary; it does not restate a role's specific acceptance
criteria, verification commands, or reporting requirements. Always assemble
and pass the complete PROMPTS.md-derived prompt — including the Decision
Packet requirement and the role's exact verdict/completion marker — the same
way you would for any other harness. Do not rely on a worker's static system
prompt to carry task-specific contract details; it cannot know them.

The call is synchronous: it returns the subagent's final report (or an
error). **Completion is the tool call returning** — there is no separate
liveness probe, PID check, or output-growth heuristic to run first. That does
not exempt this role invocation from `WORKSPACE.md`'s normal state-transition
bookkeeping (`prepared` → `launching` → `in-progress` → evidence state); it
only means the "launching" and "in-progress" window for a native call is
usually very short.

### Repair and resume

Kilo's CLI supports `--session`/`--continue` for resuming a specific prior
session from the command line, but this adapter does not depend on a
tool-level equivalent being available inside a delegated `task` call — that
is unconfirmed and should be treated as untested until verified empirically.
Default to the robust path: when a reviewer reports FAIL, delegate a **fresh**
`dsd-mutating-worker` fixer task that references the reviewer's durable
report by path rather than pasting its full content inline (same as any
other harness) — embed findings verbatim only when they are short enough that
a path reference would cost more than it saves. If session-level resume
through the `task` tool is confirmed to work in practice, prefer it for
moderate review contexts and update this file.

### Health probe

Before spending a real attempt after suspected provider trouble (repeated
banner-only/empty responses, ambiguous errors), delegate a trivial isolated
probe task asking for exactly `HEALTHCHECK OK` and nothing else to either
agent, same intent as `scripts/opencode_probe.py` but with no script needed:

```
task(agent="dsd-readonly-worker", prompt="Reply with exactly HEALTHCHECK OK and nothing else. Do not modify files.")
```

Do not infer exhausted credit/billing from an error string alone; verify what
`kilo auth` / `kilo models` can actually prove first.

### Failure classification

Map the `task` call's outcome onto SKILL.md's existing failure table:

| Observed | Classification |
|---|---|
| Tool call returns a report with a readable verdict | Normal — proceed to review as usual |
| Tool call errors with an auth/credential failure | Availability, human action likely — HUMAN-BLOCKED per credential gate above |
| Tool call errors with a rate-limit / transient provider error | Availability, likely transient — back off, health-probe, retry |
| Tool call times out or the CLI process itself dies | Transport — treat the orchestrator's own session as compromised; do not retry blindly, investigate before relaunching |
| Report is malformed, missing a verdict, or empty | Transport — malformed output, not a substantive review round |
| Report has a clean verdict but content is wrong/incomplete | Substantive — normal repair and fresh re-review loop |

### Cleanup

No process, PID record, or ephemeral database file to remove — that
maintenance category does not exist under native subagent delegation. This
does **not** shrink DSD's own `state.json`/report/major-log obligations,
which are unaffected by which worker harness is in use.

- **Roles:** `dsd-readonly-worker` handles Phase Surveyor, Discovery Worker,
  Verification Worker, Reviewer, Recovery Auditor, and Phase Auditor.
  `dsd-mutating-worker` handles Implementer and Fixer. This is the minimum
  role separation the worker-authority contract requires (mutation
  capability is the safety-critical boundary); a project that wants tighter
  per-role prompts can still generate additional agents from the same
  templates in `adapters/kilo/agents/`.

Default review budget is 5 substantive rounds; default immediate transport
budget is 5 launch attempts per role invocation, same as the OpenCode
profile. Execution is sequential. The main orchestrator performs
decomposition, plan-wide decisions, substantive escalation decisions, and
final phase approval — it is not a fallback worker when either subagent is
unavailable.

## Main-orchestrator context checkpoints in Kilo Code

This section applies when the **main orchestrator** itself runs in Kilo Code.
It is separate from the worker profile above, and it is **experimental and
unverified** — see `HARNESS.md`'s capability matrix.

Kilo's bundled CLI runtime references the same `experimental.session.compacting`
plugin hook name OpenCode's plugin interface uses. That is evidence a
pre-compaction adapter is plausible, not confirmation it works: no live Kilo
run has verified the hook fires, what shape it receives, or where Kilo
actually expects a local (non-npm-published) plugin file to live.

Install the experimental adapter:

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --harness kilo \
  --project-root <project-root>
```

This copies:

- `.kilo/plugins/dsd-compaction.ts` (template at `adapters/kilo/dsd-compaction.ts`);
- `DeepSeekAndDestroy/tools/context_checkpoint.py`.

**Before trusting this for any run you can't afford to lose continuity on:**
start a Kilo session, force or wait for native compaction, and confirm a new
checkpoint actually appears under `DeepSeekAndDestroy/compactions/`. Until
that is confirmed, treat Kilo as manual/fresh-session mode:

1. keep `HANDOVER.md` incrementally current;
2. at the configured threshold (default 65%), run
   `context_checkpoint.py prepare` manually;
3. compact or start a fresh orchestrator session from the checkpoint;
4. reload the skill, `KILOCODE.md`, and live run files, then run
   `verify-resume` before any further project work.

If the plugin path is later confirmed to work, this file should be updated to
promote Kilo out of the experimental tier in `HARNESS.md` and
`scripts/detect_harness.py`.
