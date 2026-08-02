# DeepSeek and Destroy Configuration Example

This file is optional. Copy it, delete sections you do not need, and name it
however you prefer. Any omitted setting inherits `SKILL.md` defaults.

Do not put credentials here. Reference an existing harness profile or environment
variable instead.

## Agent profiles

### Profile: DeepSeek Worker

- Harness: OpenCode CLI
- Endpoint: existing OpenCode provider configuration
- Model: `opencode-go/deepseek-v4-flash`
- Reasoning level: default
- Fresh launch: use `opencode run --auto --model ... --dir ...`
- Resume: use `opencode run --auto --session ... --dir ...`
- Positive liveness: log/report growth or harness status proving model execution
- Safe stop: terminate only the uniquely identified run
- Suitable roles: implementer, reviewer, fixer, re-reviewer, phase worker

### Profile: Expensive Reviewer

- Harness: Codex
- Named agent/profile: Luna
- Reasoning level: maximum
- Endpoint/model: existing Codex profile
- Fresh launch: use the environment's normal Luna launch method
- Resume: only when reliable continuation is supported
- Suitable roles: difficult phase review and escalation

## Role routing

- Implementer: DeepSeek Worker
- Task reviewer: DeepSeek Worker in a fresh context
- Finding fixer: resume the reviewer that produced the findings
- Fresh re-reviewer: DeepSeek Worker in a different fresh context
- Phase-finding worker: DeepSeek Worker
- Main phase approver: current orchestrator
- Escalation agent: current orchestrator

## Role prompt additions

### Implementer

- Add project-specific implementation instructions here.

### Reviewer

- Add project-specific review priorities here.

### Resumed fixer

- Fix only the reported findings; do not silently widen scope.

### Phase reviewer

- Add cross-system, product, or domain concerns here.

## Planning rules

- Prefer the largest coherent task one worker can complete and verify.
- Keep product and architectural decisions with the main orchestrator.

## Implementation rules

- Follow the project's existing architecture and conventions.
- Reuse canonical systems before creating parallel implementations.

## Review rules

- Inspect actual changes and rerun real verification.
- Fail on unresolved task-relevant findings, not merely unrelated old defects.

## Optional domain lenses

Add only what is relevant. Examples:

### Video game project

- Review gameplay, progression, balance, narrative continuity, player agency,
  save compatibility, performance, and actual player experience.

### LLM or agentic system

- Review language independence, prompt/context contamination, context limits,
  session reuse, retry behavior, model variation, and accidental deterministic assumptions.

### Security-sensitive system

- Review trust boundaries, authorization, secrets, destructive operations,
  dependency risk, and failure recovery.

## Execution overrides

- Review-round budget: 5
- Transport-attempt budget: 5
- Startup-liveness grace: 90 seconds
- Default execution: sequential
- PASS: zero unresolved task-relevant findings
- Live/destructive/paid tests: require explicit authorization

## Project rule sources

- Read `AGENTS.md` when present.
- Read `CLAUDE.md` when present.
- Read the authoritative plan and the files it references.
- Additional implementation rules: <optional path>
- Additional review rules: <optional path>
