#!/usr/bin/env python3
"""Parse only task-contract fields needed for objective DSD mechanics.

No helper here interprets acceptance quality or worker prose. The deterministic layer
may read explicit control fields such as write boundaries, protected ignored roots,
and optional proof-pattern loading hints.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from _roles import ALWAYS_PROJECT_WRITER_ROLES


def markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.I | re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    nxt = re.search(r"^##\s+", text[start:], re.M)
    end = start + nxt.start() if nxt else len(text)
    return re.sub(r"<!--.*?-->", "", text[start:end], flags=re.S).strip()


def _safe_prefixes(text: str, heading: str, *, forbid_dsd: bool = False) -> list[str]:
    section = markdown_section(text, heading)
    if not section or section.strip().upper() == "NONE":
        return []
    result: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        value = stripped[1:].strip().strip("`").replace("\\", "/").rstrip("/")
        if not value or value.upper() == "NONE":
            continue
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {".", "./"}:
            raise ValueError(f"unsafe {heading} entry: {value}")
        normalized = path.as_posix()
        if forbid_dsd and (normalized == "DeepSeekAndDestroy" or normalized.startswith("DeepSeekAndDestroy/")):
            raise ValueError(f"{heading} cannot target DeepSeekAndDestroy/**")
        result.append(normalized)
    return list(dict.fromkeys(result))


def _bullet_values(text: str, heading: str) -> list[str]:
    section = markdown_section(text, heading)
    if not section or section.strip().upper() == "NONE":
        return []
    out: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            value = stripped[1:].strip().strip("`")
            if value:
                out.append(value)
    return list(dict.fromkeys(out))


def allowed_source_changes(text: str) -> list[str]:
    return _safe_prefixes(text, "Allowed source changes")


def extra_scope_inventory(text: str) -> list[str]:
    return _safe_prefixes(text, "Extra scope inventory", forbid_dsd=True)


def proof_pattern_tags(text: str) -> list[str]:
    """Explicit loading hints only; tags are not acceptance semantics."""
    return _bullet_values(text, "Proof patterns")


def role_writes_project(role: str, text: str) -> bool:
    """Whether this exact role+contract may mutate accepted project state."""
    role = role.lower().replace("_", "-")
    if role in ALWAYS_PROJECT_WRITER_ROLES:
        return True
    if role == "verification":
        return bool(allowed_source_changes(text))
    # Evidence Clerk is always project-read-only. It may write DSD attempt artifacts,
    # never project state. Project documentation updates are ordinary writer tasks.
    return False


def validate_role_contract(role: str, text: str) -> list[str]:
    """Reserved for objective role/contract contradictions; currently none."""
    return []
