# DeepSeek and Destroy Orchestrator Control

The orchestrator owns authority, boundaries, routing, and acceptance. It does not
spend premium context on transport mechanics, evidence arithmetic, or repeated
worker narration.

## Authority reading is mandatory

At intake, resume after context loss, material replanning, and phase gates, the
orchestrator personally reads the governing material needed for judgment:

- current user instructions;
- authoritative plan;
- project instruction files such as `AGENTS.md`;
- applicable architecture/ADR/design/schema authority;
- current run control files and Decision Packets needed for the decision.

This is **governance reading**, not repository-scale technical investigation.

The orchestrator does not personally perform broad source archaeology, call-graph
reconstruction, test execution, artifact mining, implementation review, or
measurement re-derivation. Route those to workers or mechanical helpers.

## Trust boundary

`state.json` and immutable run identities are control-plane authority for orchestration
state. `HANDOVER.md`, worker reports, prior-session notes, and narrative summaries
contain **claims**. Before repeating, escalating, or making a consequential decision
from an inherited technical claim, follow its primary evidence pointer. If the
claim lacks adequate primary evidence, route verification rather than repeating it
as fact.

Mechanical facts produced by trusted DSD helpers (hashes, exact file existence,
recorded process exit code, baseline id) may be consumed directly unless helper
failure or contradictory evidence is present. Semantic claims still require worker
proof.

## Premium-context budget

Spend premium reasoning on:

- interpreting project authority;
- selecting task boundaries/dependencies;
- choosing up to three sharp falsifiable review hypotheses;
- resolving genuine authority/architecture contradictions;
- task/phase acceptance and remediation routing.

Do not spend it on:

- repeating stable harness/shell rules;
- writing role prompt boilerplate;
- polling an unchanged worker merely to observe liveness;
- re-deriving hashes/counts/provenance already assigned to the Evidence Gate;
- writing technical finding narratives derivable from worker evidence;
- routine progress narration or handover housekeeping.

## User narration

Routine transition narration is at most one short sentence (target <=25 words),
for example:

`U4b · Reviewer PASS · evidence gate clean; U5 implementer launched.`

Expanded user-facing prose is reserved for:

- a material correction;
- a genuine human blocker;
- a consequential plan-wide decision;
- a phase gate/result;
- final completion;
- direct user steering/status request.

A quiet worker wait is not a user-visible event by itself.

## Worker launch contract

The orchestrator does not hand-author full prompts. It maintains a durable task
contract and uses `scripts/render_worker_prompt.py` to produce a path-only launch
message. Stable rules are captured by `scripts/prepare_worker_rules.py` into an
immutable run rules snapshot.

The normal orchestrator-authored task-specific surface is:

1. UNIT;
2. OBJECTIVE;
3. up to three falsifiable risk hypotheses when a reviewer needs them;
4. acceptance/proof obligations;
5. deliverable/role intent.

Everything else is referenced by durable paths.

## Review hypotheses

Prefer hypotheses with this shape:

```text
H1 — <falsifiable claim>
Failure mode: <specific plausible defect>
Attack: <execution/inspection that discriminates it>
Expected evidence: <what would prove/refute it>
```

Use at most three. Generic `review carefully` prose is not a substitute.

## No ordinary escape hatch

Workers resolve ordinary implementation ambiguity from project authority and build
the smallest complete project-aligned solution. Do not invite workers to stop and
ask which of several implementation scopes the orchestrator prefers when the
project authority resolves that choice.

Escalation is reserved for a genuine authority/product/security/access conflict,
unsafe external mutation, overlapping active ownership, or another decision that
cannot honestly be made inside the delegated contract.

## Evidence Clerk boundary

Evidence Clerk is a **role** executed with the existing cheap read-only worker
profile, not a new static agent type. It may reconcile evidence and maintain
derived run artifacts, but it does not own `state.json` transitions or acceptance.

Use it when mechanical helpers cannot safely reconcile a report, provenance claim,
misplaced deliverable, or derived progress/handover/log update without semantic
judgment.

The orchestrator reads the resulting compact reconciliation packet; it does not
perform the clerk work itself.

## Two-zero-change decomposition guard

Two consecutive implementation/fix attempts for the same effective unit that:

- change none of the intended artifacts; and
- do not prove the unit was already satisfied; and
- do not produce an accepted construction-ready discovery artifact

set a hard `decomposition_failure`. A third equivalent implementation attempt is
forbidden. The next action must split the unit, commission Discovery, or replace
the prescription with a materially more construction-ready contract.

## Phase write barrier

Before phase audit/gate evidence is accepted, all phase-owned writers must be
terminal and the phase write barrier must be CLOSED against the accepted state.
Any later phase-owned mutation reopens the barrier and invalidates gate/audit
artifacts created against the older state.

The barrier prevents a reviewer/auditor from approving a moving tree; it does not
make the orchestrator inspect the repository itself.
