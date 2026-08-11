#!/usr/bin/env python3
"""Shared verification for immutable DSD worker-rules revisions."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _roles import ROLE_SKILLS

PROTOCOL_NAMES = (
    "COMMON.md",
    "PROOF-PATTERNS.md",
    *tuple(ROLE_SKILLS.values()),
)
MANIFEST_FORMAT = "dsd-worker-rules-manifest-v2"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def protocol_fingerprint(protocol_dir: Path) -> str:
    h = hashlib.sha256()
    for name in PROTOCOL_NAMES:
        path = protocol_dir / name
        if not path.is_file():
            raise ValueError(f"worker protocol snapshot is incomplete: {path}")
        h.update(name.encode("utf-8")); h.update(b"\0")
        h.update(path.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def revision_number(rules_path: Path) -> int:
    m = re.fullmatch(r"r(\d{4})", rules_path.parent.name)
    if not m or rules_path.name != "WORKER_RULES.md":
        raise ValueError(f"worker rules must identify worker-rules/rNNNN/WORKER_RULES.md: {rules_path}")
    return int(m.group(1))


def current_payload(rules_path: Path) -> dict[str, Any]:
    rules_path = rules_path.resolve()
    revision = revision_number(rules_path)
    protocol_dir = rules_path.parent / "protocol"
    return {
        "format": MANIFEST_FORMAT,
        "revision": revision,
        "path": str(rules_path),
        "sha256": sha256_file(rules_path),
        "protocol_dir": str(protocol_dir.resolve()),
        "protocol_fingerprint": protocol_fingerprint(protocol_dir),
        "protocol": {name: sha256_file(protocol_dir / name) for name in PROTOCOL_NAMES},
    }


def verify_snapshot(rules_path: Path) -> dict[str, Any]:
    rules_path = rules_path.resolve()
    manifest_path = rules_path.parent / "MANIFEST.json"
    if not rules_path.is_file():
        raise ValueError(f"worker rules missing: {rules_path}")
    if not manifest_path.is_file():
        raise ValueError(f"worker-rules manifest missing: {manifest_path}")
    try:
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"worker-rules manifest unreadable: {exc}") from exc
    actual = current_payload(rules_path)
    for key in ("format", "revision", "path", "sha256", "protocol_dir", "protocol_fingerprint", "protocol"):
        if recorded.get(key) != actual[key]:
            raise ValueError(f"immutable worker-rules revision changed after creation: {key} differs from manifest")
    return {
        **actual,
        "manifest": str(manifest_path.resolve()),
        "manifest_sha256": sha256_file(manifest_path),
    }
