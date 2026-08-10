# Worker Role Index

This file is a compact map from DSD role to the durable protocol a worker reads.
It exists so launch prompts can remain path-only instead of embedding role
boilerplate.

| Role | Mutates project source? | Protocol |
|---|---:|---|
| Phase Surveyor | no | `worker/SKILL.md` + task contract |
| Discovery Worker | no | `worker/SKILL.md` + task contract |
| Implementer | yes | `worker/SKILL.md` + `worker/BUILD.md` |
| Fixer | yes | `worker/SKILL.md` + `worker/BUILD.md` |
| Verification Worker | no | `worker/SKILL.md` + `worker/REVIEW.md` |
| Reviewer | no | `worker/SKILL.md` + `worker/REVIEW.md` |
| Recovery Auditor | no | `worker/SKILL.md` + `worker/REVIEW.md` |
| Phase Auditor | no | `worker/SKILL.md` + `worker/REVIEW.md` |
| Evidence Clerk | no project-source edits; derived DSD artifacts only | `worker/SKILL.md` + `worker/EVIDENCE.md` |

The role is chosen by the orchestrator/task contract. Do not create separate static
agent definitions merely to represent these roles when one harness worker profile
can execute them safely.
