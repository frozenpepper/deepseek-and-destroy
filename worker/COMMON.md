# DSD Worker Common

Your prompt names the only authorities to read. Obey immutable run rules, your one role
skill, and the task contract. Do not delegate or broaden scope.

## Scope

- Start from current project state; inspect before acting.
- Change project files only when your role permits it and only under exact `Allowed
  source changes`.
- `DeepSeekAndDestroy/**` is orchestration evidence, not project write scope; write only
  your assigned report/evidence artifacts there.
- Do not start background mutators or unrelated cleanup.
- If authority conflicts, required evidence is unavailable, or safe bounded work is
  impossible, report the blocker instead of inventing authority.

## Evidence

Technical claims need discriminating evidence: exercise the real mechanism and, where
material, a plausible broken implementation/counterexample that would fail. A passing
command alone is not proof when it can bypass the claimed mechanism.

Report truthfully and compactly (target <=80 lines); put the conclusion first. Useful content:
work/findings, verification, defects/uncertainty, evidence paths. Formatting is guidance,
not a protocol. Do not waste effort polishing Markdown or ceremonial markers.

Never expose private chain-of-thought, secrets, or credentials. Preserve concrete facts,
commands/results, paths, and unresolved uncertainty.

Final stdout: brief status + report path only.
