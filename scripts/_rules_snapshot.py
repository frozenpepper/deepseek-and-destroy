#!/usr/bin/env python3
"""Verify immutable DSD worker-rules snapshots."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rules_manifest(manifest_path: Path) -> dict[str, Any]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("worker-rules manifest must be a JSON object")
    return data


def verify_rules_manifest(manifest_path: Path) -> list[str]:
    """Return integrity errors for a rules snapshot manifest; [] means clean."""
    errors: list[str] = []
    try:
        data = load_rules_manifest(manifest_path)
    except Exception as exc:
        return [f"cannot load worker-rules manifest {manifest_path}: {exc}"]

    files = data.get("files")
    if not isinstance(files, list) or not files:
        return ["worker-rules manifest has no files"]

    root_raw = data.get("snapshot_root")
    if not isinstance(root_raw, str) or not root_raw:
        return ["worker-rules manifest missing snapshot_root"]
    root = Path(root_raw).expanduser().resolve()

    for row in files:
        if not isinstance(row, dict):
            errors.append("worker-rules manifest contains non-object file row")
            continue
        rel = row.get("path")
        expected = row.get("sha256")
        if not isinstance(rel, str) or not rel:
            errors.append("worker-rules manifest row missing path")
            continue
        if not isinstance(expected, str) or len(expected) != 64:
            errors.append(f"worker-rules manifest row {rel} has invalid sha256")
            continue
        path = root / rel
        if not path.is_file():
            errors.append(f"worker-rules snapshot file missing: {path}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            errors.append(f"worker-rules snapshot tampered: {path}")

    return errors
