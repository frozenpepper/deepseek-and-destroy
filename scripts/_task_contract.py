#!/usr/bin/env python3
"""Small mechanical parser for immutable DSD task-contract fields."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

AC_START_RE = re.compile(r"^\s*[-*+]\s*(?:\*\*|__)?(AC-\d+)\b", re.I)
PATTERN_RE = re.compile(r"^[A-Z][A-Z0-9-]*$")


def markdown_section(text: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.I | re.M)
    if not match:
        return ""
    start = match.end()
    nxt = re.search(r"^##\s+", text[start:], re.M)
    end = start + nxt.start() if nxt else len(text)
    return re.sub(r"<!--.*?-->", "", text[start:end], flags=re.S).strip()


def _bullet_values(text: str, heading: str) -> list[str]:
    section = markdown_section(text, heading)
    if not section or section.upper() == "NONE":
        return []
    out: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            value = stripped[1:].strip().strip("`")
            if value and value.upper() != "NONE":
                out.append(value)
    return list(dict.fromkeys(out))


def project_path_list(text: str, heading: str) -> list[str]:
    result: list[str] = []
    for value in _bullet_values(text, heading):
        normalized = value.replace("\\", "/").rstrip("/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or normalized in {".", "./"}:
            raise ValueError(f"unsafe {heading} entry: {value}")
        result.append(path.as_posix())
    return result


def allowed_source_changes(text: str) -> list[str]:
    return project_path_list(text, "Allowed source changes")



def extra_scope_inventory(text: str) -> list[str]:
    return project_path_list(text, "Extra scope inventory")


def proof_patterns(text: str) -> list[str]:
    values = [v.upper() for v in _bullet_values(text, "Proof patterns")]
    bad = [v for v in values if not PATTERN_RE.fullmatch(v)]
    if bad:
        raise ValueError("invalid Proof patterns entry: " + ", ".join(bad))
    return values


def acceptance_acs(text: str) -> list[str]:
    section = markdown_section(text, "Acceptance criteria")
    seen: set[str] = set()
    out: list[str] = []
    for raw in section.splitlines():
        match = AC_START_RE.match(raw)
        if match:
            ac = match.group(1).upper()
            if ac not in seen:
                seen.add(ac)
                out.append(ac)
    return out
