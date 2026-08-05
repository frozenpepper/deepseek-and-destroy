# DeepSeek and Destroy — Kilo Code Adapter

Read this file only when the effective worker profile is Kilo Code. It
defines the built-in DeepSeek Flash worker profile and the native
subagent-delegation behavior. Other harnesses (OpenCode, Codex, claude-code,
custom) have their own adapters and are unaffected by this file.

## Why this adapter looks different from OPENCODE.md

OpenCode workers are separate OS processes: the orchestrator shells out to
`opencode run`, tracks a PID, polls CPU/output to infer liveness, and manages
an isolated ephemeral SQLite database per worker so throwaway sessions don't
bloat the interactive database. None of that applies here.

Kilo Code's CLI (`kilo`) has a **native subagent system**: a primary agent
(the orchestrator) calls its own `task` tool to delegate a unit of work to a
named subagent, in-process, synchronously. The call returns when the
subagent's turn is done. There is no detached process to track, no PID to
capture, no redirected log to poll, and no ephemeral database to create or
clean up. Liveness, transport, and session bookkeeping are the CLI's problem,
not the orchestrator's.

This is the same mental model as this skill's own orchestrator role — a main
context delegating bounded units to fresh worker contexts — so "worker" here
maps directly onto a Kilo **subagent**, and "spawn" maps onto a native `task`
tool call instead of a shell command.

(Kilo's CLI is itself built on OpenCode's engine — its own logs and internal
docs reference `opencode` directly — which is why global flags like
`--model provider/model`, `--session`, and `--continue` look familiar. That
lineage is irrelevant to this adapter: delegation here goes through Kilo's
native subagent mechanism, not a reimplementation of the OpenCode subprocess
pattern.)

## Prerequisites

Before this profile can be used:

1. `kilo` CLI installed (`npm install -g @kilocode/cli`) — version should
   match the Kilo Code extension in use, if any.
2. The `deepseek-worker` subagent registered, either project-locally at
   `.kilocode/agents/deepseek-worker.md` or globally at
   `~/.kilocode/agents/deepseek-worker.md` (a symlink to the copy shipped in
   this skill's `.kilocode/agents/deepseek-worker.md` is the simplest way to
   get both). Verify with `kilo agent list` — it should show
   `deepseek-worker (subagent)`.
3. A DeepSeek credential configured in Kilo (`kilo auth`) so the
   `deepseek/deepseek-v4-flash` model resolves. This is a **direct DeepSeek
   provider model**, not the `kilo/deepseek/...` gateway/credits namespace —
   confirm with `kilo models | grep deepseek` and use the bare `deepseek/`
   prefix so cost is governed by DeepSeek's own pricing, not Kilo credits.
   Never place the API key in a prompt, config file, or anywhere this skill's
   state/log files might capture it — `kilo auth` stores it directly.

If the `deepseek-worker` agent is not registered or the model does not
resolve, this is a setup gap, not a transport failure: do not retry:
apply the Human escalation gate ("required credentials... are unavailable").

## Default worker profile

- **Profile:** DeepSeek Flash Worker
- **Harness:** Kilo Code native subagent
- **Agent name:** `deepseek-worker`
- **Model:** `deepseek/deepseek-v4-flash` (pinned in the subagent's own
  frontmatter — do not override per-call; if a different model is needed,
  edit the subagent file rather than passing an ad hoc override)
- **Endpoint:** the DeepSeek provider already configured via `kilo auth`
- **Ephemeral storage:** none required. Kilo owns subagent session storage;
  there is nothing to isolate or delete.

### Delegating a unit of work

The orchestrator delegates by calling its own `task` tool with the
`deepseek-worker` agent and a full self-contained prompt built per
`PROMPTS.md`'s Common Rules and the relevant worker-role template — same
content contract as any other harness, just a native tool call instead of a
constructed shell command:

```
task(agent="deepseek-worker", prompt="<full self-contained role prompt>")
```

For manual testing or debugging outside an orchestrator session, the
equivalent standalone invocation is:

```bash
kilo run --agent deepseek-worker "<full self-contained role prompt>"
```

The call is synchronous: it returns the subagent's final report (or an
error). **Completion is the tool call returning** — there is no separate
liveness probe, PID check, or output-growth heuristic to run first.

### Repair and resume

Kilo's CLI supports `--session`/`--continue` for resuming a specific prior
session from the command line, but this adapter does not depend on a
tool-level equivalent being available inside a delegated `task` call — that
is unconfirmed and should be treated as untested until verified empirically.
Default to the robust path: when a reviewer reports FAIL, delegate a **fresh**
`deepseek-worker` task with the prior findings embedded verbatim in the
prompt (same fallback SKILL.md already sanctions for heavy review contexts).
If session-level resume through the `task` tool is confirmed to work in
practice, prefer it and update this file.

### Health probe

Before spending a real attempt after suspected provider trouble (repeated
banner-only/empty responses, ambiguous errors), delegate a trivial isolated
probe task asking for exactly `HEALTHCHECK OK` and nothing else, same intent
as `scripts/opencode_probe.py` but with no script needed — it's just another
`task(agent="deepseek-worker", prompt="Reply with exactly HEALTHCHECK OK and
nothing else. Do not modify files.")` call. Do not infer exhausted
credit/billing from an error string alone; verify what `kilo auth` /
`kilo models` can actually prove first.

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

None. No ephemeral database files, no PID records, no log files to remove —
this entire maintenance category that OPENCODE.md requires does not exist
under native subagent delegation.

- **Roles:** discovery worker, implementer, verification-only worker,
  reviewer, resumed fixer, fresh re-reviewer, and phase-finding worker — all
  route to the same `deepseek-worker` subagent, distinguished only by the
  task-specific prompt built from `PROMPTS.md`, matching this skill's default
  policy of one worker profile for every role.

Default review budget is 5 substantive rounds; default immediate transport
budget is 5 launch attempts per role invocation, same as the OpenCode
profile. Execution is sequential. The main orchestrator performs
decomposition, plan-wide decisions, substantive escalation decisions, and
final phase approval — it is not a fallback worker when the `deepseek-worker`
subagent is unavailable.
