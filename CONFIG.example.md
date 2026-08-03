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
- Positive liveness: actual OpenCode process accumulated CPU time advances; do not use redirected log growth
- Safe stop: terminate only the uniquely identified run
- Suitable roles: implementer, reviewer, fixer, re-reviewer, phase worker

### Profile: Backup Worker

- Harness: <Codex, Claude Code, OpenCode, or custom>
- Endpoint/model/profile: <existing configured profile>
- Reasoning level: <level>
- Fresh launch: <method>
- Resume: <method or unsupported>
- Positive liveness: <reliable harness-specific signal; avoid buffered-output assumptions>
- Safe stop: <method>
- Suitable roles: equivalent fallback when the default worker is unavailable

### Profile: Expensive Specialist

- Harness: Codex
- Named agent/profile: Luna
- Reasoning level: maximum
- Suitable roles: difficult substantive escalation or specialized phase review
- Not suitable as: automatic fallback merely because a cheap endpoint is down

## Role routing

- Implementer: DeepSeek Worker
- Task reviewer: DeepSeek Worker in a fresh context
- Finding fixer: resume the reviewer that produced the findings
- Fresh re-reviewer: DeepSeek Worker in a different fresh context
- Phase-finding worker: DeepSeek Worker
- Substantive escalation worker: Expensive Specialist when needed
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

### Phase reviewer

- Add cross-system, product, or domain concerns here.

## Planning rules

- Continue automatically through tasks and phases until the plan is complete or
  genuinely human-blocked.
- Prefer the largest coherent task one worker can complete and verify.
- Split a task before launch when it plausibly exceeds about 30 minutes of tool-heavy work or contains natural independent units.
- Resolve ordinary ambiguity from the plan, documentation, and existing project.
- Keep unresolved product and architecture decisions with the main orchestrator.

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
- Default execution: sequential
- PASS: zero unresolved task-relevant findings
- Live/destructive/paid tests: require explicit authorization
- Worker availability: bounded wait/backoff, retry, then equivalent fallback
- Persistent worker unavailability: human escalation with exact resume point
- Orchestrator substitution for unavailable workers: prohibited

## Project rule sources

- Read `AGENTS.md` when present.
- Read `CLAUDE.md` when present.
- Read the authoritative plan and every file it materially references.
- Additional architecture sources: <optional path>
- Additional implementation rules: <optional path>
- Additional review rules: <optional path>
