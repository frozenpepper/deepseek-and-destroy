#!/usr/bin/env python3
"""DSD worker-role registry plus objective project-write capability."""
from __future__ import annotations

ROLE_SKILLS = {
    "implementer": "roles/dsd-implementer/SKILL.md",
    "fixer": "roles/dsd-fixer/SKILL.md",
    "reviewer": "roles/dsd-reviewer/SKILL.md",
    "verification": "roles/dsd-verification/SKILL.md",
    "discovery": "roles/dsd-discovery/SKILL.md",
    "phase-surveyor": "roles/dsd-phase-surveyor/SKILL.md",
    "recovery": "roles/dsd-recovery/SKILL.md",
    "phase-auditor": "roles/dsd-phase-auditor/SKILL.md",
    "evidence-clerk": "roles/dsd-evidence-clerk/SKILL.md",
}
ROLE_NAMES = tuple(ROLE_SKILLS)

ALWAYS_PROJECT_WRITERS = frozenset({"implementer", "fixer"})
CONDITIONAL_PROJECT_WRITERS = frozenset({"verification"})
ZERO_CHANGE_GUARD_ROLES = ALWAYS_PROJECT_WRITERS


def role_is_project_writer(role: str, allowed_source_changes: list[str] | tuple[str, ...] | set[str]) -> bool:
    role = role.lower()
    return role in ALWAYS_PROJECT_WRITERS or (role in CONDITIONAL_PROJECT_WRITERS and bool(allowed_source_changes))
