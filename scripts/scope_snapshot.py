#!/usr/bin/env python3
"""Capture and compare content-hash scope snapshots for DSD runs.

This helper is deliberately mechanical. It does not decide whether a change is
valid; workers and the orchestrator make that judgment from the resulting JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expand_paths(root: Path, raw_paths: Iterable[str]) -> set[Path]:
    result: set[Path] = set()
    for raw in raw_paths:
        candidate = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path is outside project root: {candidate}") from exc
        if candidate.is_dir():
            result.update(p for p in candidate.rglob("*") if p.is_file())
        else:
            result.add(candidate)
    return result


def git_changed_paths(root: Path) -> set[Path]:
    commands = [
        ["git", "diff", "--name-only", "--"],
        ["git", "diff", "--cached", "--name-only", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    result: set[Path] = set()
    for command in commands:
        completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        if completed.returncode not in (0, 128):
            raise RuntimeError(f"Command failed: {' '.join(command)}\n{completed.stderr}")
        if completed.returncode == 128:  # not a Git worktree
            return set()
        for line in completed.stdout.splitlines():
            if line.strip():
                result.add((root / line.strip()).resolve())
    return result


def capture(root: Path, paths: set[Path]) -> dict:
    entries: dict[str, dict] = {}
    for path in sorted(paths):
        rel = path.relative_to(root).as_posix()
        if path.is_file():
            stat = path.stat()
            entries[rel] = {"exists": True, "sha256": sha256_file(path), "size": stat.st_size}
        else:
            entries[rel] = {"exists": False, "sha256": None, "size": None}
    return {
        "format": "deepseek-and-destroy-scope-snapshot-v1",
        "project_root": str(root),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }


def compare(root: Path, baseline: dict) -> dict:
    old_entries: dict[str, dict] = baseline.get("entries", {})
    current_paths = {(root / rel).resolve() for rel in old_entries}
    current = capture(root, current_paths)
    new_entries = current["entries"]
    changed: list[dict] = []
    unchanged: list[str] = []
    for rel in sorted(old_entries):
        before = old_entries[rel]
        after = new_entries[rel]
        if before == after:
            unchanged.append(rel)
        else:
            changed.append({"path": rel, "before": before, "after": after})
    return {
        "format": "deepseek-and-destroy-scope-comparison-v1",
        "project_root": str(root),
        "compared_at": datetime.now(timezone.utc).isoformat(),
        "baseline_captured_at": baseline.get("captured_at"),
        "changed": changed,
        "unchanged": unchanged,
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="Create a content-hash snapshot")
    cap.add_argument("--root", required=True, type=Path)
    cap.add_argument("--output", required=True, type=Path)
    cap.add_argument("--include-git-changes", action="store_true")
    cap.add_argument("paths", nargs="+", help="Files or directories relative to root")

    cmp = sub.add_parser("compare", help="Compare current content to a snapshot")
    cmp.add_argument("--root", required=True, type=Path)
    cmp.add_argument("--baseline", required=True, type=Path)
    cmp.add_argument("--output", type=Path)
    cmp.add_argument("--fail-on-change", action="store_true")
    return ap


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"Project root does not exist: {root}", file=sys.stderr)
        return 2

    try:
        if args.command == "capture":
            paths = expand_paths(root, args.paths)
            if args.include_git_changes:
                paths.update(git_changed_paths(root))
            data = capture(root, paths)
            output = args.output.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
            print(f"Captured {len(data['entries'])} paths to {output}")
            return 0

        baseline = json.loads(args.baseline.read_text())
        data = compare(root, baseline)
        rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
        if args.output:
            output = args.output.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered)
            print(f"Compared {len(data['changed']) + len(data['unchanged'])} paths; "
                  f"{len(data['changed'])} changed. Report: {output}")
        else:
            sys.stdout.write(rendered)
        return 1 if args.fail_on_change and data["changed"] else 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"scope_snapshot error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
