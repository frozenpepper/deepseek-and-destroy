# DeepSeek and Destroy

> **Feed it a plan. It keeps spawning, reviewing, fixing, and moving forward until the plan is actually done.**

DeepSeek and Destroy is a portable coding-agent skill for executing large,
multi-phase implementation plans without turning the main orchestrator into an
overworked implementation mule.

The main orchestrator keeps the complete project picture:

- what the plan is trying to achieve;
- how the phases depend on each other;
- what the project’s architecture and ethos require;
- when a decision is genuinely high level;
- whether a phase is really ready to pass.

Worker agents do most of the expensive-volume work:

- current-state surveys;
- subsystem discovery and call-path tracing;
- implementation;
- verification and large-artifact analysis;
- independent review;
- repair and fresh re-review;
- reportless-worker recovery audits;
- phase evidence synthesis.

The default workers use DeepSeek V4 Flash through OpenCode because it is capable,
fast, and cheap enough to throw at repeated implementation/review loops without
hearing your wallet scream. DeepSeek is the default, not a requirement.

---

## The rule that matters most

Once you give DeepSeek and Destroy an authoritative plan, it is expected to
**execute the plan**, not explain what it might do and wait for you to keep saying
“continue.”

It should keep moving through:

```text
task → review → fix → fresh review → next task → phase gate → next phase
```

until one of four things happens:

1. the entire plan and its delivery artifacts are complete;
2. a genuinely human-level blocker is reached;
3. you explicitly pause it;
4. you abandon the run.

A task finishing is not a reason to stop.  
A phase finishing is not a reason to stop.  
A test failing is not a reason to stop.  
A reviewer finding problems is definitely not a reason to stop—that is literally
why the reviewer is there.

A context window ending is also not plan completion. The skill stores an exact
`next_action` so the next orchestrator session continues the run rather than
performing a dramatic reading of the previous session’s accomplishments.

---

## What the loop does

For each bounded task:

```text
Fresh IMPLEMENTER
        │
        ▼
Fresh REVIEWER
   │         │
 PASS      FAIL
   │         │
   │         ▼
   │   Resume that reviewer
   │   to fix its own findings
   │         │
   │         ▼
   │   Fresh REVIEWER checks
   │   the repaired result
   │         │
   └─────────┴──────► task accepted
```

The useful twist is the repair step:

- the reviewer that investigated the problem keeps its evidence and context;
- that reviewer is resumed to repair the exact findings;
- a different fresh reviewer validates the result.

After all tasks in a phase pass, verification workers run the substantial phase
checks and a fresh phase auditor synthesizes the evidence. The main orchestrator
performs the hard gate: integration, architecture, cross-task effects, domain
impact, plan fidelity, and final approval.

Cheap workers survey the site, turn the wrenches, run the machinery, inspect the
wreckage, and prepare the evidence. The orchestrator remains the architect,
foreman, and final inspector.


If the final inspector finds a problem, it does not grab a wrench. It writes a
small phase-remediation plan, sends the investigation and fixes back through the
worker loops, commissions fresh verification and a fresh phase audit, then repeats
the gate. Doubt always creates another worker assignment; it never creates a
second implementation job for the orchestrator.

---

## Decisions stay expensive; investigation stays cheap

The orchestrator owns the whole-plan decisions. It does **not** need to personally
perform every repository scan, call-graph trace, hash comparison, five-megabyte
artifact audit, browser battery, or full test suite.

The default division is:

```text
Main orchestrator:
understand → decide → route → judge → approve

Cheap workers:
survey → discover → implement → verify → review → fix → recover → audit

Helpers:
hash → compare → monitor → validate state → health probe
```

That means a richer implementation prompt should normally come from a durable
worker-produced survey or discovery brief—not from Opus spending half its context
rediscovering the repository before DeepSeek even starts.

The main orchestrator still understands the governing plan and project authority,
resolves plan-wide contradictions, chooses task boundaries, decides whether
findings are material, and owns every phase gate. On resume it uses hashes, the
handover, and Decision Packets rather than rereading an unchanged documentation
corpus. When technical evidence conflicts, it sends the exact question to a fresh
worker in a clean context; it does not inspect or verify the implementation itself.

---

## It does not ask humans to do the orchestrator’s homework

On a new run, the orchestrator reads the authoritative plan and governing project
instructions. It records hashes and compact summaries. On resume, it starts from
the handover, state, plan reference, and Decision Packets, then rereads only
changed or decision-critical sources instead of paying again for the entire
history.

It should resolve ordinary ambiguity from those sources and make decisions that
fit the project’s scope, architecture, ethos, and the spirit of the plan.

It should not interrupt you for routine implementation choices, failing tests,
task re-scoping, or the obvious next phase.

Human escalation is reserved for things such as:

- contradictory requirements with materially different outcomes;
- a real missing product or architecture decision;
- required credentials, access, devices, files, or external environments;
- destructive/live/paid actions needing authorization;
- worker quota or credits being exhausted;
- a persistent provider outage;
- unsafe concurrent work that cannot be isolated;
- a plan that is genuinely impossible or materially incomplete.

---

## The orchestrator is not paid twice for the same review

A fresh reviewer PASS is supposed to save premium-model work, not trigger another
full review by the orchestrator.

The default fast path is:

```text
independent reviewer PASS
+ verification reports PASS
+ scope/preservation clean
+ no conflicting evidence
= accept task and continue
```

The orchestrator does not reread the code, rerun the suite, reparse the artifact,
or rederive counts. When evidence conflicts, it records the exact disputed
predicate and sends a fresh cheap worker to review, verify, discover, or adjudicate
it. If that worker finds a defect, the normal repair and fresh re-review loop runs
again until the evidence is clear.

Worker reports begin with a compact **Decision Packet**, so the orchestrator can
make normal routing and acceptance decisions without loading the full forensic
record. The helper `scripts/decision_packet.py` extracts that section.

The same economy applies to chat. Routine worker transitions get a short status,
not several paragraphs repeating the report. Detailed reasoning lives in the run
folder; humans hear about material corrections, blockers, major plan decisions,
phase completion, and final completion.


### Doubt means “spawn,” not “inspect”

The orchestrator is expected to rely on the workers. When a result feels doubtful,
it does not open the code and start a second review. It launches a fresh worker
with a clean context and one exact question. Missing test evidence goes to a
Verification Worker. A questionable implementation goes to a fresh Reviewer.
Architecture uncertainty goes to Discovery. Conflicting reports get a targeted
independent adjudication.

If the new worker finds a problem, that problem enters the same repair → fresh
review loop. The orchestrator keeps routing until the evidence is clear.

---

## Broken workers do not turn the orchestrator into a worker

This is explicit because several orchestrators apparently needed the emotional
support.

When a worker endpoint has connection problems, rate limits, an outage,
authentication failure, or no remaining credit, the main orchestrator must not
say:

> “Fine, I’ll just implement and review everything myself.”

Instead it must:

1. preserve the exact run state;
2. decide whether the failure is plausibly temporary;
3. wait/back off and retry when reasonable;
4. use an equivalent configured fallback worker when available;
5. escalate to the human when external action is required.

Worker availability problems are plumbing problems, not permission to destroy the
cost model and independent-review model.

The orchestrator does not intervene directly in implementation or review. Repeated
worker difficulty triggers re-scoping, discovery, a cleaner prompt, a stronger
configured worker, or a precise human escalation—not an expensive-model takeover.

---

## Multiple orchestrators are supported

Every execution owns a separate run:

```text
DeepSeekAndDestroy/
└── plans/
    └── <plan-id>/
        └── runs/
            └── <run-id>/
```

Each run keeps its own:

- manifest and owner;
- plan reference and immutable plan snapshots;
- state and exact next action;
- configuration;
- worker logs and reports;
- major findings/fixes log;
- defect ledger;
- phase and task artifacts.

Separate run folders protect orchestration history. They do **not** magically
protect source files. Two orchestrators that may edit the same files need
separate Git worktrees/branches or explicitly non-overlapping scopes.

See `WORKSPACE.md` for the complete contract.

---

## Major engineering findings are not allowed to evaporate

Every run contains:

```text
major-findings-and-fixes.md
```

It records the important stuff future agents should not have to rediscover:

- serious defects and regressions;
- non-obvious root causes;
- consequential architecture or contract decisions;
- major fixes and why they were chosen;
- rejected alternatives when they matter;
- verification and remaining risks;
- worker availability incidents;
- orchestrator phase-gate decisions, remediation plans, and human escalations.

It is not a transcript and not hidden chain-of-thought. It is a concise,
evidence-linked engineering record.

---

## Default setup: no configuration required

Out of the box:

- **Worker harness:** OpenCode CLI
- **Worker model:** `opencode-go/deepseek-v4-flash`
- **Endpoint:** your existing OpenCode provider configuration
- **Execution:** sequential
- **Review rounds:** 5 before orchestrator reassessment
- **Immediate transport attempts:** 5 per invocation
- **Startup liveness grace:** 90 seconds
- **Main phase approver:** the orchestrator that loaded the skill

The default OpenCode adapter uses isolated disposable databases for workers so
hundreds of short-lived sessions do not inflate the normal OpenCode history
database into a small moon.

See `OPENCODE.md`.

A Kilo Code profile is also available: workers run as a native Kilo subagent
instead of a spawned process, so there is no database or PID to manage at
all. See `KILOCODE.md` and the Kilo example profile in `CONFIG.example.md`.

---

## Install

Copy the complete folder into the skills directory used by your harness:

```text
deepseek-and-destroy/
├── SKILL.md
├── README.md
├── WORKSPACE.md
├── PROMPTS.md
├── HARNESS.md
├── COMPACTION.md
├── CODEX.md
├── CLAUDE.md
├── OPENCODE.md
├── KILOCODE.md
├── CONFIG.example.md
├── CHANGELOG.md
├── adapters/
│   ├── codex/
│   ├── claude/
│   ├── opencode/
│   └── kilo/
│       └── agents/
│           ├── dsd-mutating-worker.md
│           └── dsd-readonly-worker.md
└── scripts/
    ├── check_state.py
    ├── context_checkpoint.py
    ├── detect_harness.py
    ├── install_compaction_adapter.py
    ├── install_kilo_agents.py
    ├── decision_packet.py
    ├── opencode_probe.py
    └── scope_snapshot.py
```

`SKILL.md` is the core mission and orchestration policy.

The companion files keep the core readable:

- `WORKSPACE.md` — state, plans, concurrency, logging;
- `PROMPTS.md` — exact implementer/reviewer/fixer prompts;
- `HARNESS.md` and `COMPACTION.md` — orchestrator harness selection and durable context checkpoints;
- `CODEX.md`, `CLAUDE.md`, and `OPENCODE.md` — harness-specific adapters;
- `KILOCODE.md` — Kilo Code worker adapter (native subagent delegation) and
  experimental orchestrator compaction plugin;
- `adapters/kilo/agents/` — role-separated Kilo subagent templates (implementer
  and read-only), installed by `scripts/install_kilo_agents.py`;
- `CONFIG.example.md` — optional model, routing, project, and checkpoint rules;
- `scripts/check_state.py` — optional Stop-hook/state invariant checker;
- `scripts/context_checkpoint.py` — immutable checkpoint and rehydration helper;
- `scripts/detect_harness.py` and `install_compaction_adapter.py` — adapter selection and project-local installation;
- `scripts/install_kilo_agents.py` — resolves the effective worker model and
  installs the Kilo subagents;
- `scripts/opencode_probe.py` — isolated exact-model health probe;
- `scripts/scope_snapshot.py` — mechanical content-hash baseline and comparison.

---

## Quick start

```text
Use DeepSeek and Destroy to execute the authoritative plan at
DOCS/Plans/implementation-plan.md.

Continue autonomously until the complete plan is finished or a genuine
human-level blocker is reached. Complete all work that does not require an
authorized live test before preparing the final live-test gate.
```

That is enough when the defaults fit.

A useful activation prompt may also specify delivery requirements:

```text
Use DeepSeek and Destroy to execute PLAN.md.

Keep the project package, plan-progress record, and standalone handover updated.
Do not stop after individual tasks or phases. Escalate only for major human
decisions, unavailable access/authorization, or unresolved worker availability.
```

---

## Optional configuration

Use `CONFIG.example.md` to change only what you need:

- harnesses, endpoints, models, named agents, and reasoning levels;
- role routing, including phase surveyors, discovery workers, verification-only
  workers, recovery auditors, and phase auditors;
- fresh-launch and resume methods;
- equivalent fallback workers;
- project-specific implementation/review rules;
- game, narrative, LLM, security, UX, or other domain review lenses;
- budgets, liveness, and live-test policy;
- additional rule and guide paths.

Configuration is a partial Markdown override, not a brittle schema. Missing
settings keep the defaults.

You may attach it, name it explicitly, or keep one project-local file named:

```text
.deepseek-and-destroy.md
deepseek-and-destroy.config.md
DSD_CONFIG.md
```

Do not put credentials in it.

---

## Configuration priority

1. explicit current user instructions;
2. explicitly attached or named configuration;
3. one unambiguous project-local configuration;
4. sibling `CONFIG.md` when available;
5. built-in defaults.

Before every spawn, the orchestrator resolves the exact worker profile and rules
for that role and places them directly in the prompt. Workers do not inherit
configuration through spiritual osmosis.

The main orchestrator is **not** an implicit fallback worker.

---

## Reliability lessons already paid for in blood

### A PID is not proof of intelligent life

The liveness check is harness-specific. For OpenCode, redirected stdout may be
block-buffered, so bytes alone prove nothing. The adapter combines the exact
process identity, elapsed time, accumulated CPU, and output growth: dead, slow,
and wedged workers are different states. It also avoids `pgrep -f` self-matches.

### Transport failure is not a review finding

Dead launches, flaky connections, malformed reports, and provider problems use a
separate availability path and do not burn substantive review rounds.

### Refactors preserve accepted behavior

Previously accepted outputs/contracts can be captured as immutable preservation
evidence. Agents may not “fix” a mismatch by updating the expected evidence.

### Timestamps are liars

Scope and preservation use content diffs or hashes, never modification time alone.

### Old defects stay in their own lane

A pre-existing unrelated bug goes into the defect ledger. It is not silently
smuggled into the current task or repeatedly used to fail it.

### Intended work is not a running worker

State distinguishes `prepared`, `launching`, and `in-progress`. A task cannot be
called in progress unless a real attempt exists and either its worker is live or
a complete report proves it ran. This catches the classic “updated state, forgot
to launch” failure immediately.

### One independently reviewable unit per worker

Before spawning, the orchestrator lists the units. One behavioral change plus its
direct tests can be one unit. A validator, wiring, fixture migration, generated
client, artifact audit, browser battery, and full-suite run are separate when each
can be reviewed alone. More than one unit means split.

### Discovery writes a spec before construction

Unfamiliar subsystem? First send an explorer to produce a cited, durable spec and
stop. If the result compresses cleanly, a fresh implementer gets the brief. If it
does not, resume the explorer for a narrowly bounded build turn. Either way, the
reviewer is fresh. Session memory is useful; a file is durable.

### The orchestrator does not become the explorer

Before phase decomposition, a cheap Phase Surveyor measures what exists, what is
wired, what is merely present, and what partial work already exists. Reportless
worker damage goes to a Recovery Auditor. Large phase evidence goes to a Phase
Auditor. The orchestrator decides from those artifacts instead of personally
absorbing their repository-scale workload.

### Reports are written while the worker is still alive

Workers create reports/specs early and append. A dying session can still leave
usable findings. The watchdog waits for process exit before judging final artifacts;
a report file appearing is only a checkpoint.

### Dead workers may leave live damage

A reportless worker exit makes the tree suspect. Hashes and content diffs are
reconciled before any retry or next task. “No report” never means “no edits.”

### Verification can be its own worker

Large artifact analysis, browser runs, mutation testing, and long full suites are
first-class verification-only units. They do not need to consume the same context
as code review.

### Old prompts can point at dead places

Retries audit rules, criteria, commands, **and every path**. A prompt that still
writes to yesterday's run folder is not a valid prompt.

### Counts need a predicate

Before claiming “there are 17,” “none exist,” or “all callers are covered,” the
agent states what it searched and what counted. Contradictory worker evidence
triggers a fresh, wider derivation—not a defence of the old number.

### Being autonomous does not mean pretending you were right

A material correction is surfaced, logged, and used to repair affected decisions.
Then execution continues; the correction is not an excuse to stop the run.

### Fresh review means fresh review

When independence is lost, the skill records it honestly instead of putting a
fake moustache on self-review and calling it peer validation.

---

### Provider trouble gets a health probe, not five giant retries

A minimal `HEALTHCHECK OK` probe separates a broken task from a broken endpoint.
The exact model id comes from the harness's model listing, not memory. Transient
outages enter `WAITING-FOR-WORKER`, re-probe on backoff, and relaunch automatically
or use a configured healthy fallback.

### “Launching next” is not launching next

An active orchestrator turn may end only with a live worker, an active persisted
wait/probe, or a legitimate terminal state. Future tense is not a process.

---

## Prescribe large mechanical refactors

Cheap workers are excellent executors, but a large extraction or migration can
burn an entire context rediscovering a design that was already decided. For that
kind of work, DeepSeek and Destroy uses **prescription over instruction**:

- a Surveyor or Discovery Worker writes a durable construction brief;
- the brief names exact files, symbols, moves, wiring, exclusions, and first edit;
- the implementer verifies local assumptions and starts writing instead of
  reopening the architecture question.

A first long attempt that analyses heavily and changes nothing is treated as a
scoping signal. The same vague prompt is not launched again.

Scope baselines are rolling per-attempt snapshots of the immediately previous
accepted tree. They are refreshed after accepted changes; immutable behavior
preservation evidence is not.

## Frequently asked questions

### Do I have to use DeepSeek?

No. It inspired the name and is the default worker. Every role can be routed to
another harness or model.

### Does it work without a configuration file?

Yes. The built-in OpenCode + DeepSeek profile is complete.

### Does it stop after every phase?

It should not. Phase completion causes the next phase to start immediately.

### When should it ask me something?

Only when the human escalation gate is met: a major unresolved decision,
authorization/access requirement, persistent worker availability problem, or
another blocker that project authority cannot solve.

### What if DeepSeek runs out of credit?

The orchestrator preserves state and either retries later, uses a configured
equivalent fallback, or asks you to restore worker capacity. It does not suddenly
become the implementation workforce.

### Can multiple orchestrators run it?

Yes, using unique run folders and source-code isolation where scopes overlap.

### Can it survive a crashed session?

That is one of the main points. The run stores its plan snapshot, state, evidence,
and exact next action.

### Is it fully autonomous?

Within the authority granted by the plan and project documentation, yes. It will
not invent missing product decisions, supply credentials, authorize destructive
operations, or pretend an unavailable external service works.

---

## The philosophy in one paragraph

Use the strongest expensive model for whole-plan decisions, routing, conflict
resolution, and phase approval. Use capable inexpensive workers for surveys,
discovery, implementation, verification, review, repair, recovery forensics, and
evidence synthesis. Use small helpers for mechanical state, hashing, liveness, and
health checks. Preserve evidence, decisions, and recovery state. Keep moving
without demanding ceremonial “continue” prompts. Stop only when the plan is
actually complete or the remaining problem genuinely belongs to a human.

## Long runs do not have to trust amnesia

DeepSeek and Destroy can outlive a healthy orchestrator context window. The skill
therefore uses an external **Context Checkpoint Protocol** rather than hoping the
harness's automatic summary remembers every important user instruction, project
quirk, active worker, and exact next action.

The default policy is:

- checkpoint at 65% when context use is measurable;
- compact at the next safe orchestration boundary, normally before 75%;
- begin no new substantial phase-level reasoning at 80%;
- when percentage is unavailable, rely on native hooks plus periodic checkpoints.

The important optimization is that the orchestrator does not write a giant new
handover from memory each time. `HANDOVER.md` stays small and is maintained
incrementally. A helper snapshots it together with `state.json`, the plan
reference, and the authority index. After compaction, the skill reloads those
files, verifies live state, and immediately continues from `next_action`.

The skill detects whether the main orchestrator is Codex, Claude Code, OpenCode,
or an unknown/custom harness and installs the strongest project-local adapter:

```bash
python3 <skill-root>/scripts/install_compaction_adapter.py \
  --harness auto \
  --project-root <project-root>
```

See `HARNESS.md`, `COMPACTION.md`, and the selected harness adapter for details.
---

## License

DeepSeek and Destroy is released under the [MIT License](LICENSE). Use it,
modify it, fork it, redistribute it, bundle it into commercial tools, or sell
services built around it. Keep the copyright and license notice with copies or
substantial portions of the software.

