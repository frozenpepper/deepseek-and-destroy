# DeepSeek and Destroy

> **Feed it a plan. Let the workers implement, review, fix, and repeat until the code survives.**

DeepSeek and Destroy is a portable coding-agent skill for executing large,
multi-phase implementation plans without making the main orchestrator personally
do every file edit, test run, review pass, and repair.

The basic idea is simple:

- the **main orchestrator** reads the whole plan, makes the important decisions,
  decomposes the work, handles escalation, and approves complete phases;
- capable, inexpensive **worker agents** perform most of the implementation,
  verification, review, and repair work;
- every repair is checked by fresh eyes before the task is accepted;
- progress is written to disk so a crashed or compacted session can resume instead
  of reenacting the first half of *Memento*.

Despite the name, DeepSeek is the default worker—not a requirement. The worker
harness, endpoint, model, role routing, and project-specific rules can all be
overridden with an optional Markdown configuration file.

---

## What actually happens

For every bounded task, the skill runs this loop:

```text
                         ┌──────────────────────────┐
                         │   Main orchestrator      │
                         │ reads + decomposes plan  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │ Fresh IMPLEMENTER        │
                         │ changes code + verifies  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │ Fresh REVIEWER           │
                         │ inspects actual work     │
                         └───────┬──────────┬───────┘
                                 │ PASS     │ FAIL
                                 │          ▼
                                 │   Resume that reviewer
                                 │   to fix its own findings
                                 │          │
                                 │          ▼
                                 │   Fresh REVIEWER checks
                                 │   the repaired result
                                 │          │
                                 └──────────┴───────────────┐
                                                            ▼
                                               Task accepted only when
                                               no relevant findings remain
```

When every task in a phase passes, the main orchestrator performs a broader
**phase-level hard gate**. This is where cross-task integration, architecture,
plan fidelity, and the full phase verification are judged.

In other words: cheap workers turn the wrenches; the expensive model remains the
architect, foreman, and final inspector.

---

## Why use it?

Large plans are awkward for a single coding-agent context. The model that
understands the whole project gradually fills its context with terminal output,
file contents, test logs, repair attempts, and seventeen slightly different
versions of the same stack trace.

DeepSeek and Destroy keeps that main context focused on high-value reasoning by
pushing bounded work into disposable or resumable worker sessions.

It is useful when:

- a plan contains several ordered phases or many implementation steps;
- each step needs real verification rather than a confident “looks good”;
- independent review matters;
- the work may outlive one context window or one uninterrupted session;
- you want strict phase gates without paying premium-model prices for every
  mechanical implementation pass;
- you are tired of asking, “Did the agent actually run the tests, or did it just
  develop a strong emotional belief that they would pass?”

It is probably unnecessary for a two-line typo fix, a tiny isolated script, or a
task whose entire plan is “rename this button.”

---

## Default setup: zero configuration required

Out of the box, the skill uses:

- **Worker harness:** OpenCode CLI
- **Worker model:** `opencode-go/deepseek-v4-flash`
- **Endpoint:** whatever provider is already configured in OpenCode
- **Worker roles:** implementation, review, repair, fresh re-review, and
  phase-finding repair
- **Main phase approver:** the orchestrator that loaded the skill
- **Execution:** sequential by default
- **Review budget:** 5 substantive rounds
- **Transport retry budget:** 5 attempts per invocation

You do **not** need to provide a configuration file when this setup matches your
environment.

You only need:

1. OpenCode installed and available to the orchestrator;
2. access to `opencode-go/deepseek-v4-flash` through your OpenCode provider
   configuration; and
3. a real implementation plan with enough detail to decompose and verify.

The skill can itself be loaded by Codex, Claude Code, OpenCode, or another capable
coding harness. Without an override, those orchestrators still launch the workers
through OpenCode—that is intentional.

---

## Install

Copy the whole folder into the skills directory used by your harness:

```text
deepseek-and-destroy/
├── SKILL.md
├── README.md
└── CONFIG.example.md
```

Exact skill-directory locations differ between harnesses and user setups. Use the
same location where your other working skills live.

`SKILL.md` is the actual skill. `README.md` is this guide.
`CONFIG.example.md` is optional and exists to be copied and edited—not worshipped
as sacred YAML.

---

## Quick start

Give the orchestrator the skill, the authoritative plan path, and any delivery or
live-testing constraints that matter:

```text
Use DeepSeek and Destroy to execute the authoritative plan at
DOCS/Plans/implementation-plan.md.

Complete all work that does not require live testing first. Preserve the plan's
phase gates and produce the requested package and handover artifacts.
```

That is enough when the defaults fit.

A good plan should make clear:

- what each phase is supposed to achieve;
- important contracts and behavior that must remain compatible;
- acceptance criteria;
- verification commands or observable evidence;
- which tests require live services, payment, destructive actions, or your local
  environment.

The skill can resolve ordinary implementation details from the repository. It
should not invent missing product decisions or silently rewrite the plan's intent.

---

## Optional configuration

Configuration is deliberately external so the core skill stays readable and the
same installed copy can serve different projects and harnesses.

Start from `CONFIG.example.md`, delete everything you do not need, and change only
the parts you care about.

You can override things such as:

- worker harnesses, endpoints, models, named agents, and reasoning levels;
- which profile performs each role;
- how fresh and resumed sessions are launched;
- role-specific prompt additions;
- planning, implementation, and review rules;
- domain review lenses for games, narrative systems, LLM pipelines, security,
  UX, accessibility, or other specialized projects;
- liveness grace periods, retry budgets, and live-test policy;
- project-local rule and guide files that workers must read.

Example first prompt:

```text
Use DeepSeek and Destroy to execute PLAN.md.
Use the attached DSD_CONFIG.md as the external configuration.
```

A project can also keep one unambiguous configuration file named:

```text
.deepseek-and-destroy.md
deepseek-and-destroy.config.md
DSD_CONFIG.md
```

Configuration is a **partial override**. Missing values continue using the built-in
defaults. You do not need to reproduce the entire example just to change one
reviewer model.

Do not place API keys or tokens in the file. Reference an existing harness
profile, provider configuration, or environment variable instead.

### Configuration priority

When several instruction sources exist, the skill resolves them in this order:

1. explicit instructions in the current user prompt;
2. a configuration file explicitly attached or named by the user;
3. one unambiguous project-local configuration file;
4. a sibling `CONFIG.md`, when the harness exposes it;
5. the defaults in `SKILL.md`.

Before launching any worker, the orchestrator must resolve the profile and rules
for that exact role and place the relevant instructions directly into its prompt.
Workers do not inherit configuration telepathically.

The effective, secret-free result is recorded under:

```text
.plan-execution/effective-configuration.md
```

If a worker launches with the wrong model, endpoint, profile, session mode, or
required rule set, that run is rejected rather than quietly treated as valid.

---

## The `.plan-execution/` workspace

The skill maintains a durable workspace inside the project:

```text
.plan-execution/
├── state.json
├── effective-configuration.md
├── out-of-scope-defects.md
└── <phase-id>/
    └── <task-id>/
        ├── task.md
        ├── implementer-report.md
        ├── review-1.md
        ├── fix-1.md
        ├── review-2.md
        ├── run logs...
        └── verdict.json
```

This is not decorative paperwork. It allows a new or compacted orchestrator
session to determine whether it should:

- launch an implementer;
- review completed work;
- resume a reviewer to repair its findings;
- run a fresh re-review;
- complete a phase gate; or
- recognize that the plan is already finished.

The result is resumable execution without depending on one chat session remembering
every detail forever.

---

## Reliability lessons already paid for in blood

The workflow includes several protections learned from long real-world runs:

### A process existing does not mean a worker started

After launch, the orchestrator looks for positive worker-level liveness—such as
log growth, report growth, or reliable harness status—before waiting through a
long timeout. A silent wrapper process is not proof of life.

### Broken transport is not broken code

Dead launches, flaky connections, hung wrappers, and malformed reports use a
separate retry budget. They do not consume substantive review rounds and do not
force the expensive orchestrator to take over merely because the plumbing had a
bad afternoon.

### Refactors must preserve accepted behavior

When a task refactors previously accepted work, the orchestrator captures relevant
pre-change evidence and gives it to the implementer as a preservation gate. The
agent may not “fix” a mismatch by updating the expected evidence.

### Timestamps are liars

Scope verification uses version-control diffs or content hashes. A regenerated but
identical file is not treated as changed merely because its modification time had
an exciting day.

### Unrelated defects get recorded, not smuggled into scope

A real pre-existing bug discovered during a bounded task is written to the defect
ledger. Reviewers are told about it, fixers may not silently widen the task to
repair it, and the main orchestrator decides what to do with it at the phase gate.

### Fresh review means fresh review

If escalation forces the main orchestrator to validate its own repair, the loss of
independence is recorded. Self-validation is never dressed up later as peer review
wearing a fake moustache.

---

## Project-specific rules

DeepSeek and Destroy does not replace repository instructions. It must still read
and respect applicable files such as:

- `AGENTS.md`;
- `CLAUDE.md`;
- the authoritative plan;
- architecture documents and handovers referenced by the plan;
- project-specific implementation, review, or domain guides.

The optional configuration can point to additional rule sources or add concise
role-specific instructions.

This is particularly useful when a reviewer needs more than generic code quality.
For example:

- a game reviewer may need to examine gameplay, progression, balance, narrative
  continuity, save compatibility, and player experience;
- an LLM-system reviewer may need to examine prompt contamination, language
  independence, context pressure, retry behavior, and model variance;
- a security reviewer may need to examine trust boundaries, authorization,
  destructive operations, and recovery behavior.

Those details belong in the project or external configuration, not permanently in
every installation of the core skill.

---

## Frequently asked questions

### Do I have to use DeepSeek?

No. It is the cheap and capable default that inspired the name. Configure another
model or harness for any role—or all of them.

### Do I need a configuration file?

No. The built-in OpenCode + DeepSeek Flash profile is complete.

### Does the main orchestrator still review the work?

Yes. Workers handle task-level implementation and review loops. The main
orchestrator retains decomposition, architectural judgment, escalation, and every
major phase approval.

### Why does the reviewer fix its own findings?

Because that reviewer has already gathered the relevant evidence and code context.
It is resumed for efficient repair, but a different fresh reviewer must validate
the result so the fixer never grades its own homework.

### Why not let one agent do everything?

You can. Eventually its context may resemble an attic after a tornado. This skill
keeps the broad plan in one place while sending bounded work to focused contexts.

### Is it fully autonomous?

It can execute substantial plans without constant supervision, but it deliberately
stops for unresolved product decisions, unsafe or destructive actions, paid/live
tests requiring authorization, and failures that exhaust the configured budgets.

### Does it cheat tests to get a green checkmark?

It is explicitly instructed not to weaken, skip, delete, rewrite, or special-case
tests to manufacture a pass. Verification is evidence, not an obstacle course to
be quietly demolished.

### Can it survive a crashed session?

That is one of its main purposes. `state.json` and the task artifacts define the
resume point.

---

## Files in this folder

### `SKILL.md`

The complete orchestration contract, workflow, worker prompts, recovery protocol,
quality gates, and built-in defaults.

### `CONFIG.example.md`

An optional, human-editable example for changing agents, role routing, prompts,
rules, domain lenses, and execution policy.

### `README.md`

The friendly tour. You are currently inside it. Please keep your hands and feet
within the Markdown until the ride has stopped.

---

## The philosophy in one paragraph

Use powerful orchestration where broad context and judgment matter. Use cheap,
capable workers for bounded implementation and verification. Preserve independent
review. Resume contexts when retained evidence is valuable. Write progress to
disk. Treat real tests and artifacts as evidence. Escalate honestly when the loop
cannot converge.

Or, less formally:

> **Make the cheap model do the work. Wake the expensive model for the important decisions. Destroy the plan—constructively.**
