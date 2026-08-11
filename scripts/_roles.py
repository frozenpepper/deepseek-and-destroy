#!/usr/bin/env python3
"""Single registry for DSD worker roles, capabilities, role-skill paths, and terminals."""
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

ROLE_TERMINALS = {
    "implementer": {"PASS", "BLOCKED", "DECISION_REQUIRED"},
    "fixer": {"FIXED", "BLOCKED", "DECISION_REQUIRED"},
    "reviewer": {"PASS", "FAIL"},
    "verification": {"PASS", "FAIL"},
    "discovery": {"PASS", "BLOCKED", "DECISION_REQUIRED"},
    "phase-surveyor": {"PASS", "BLOCKED", "DECISION_REQUIRED"},
    "recovery": {"PASS", "BLOCKED", "DECISION_REQUIRED"},
    "phase-auditor": {"READY", "NOT_READY"},
    "evidence-clerk": {"CLEAN", "DISCREPANCY", "MALFORMED"},
}

ROLE_NAMES = tuple(ROLE_SKILLS)

# Distinct capabilities are named explicitly rather than overloading one "mutating"
# set. Evidence Clerk may update an explicitly contracted progress/documentation
# path, but it is not an implementation/fix role and does not participate in the
# two-zero-change source-work guard.
CONTRACT_SCOPED_WRITER_ROLES = frozenset({"implementer", "fixer", "evidence-clerk"})
ZERO_CHANGE_GUARD_ROLES = frozenset({"implementer", "fixer"})
PHASE_BARRIER_WRITER_ROLES = frozenset({"implementer", "fixer", "evidence-clerk"})
READ_ONLY_ROLES = frozenset(set(ROLE_NAMES) - set(CONTRACT_SCOPED_WRITER_ROLES))
