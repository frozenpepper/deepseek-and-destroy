#!/usr/bin/env python3
"""Capture and compare compact factual project-state snapshots for DSD attempts.

New Git attempts snapshot only the dirty/untracked set plus explicitly named ignored
roots. The terminal comparison hashes only paths that could have changed during the
attempt. Historical full-worktree snapshots remain readable for existing runs.
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

from _contract import extra_scope_inventory


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
    return Path(os.path.abspath(os.fspath(candidate)))


def entry_for(path: Path) -> dict:
    if path.is_symlink():
        target = os.readlink(path)
        encoded = target.encode("utf-8", errors="surrogateescape")
        return {"exists": True, "kind": "symlink", "target": target, "sha256": hashlib.sha256(encoded).hexdigest(), "size": len(encoded)}
    if path.is_file():
        stat = path.stat()
        return {"exists": True, "kind": "file", "sha256": sha256_file(path), "size": stat.st_size}
    if path.is_dir():
        return {"exists": True, "kind": "directory", "sha256": None, "size": None}
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
            result.add(candidate)  # missing path remains an explicit tripwire
    return result


def git_output(root: Path, command: list[str], *, binary: bool = False) -> str | bytes | None:
    cp = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if cp.returncode == 128:
        return None
    if cp.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{cp.stderr.decode(errors='replace')}")
    return cp.stdout if binary else cp.stdout.decode("utf-8", errors="surrogateescape")


def git_head(root: Path) -> str | None:
    out = git_output(root, ["git", "rev-parse", "HEAD"])
    if out is None:
        return None
    return str(out).strip() or None


def git_changed_paths(root: Path, exclude_prefixes: list[str] | None = None) -> set[Path]:
    exclusions = exclude_prefixes or []
    commands = [
        ["git", "diff", "--name-only", "-z", "--"],
        ["git", "diff", "--cached", "--name-only", "-z", "--"],
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
    ]
    result: set[Path] = set()
    for command in commands:
        raw = git_output(root, command, binary=True)
        if raw is None:
            raise RuntimeError("Git project required for compact DSD scope capture")
        assert isinstance(raw, bytes)
        for item in raw.split(b"\0"):
            if not item:
                continue
            rel = item.decode("utf-8", errors="surrogateescape")
            if not is_excluded(rel, exclusions):
                result.add(lexical_path(root, rel))
    return result


def git_path_exists_in_commit(root: Path, commit: str | None, rel: str) -> bool:
    if not commit:
        return False
    cp = subprocess.run(["git", "cat-file", "-e", f"{commit}:{rel}"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return cp.returncode == 0


def git_paths_between(root: Path, before: str | None, after: str | None, exclude_prefixes: list[str]) -> set[Path]:
    if not before or not after or before == after:
        return set()
    raw = git_output(root, ["git", "diff", "--name-only", "-z", before, after, "--"], binary=True)
    if raw is None:
        return set()
    assert isinstance(raw, bytes)
    out: set[Path] = set()
    for item in raw.split(b"\0"):
        if not item:
            continue
        rel = item.decode("utf-8", errors="surrogateescape")
        if not is_excluded(rel, exclude_prefixes):
            out.add(lexical_path(root, rel))
    return out


def git_worktree_paths(root: Path, exclude_prefixes: list[str]) -> set[Path]:
    """Legacy v4 full inventory; retained only to read/compare historical runs."""
    raw = git_output(root, ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], binary=True)
    if raw is None:
        raise RuntimeError("git worktree inventory failed: not a Git project")
    assert isinstance(raw, bytes)
    result: set[Path] = set()
    for item in raw.split(b"\0"):
        if not item:
            continue
        rel = item.decode("utf-8", errors="surrogateescape")
        if not is_excluded(rel, exclude_prefixes):
            result.add(lexical_path(root, rel))
    return result


def capture(root: Path, paths: set[Path], *, inventory_mode: str = "paths", exclude_prefixes: list[str] | None = None,
            extra_inventory_specs: list[str] | None = None, baseline_head: str | None = None) -> dict:
    entries: dict[str, dict] = {}
    for path in sorted(paths):
        entries[path.relative_to(root).as_posix()] = entry_for(path)
    return {
        "format": "deepseek-and-destroy-scope-snapshot-v5" if inventory_mode == "git-dirty" else "deepseek-and-destroy-scope-snapshot-v4",
        "project_root": str(root),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "inventory_mode": inventory_mode,
        "git_head": baseline_head,
        "exclude_prefixes": exclude_prefixes or [],
        "extra_inventory_specs": extra_inventory_specs or [],
        "entries": entries,
    }


def compare(root: Path, baseline: dict) -> dict:
    old_entries: dict[str, dict] = baseline.get("entries", {})
    mode = str(baseline.get("inventory_mode", "paths"))
    exclusions = [str(x) for x in baseline.get("exclude_prefixes", []) if isinstance(x, str)]
    extra_specs = [str(x) for x in baseline.get("extra_inventory_specs", []) if isinstance(x, str)]
    rels = set(old_entries)
    head_before = baseline.get("git_head") if isinstance(baseline.get("git_head"), str) else None
    head_after = git_head(root) if mode == "git-dirty" else head_before
    current_git_rels: set[str] = set()
    current_extra_rels: set[str] = set()

    if mode == "git-worktree":  # historical v4 compatibility
        current_inventory = git_worktree_paths(root, exclusions)
        current_git_rels = {path.relative_to(root).as_posix() for path in current_inventory}
        rels.update(current_git_rels)
    elif mode == "git-dirty":
        current_dirty = git_changed_paths(root, exclusions)
        head_delta = git_paths_between(root, head_before, head_after, exclusions)
        current_git_rels = {path.relative_to(root).as_posix() for path in (current_dirty | head_delta)}
        rels.update(current_git_rels)

    if extra_specs:
        current_extra_rels = {path.relative_to(root).as_posix() for path in expand_paths(root, extra_specs)}
        rels.update(current_extra_rels)

    current_paths = {lexical_path(root, rel) for rel in rels}
    current = capture(root, current_paths, inventory_mode=mode, exclude_prefixes=exclusions,
                      extra_inventory_specs=extra_specs, baseline_head=head_after)
    new_entries = current["entries"]
    changed: list[dict] = []
    added: list[str] = []
    removed: list[str] = []
    modified: list[str] = []
    unchanged: list[str] = []
    missing = {"exists": False, "kind": None, "sha256": None, "size": None}
    clean_baseline = {"state": "clean-at-baseline"}

    for rel in sorted(rels):
        if rel in old_entries:
            before = old_entries[rel]
            after = new_entries.get(rel, missing)
            if before == after:
                unchanged.append(rel)
                continue
        elif mode == "git-dirty" and rel in current_extra_rels:
            before = missing
            after = new_entries.get(rel, missing)
        elif mode == "git-dirty" and rel in current_git_rels:
            before = clean_baseline
            after = new_entries.get(rel, missing)
        else:
            before = missing
            after = new_entries.get(rel, missing)
            if before == after:
                unchanged.append(rel)
                continue

        changed.append({"path": rel, "before": before, "after": after})
        if before is clean_baseline:
            existed_before = git_path_exists_in_commit(root, head_before, rel)
        else:
            existed_before = bool(isinstance(before, dict) and before.get("exists"))
        if not existed_before and after.get("exists"):
            added.append(rel)
        elif existed_before and after.get("exists") is False:
            removed.append(rel)
        else:
            modified.append(rel)

    head_changed = bool(head_before and head_after and head_before != head_after)
    return {
        "format": "deepseek-and-destroy-scope-comparison-v5" if mode == "git-dirty" else "deepseek-and-destroy-scope-comparison-v4",
        "project_root": str(root),
        "compared_at": datetime.now(timezone.utc).isoformat(),
        "baseline_captured_at": baseline.get("captured_at"),
        "inventory_mode": mode,
        "git_head_before": head_before,
        "git_head_after": head_after,
        "git_head_changed": head_changed,
        "exclude_prefixes": exclusions,
        "extra_inventory_specs": extra_specs,
        "changed": changed,
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
    }


def write_new_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    except FileExistsError as exc:
        raise ValueError(f"immutable scope artifact already exists: {path}; use a new path") from exc


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture", help="Create a factual project-state baseline")
    cap.add_argument("--root", required=True, type=Path)
    cap.add_argument("--output", required=True, type=Path)
    cap.add_argument("--include-git-changes", action="store_true")
    cap.add_argument("--git-dirty", action="store_true", help="compact baseline: hash only dirty/untracked paths plus explicit ignored inventory")
    cap.add_argument("--git-worktree", action="store_true", help=argparse.SUPPRESS)  # historical compatibility only
    cap.add_argument("--exclude-prefix", action="append", default=[])
    cap.add_argument("--extra-inventory", action="append", default=[])
    cap.add_argument("--task-contract", type=Path)
    cap.add_argument("paths", nargs="*")
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
            git_mode = bool(args.git_dirty or args.git_worktree)
            if git_mode and args.paths:
                raise ValueError("use a Git inventory mode or explicit paths, not both")
            if not git_mode and not args.paths:
                raise ValueError("capture requires --git-dirty or at least one explicit path")
            contract_extra: list[str] = []
            if args.task_contract:
                task_contract = args.task_contract if args.task_contract.is_absolute() else root / args.task_contract
                task_contract = task_contract.resolve()
                if not task_contract.is_file():
                    raise ValueError(f"task contract missing: {task_contract}")
                contract_extra = extra_scope_inventory(task_contract.read_text(encoding="utf-8", errors="replace"))
            requested_extra = list(dict.fromkeys([*args.extra_inventory, *contract_extra]))
            extra_specs: list[str] = []
            if args.git_dirty:
                paths = git_changed_paths(root, args.exclude_prefix)
                mode = "git-dirty"
                head = git_head(root)
            elif args.git_worktree:
                paths = git_worktree_paths(root, args.exclude_prefix)
                mode = "git-worktree"
                head = None
            else:
                paths = expand_paths(root, args.paths)
                if args.include_git_changes:
                    paths.update(git_changed_paths(root, args.exclude_prefix))
                mode = "paths"
                head = None
            if requested_extra:
                if not git_mode:
                    raise ValueError("extra inventory is supported only with Git inventory modes")
                for raw in requested_extra:
                    candidate = lexical_path(root, raw)
                    rel = candidate.relative_to(root).as_posix()
                    if rel == "DeepSeekAndDestroy" or rel.startswith("DeepSeekAndDestroy/"):
                        raise ValueError("--extra-inventory cannot target DeepSeekAndDestroy/**")
                    extra_specs.append(rel)
                extra_specs = list(dict.fromkeys(extra_specs))
                paths.update(expand_paths(root, extra_specs))
            data = capture(root, paths, inventory_mode=mode, exclude_prefixes=args.exclude_prefix,
                           extra_inventory_specs=extra_specs, baseline_head=head)
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
            print(f"Compared compact scope; {len(data['changed'])} path(s) changed. Report: {output}")
        else:
            sys.stdout.write(rendered)
        changed = bool(data["changed"] or data.get("git_head_changed"))
        return 1 if args.fail_on_change and changed else 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"scope_snapshot error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
