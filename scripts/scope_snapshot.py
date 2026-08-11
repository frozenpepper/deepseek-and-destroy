#!/usr/bin/env python3
"""Capture and compare content-hash scope snapshots for DSD runs.

This helper is deliberately mechanical. It does not decide whether a change is
valid. It supports bounded path snapshots for mutating-task scope and a full Git
worktree snapshot for read-only independence checks. Parent-facing artifacts cite
the snapshot path; they do not ingest hash catalogs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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


def lexical_path(root: Path, raw: str | Path) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    # abspath normalizes . and .. without dereferencing symlinks. Scope capture
    # must never follow a project symlink into an external file just to hash it.
    return Path(os.path.abspath(os.fspath(candidate)))


def entry_for(path: Path) -> dict:
    if path.is_symlink():
        target = os.readlink(path)
        digest = hashlib.sha256(target.encode("utf-8", errors="surrogateescape")).hexdigest()
        return {"exists": True, "kind": "symlink", "target": target, "sha256": digest, "size": len(target.encode("utf-8", errors="surrogateescape"))}
    if path.is_file():
        stat = path.stat()
        return {"exists": True, "kind": "file", "sha256": sha256_file(path), "size": stat.st_size}
    return {"exists": False, "kind": None, "sha256": None, "size": None}


def is_excluded(rel: str, prefixes: list[str]) -> bool:
    normalized = Path(rel.replace("\\", "/")).as_posix()
    for raw in prefixes:
        prefix = Path(raw.replace("\\", "/")).as_posix().rstrip("/")
        if prefix and (normalized == prefix or normalized.startswith(prefix + "/")):
            return True
    return False


def expand_paths(root: Path, raw_paths: Iterable[str]) -> set[Path]:
    result: set[Path] = set()
    for raw in raw_paths:
        candidate = lexical_path(root, raw)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path is outside project root: {candidate}") from exc
        if candidate.is_symlink():
            result.add(candidate)
        elif candidate.is_dir():
            result.update(p for p in candidate.rglob("*") if p.is_file() or p.is_symlink())
        else:
            # Preserve a missing expected path as an explicit exists=false tripwire.
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
        if completed.returncode == 128:
            return set()
        for line in completed.stdout.splitlines():
            if line.strip():
                result.add(lexical_path(root, line.strip()))
    return result


def git_worktree_paths(root: Path, exclude_prefixes: list[str]) -> set[Path]:
    cp = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"git worktree inventory failed ({cp.returncode}): {cp.stderr.decode(errors='replace')}")
    result: set[Path] = set()
    for raw in cp.stdout.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="surrogateescape")
        if is_excluded(rel, exclude_prefixes):
            continue
        result.add(lexical_path(root, rel))
    return result


def capture(root: Path, paths: set[Path], *, inventory_mode: str = "paths", exclude_prefixes: list[str] | None = None) -> dict:
    entries: dict[str, dict] = {}
    for path in sorted(paths):
        rel = path.relative_to(root).as_posix()
        entries[rel] = entry_for(path)
    return {
        "format": "deepseek-and-destroy-scope-snapshot-v3",
        "project_root": str(root),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "inventory_mode": inventory_mode,
        "exclude_prefixes": exclude_prefixes or [],
        "entries": entries,
    }


def compare(root: Path, baseline: dict) -> dict:
    old_entries: dict[str, dict] = baseline.get("entries", {})
    mode = str(baseline.get("inventory_mode", "paths"))
    exclusions = [str(x) for x in baseline.get("exclude_prefixes", []) if isinstance(x, str)]
    rels = set(old_entries)
    if mode == "git-worktree":
        current_inventory = git_worktree_paths(root, exclusions)
        rels.update(path.relative_to(root).as_posix() for path in current_inventory)
    current_paths = {lexical_path(root, rel) for rel in rels}
    current = capture(root, current_paths, inventory_mode=mode, exclude_prefixes=exclusions)
    new_entries = current["entries"]
    changed: list[dict] = []
    unchanged: list[str] = []
    missing = {"exists": False, "kind": None, "sha256": None, "size": None}
    for rel in sorted(rels):
        before = old_entries.get(rel, missing)
        after = new_entries.get(rel, missing)
        if before == after:
            unchanged.append(rel)
        else:
            changed.append({"path": rel, "before": before, "after": after})
    return {
        "format": "deepseek-and-destroy-scope-comparison-v3",
        "project_root": str(root),
        "compared_at": datetime.now(timezone.utc).isoformat(),
        "baseline_captured_at": baseline.get("captured_at"),
        "inventory_mode": mode,
        "exclude_prefixes": exclusions,
        "changed": changed,
        "unchanged": unchanged,
    }


def write_new_json(path: Path, data: dict) -> None:
    """Write one immutable evidence artifact; callers use a new numbered path for later evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    except FileExistsError as exc:
        raise ValueError(f"immutable scope artifact already exists: {path}; use a new path") from exc


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="Create a content-hash snapshot")
    cap.add_argument("--root", required=True, type=Path)
    cap.add_argument("--output", required=True, type=Path)
    cap.add_argument("--include-git-changes", action="store_true")
    cap.add_argument("--git-worktree", action="store_true", help="snapshot all Git tracked + untracked nonignored files; ideal for read-only worker independence")
    cap.add_argument("--exclude-prefix", action="append", default=[], help="project-relative prefix excluded from --git-worktree inventory; repeatable")
    cap.add_argument("paths", nargs="*", help="Files/directories relative to root for bounded scope snapshots")

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
            if args.git_worktree and args.paths:
                raise ValueError("use either --git-worktree or explicit paths, not both")
            if not args.git_worktree and not args.paths:
                raise ValueError("capture requires --git-worktree or at least one explicit path")
            if args.git_worktree:
                paths = git_worktree_paths(root, args.exclude_prefix)
                mode = "git-worktree"
            else:
                paths = expand_paths(root, args.paths)
                if args.include_git_changes:
                    paths.update(git_changed_paths(root))
                mode = "paths"
            data = capture(root, paths, inventory_mode=mode, exclude_prefixes=args.exclude_prefix)
            output = args.output.resolve()
            write_new_json(output, data)
            print(f"Captured {len(data['entries'])} paths ({mode}) to {output}")
            return 0

        baseline = json.loads(args.baseline.read_text())
        data = compare(root, baseline)
        rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
        if args.output:
            output = args.output.resolve()
            write_new_json(output, data)
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
