#!/usr/bin/env python3
"""Single registry for DSD worker roles and objective project-write capabilities."""
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
ALWAYS_PROJECT_WRITER_ROLES = frozenset({"implementer", "fixer"})
CONDITIONALLY_WRITING_ROLES = frozenset({"verification"})
ALWAYS_READ_ONLY_ROLES = frozenset(set(ROLE_NAMES) - set(ALWAYS_PROJECT_WRITER_ROLES) - set(CONDITIONALLY_WRITING_ROLES))
