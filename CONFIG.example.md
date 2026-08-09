# DeepSeek and Destroy Configuration Example

Optional partial overrides. Omitted values keep `SKILL.md` defaults. Never place
credentials here.

## Default worker

- Harness: OpenCode CLI
- Model: `opencode-go/deepseek-v4-flash`
- Storage: one disposable external run-level OpenCode DB (see `OPENCODE.md`)
- Execution: sequential
- Fresh implementer/reviewer contexts: yes
- Reviewer→fixer resume: same run DB + recorded session when healthy
- Equivalent availability fallback: <optional profile>

## Kilo alternative

- Mutating agent: `dsd-mutating-worker`
- Read-only agent: `dsd-readonly-worker`
- Install: `python3 <skill-root>/scripts/install_kilo_agents.py --project-root <project-root>`
- Default model: `deepseek/deepseek-v4-flash` (validated by installer)

## Role routing

- Phase surveyor: default worker, read-only
- Discovery: default worker, read-only
- Implementer: default worker, mutating
- Verification: default worker, read-only
- Reviewer/re-reviewer: default worker, read-only and fresh
- Fixer: resume reviewer when useful/healthy; fresh fixer after heavy review
- Recovery auditor: default worker, fresh/read-only
- Phase auditor: default worker, fresh/read-only
- Main phase approver: current orchestrator

The main orchestrator is never an implicit fallback worker.

## Worker proof contract

- Stable AC IDs: required for meaningful criteria
- Proof Obligations: required for non-trivial behavioral criteria
- Counterexample-first review: enabled
- Proof patterns: attach only when relevant (`NEGATIVE-GATE`, `CARDINALITY`,
  `IDENTITY`, `DURABILITY`, `DERIVED-EVIDENCE`)
- Fast path: requires complete PASS Proof Matrix + no task-relevant defects +
  structural review-contract validation

## Execution

- Review rounds: 5
- Immediate transport attempts: 5
- Startup liveness grace: 90 seconds
- Default execution: sequential
- PASS standard: zero unresolved task-relevant findings
- Live/destructive/paid/external tests: require authorization
- Worker availability: health probe → bounded backoff → equivalent fallback →
  HUMAN-BLOCKED only when external intervention is required

## Task sizing

- One independently reviewable unit per worker by default
- Split discovery from construction when unfamiliar
- Split independently reviewable verification classes
- Use worker-produced construction briefs and Proof Obligations for non-trivial
  tasks rather than premium-orchestrator rediscovery

## Project rules

- Read `AGENTS.md`, `CLAUDE.md`, architecture docs, authoritative plan and referenced
  schemas/guides when present.
- Additional implementation rules: <optional path>
- Additional review/domain rules: <optional path>

## Orchestrator context checkpoints

- Enabled: yes
- Harness: auto-detect; explicit value wins
- Checkpoint due: 65%
- Compact before: 75%
- Hard ceiling: 80%
- Safe-boundary fallback when percentage unavailable: every 4 accepted tasks and
  before long phase gate
- HANDOVER: compact/incremental; update when resume semantics materially change
- Global harness configuration changes: no
