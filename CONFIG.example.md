# DeepSeek and Destroy Configuration Example

This file is optional. Copy it, delete sections you do not need, and change only
the settings relevant to your project. Omitted values inherit `SKILL.md`.

Do not place credentials here. Reference existing harness profiles or environment
variables.

## Agent profiles

### Profile: DeepSeek Worker

- Harness: OpenCode CLI
- Endpoint: existing OpenCode provider configuration
- Model: `opencode-go/deepseek-v4-flash`
- Reasoning level: default
- Fresh launch: use the OpenCode adapter in `OPENCODE.md`
- Resume: use the OpenCode adapter with the recorded worker DB/session
- Positive liveness: classify exact process existence + accumulated CPU + output growth; never output alone
- Health probe: verify exact id with `opencode models`, then require `HEALTHCHECK OK` in an isolated DB
- Safe stop: terminate only the uniquely identified run
- Suitable roles: phase surveyor, discovery, implementer, verification, reviewer, fixer, re-reviewer, recovery auditor, phase auditor, phase worker

### Profile: Backup Worker

- Harness: <Codex, Claude Code, OpenCode, or custom>
- Endpoint/model/profile: <existing configured profile>
- Reasoning level: <level>
- Fresh launch: <method>
- Resume: <method or unsupported>
- Positive liveness: <reliable harness-specific process/CPU/output or status signal>
- Health probe: <minimal authorized prompt and success predicate>
- Safe stop: <method>
- Suitable roles: equivalent fallback when the default worker is unavailable

### Profile: Expensive Specialist

- Harness: Codex
- Named agent/profile: Luna
- Reasoning level: maximum
- Suitable roles: difficult substantive escalation or specialized phase review
- Not suitable as: automatic fallback merely because a cheap endpoint is down

## Role routing

- Phase surveyor: DeepSeek Worker in a fresh read-only context
- Discovery worker: DeepSeek Worker
- Implementer: DeepSeek Worker
- Verification-only worker: DeepSeek Worker in a fresh context
- Task reviewer: DeepSeek Worker in a fresh context
- Finding fixer: resume the reviewer that produced the findings when its context remains healthy
- Fresh re-reviewer: DeepSeek Worker in a different fresh context
- Recovery auditor: DeepSeek Worker in a fresh read-only context
- Phase auditor: DeepSeek Worker in a fresh read-only context
- Phase-finding worker: DeepSeek Worker
- Substantive escalation worker: Expensive Specialist when a stronger worker is needed
- Equivalent worker-availability fallback: Backup Worker
- Main phase approver: current orchestrator

The main orchestrator is never an implicit worker-availability fallback.

## Role prompt additions

### Implementer

- Add project-specific implementation instructions here.

### Reviewer

- Add project-specific review priorities here.

### Resumed fixer

- Fix only reported findings; do not silently widen scope.

### Phase surveyor

- Measure current reality and cite evidence; do not implement or make product decisions.

### Recovery auditor

- Classify suspect changes and recommend disposition; do not modify the tree.

### Phase auditor

- Synthesize cross-system, product, and domain evidence; advise but never approve the phase.

## Planning rules

- Continue automatically through tasks and phases until the plan is complete or
  genuinely human-blocked.
- Count independently reviewable units before each spawn; default to one unit per task.
- Split discovery from construction and split distinct verification classes.
- Task size includes artifact size and discovery cost, not only code volume.
- Resolve ordinary ambiguity from the plan, documentation, and existing project.
- The orchestrator owns decisions and boundaries, not repository-scale investigation volume.
- Delegate state surveys, subsystem tracing, large measurements, recovery forensics,
  and phase evidence synthesis to cheap workers; judge their durable reports.
- Keep unresolved product and architecture decisions with the main orchestrator.

## Construction policy

- For decided multi-file extraction/migration/refactor work, require a durable
  construction brief with exact files, symbols, boundaries, wiring, exclusions,
  first edit, and verification.
- A first substantial zero-change analytical death triggers immediate re-scope or
  prescription; do not retry the same open-ended prompt.

## Implementation rules

- Follow the project's existing architecture and conventions.
- Reuse canonical systems before creating parallel implementations.

## Review rules

- Inspect actual changes and rerun real verification.
- Fail on unresolved task-relevant findings, not unrelated old defects.
- Log major findings and fixes with concise engineering rationale and evidence.
- State the measurement predicate before asserting counts, absence, or completeness.
- Surface and log material corrections, repair affected decisions, then continue.

## Optional domain lenses

### Video game project

- Review gameplay, progression, balance, narrative continuity, player agency,
  save compatibility, performance, and actual player experience.

### LLM or agentic system

- Review language independence, prompt/context contamination, context pressure,
  session reuse, retry behavior, model variance, and accidental deterministic assumptions.

### Security-sensitive system

- Review trust boundaries, authorization, secrets, destructive operations,
  dependency risk, and failure recovery.

## Execution overrides

- Review-round budget: 5
- Immediate transport-attempt budget: 5
- Startup-liveness grace: 90 seconds
- Ongoing-progress window: 10 minutes before a repeated multi-signal wedge assessment
- Resume launch retry: 1 exact retry after a short delay
- Provider re-probe interval: 5 minutes, increasing with bounded backoff
- Soft worker cap: warn/finalize before hard cap; graceful stop before kill
- Default execution: sequential
- PASS: zero unresolved task-relevant findings
- Live/destructive/paid tests: require explicit authorization
- Worker availability: `WAITING-FOR-WORKER`, health probe, bounded backoff, automatic relaunch, then equivalent fallback
- Persistent worker unavailability: human escalation with exact resume point
- Orchestrator substitution for unavailable workers: prohibited

## Project rule sources

- Read `AGENTS.md` when present.
- Read `CLAUDE.md` when present.
- Read the authoritative plan and every file it materially references.
- Additional architecture sources: <optional path>
- Additional implementation rules: <optional path>
- Additional review rules: <optional path>

## Orchestrator economy

- Task acceptance: use the fast path after an independent PASS with complete Decision Packet, passing verification, clean scope/preservation, and no conflicting evidence.
- Orchestrator technical spot checks: prohibited; every doubt becomes a fresh targeted worker assignment.
- Orchestrator project-file changes: prohibited; phase-gate findings become immutable remediation plans executed by workers.
- Phase-gate findings: write an immutable remediation plan and execute it entirely through worker implementation, verification, repair, and fresh review loops.
- Conflicting worker evidence: assign a fresh clean-context worker to adjudicate the exact predicate; the orchestrator does not inspect the implementation.
- Orchestrator test execution: prohibited; all verification runs belong to Verification Workers.
- Task-specific prompt envelope: normally <= 1,200 words excluding Common Rules; reference durable briefs rather than inlining them.
- Task-specific reviewer risks: maximum 3 concise hypotheses beyond the standard reviewer contract.
- Resume behavior: use HANDOVER/state/Decision Packets and authority hashes; reread only changed or decision-critical sources.
- User-facing updates: sparse; one-line routine status, fuller messages only for material correction, blocker, phase completion, or final completion.
