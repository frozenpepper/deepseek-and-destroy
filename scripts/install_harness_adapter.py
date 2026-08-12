#!/usr/bin/env python3
"""Install the project-local DSD adapter for the selected orchestrator harness.

The installer is idempotent and backs up changed JSON configuration files. It
never edits user-global harness configuration.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from detect_harness import select_harness

MARKER = "DeepSeekAndDestroy/tools/context_checkpoint.py"


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git_root(start: Path) -> Path:
    try:
        out = subprocess.check_output(["git", "-C", str(start), "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL).strip()
        if out:
            return Path(out).resolve()
    except Exception:
        pass
    return start.resolve()


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    destination = path.with_name(path.name + f".dsd-backup-{utc_stamp()}")
    shutil.copy2(path, destination)
    return destination


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_hook(data: dict[str, Any], event: str, group: dict[str, Any], marker: str = MARKER) -> bool:
    hooks = data.setdefault("hooks", {})
    groups = hooks.setdefault(event, [])
    for existing in groups:
        for handler in existing.get("hooks", []):
            if marker in str(handler.get("command", "")) and (event.lower() in str(handler.get("command", "")).lower() or marker != MARKER):
                if existing == group:
                    return False
                existing.clear(); existing.update(group); return True
    groups.append(group)
    return True


def install_hook_fragment(path: Path, fragment_path: Path) -> tuple[bool, Path | None]:
    """Merge canonical hook groups from a checked-in adapter fragment."""
    data = load_json(path)
    fragment = load_json(fragment_path)
    changed = False
    if "description" in fragment and not data.get("description"):
        data["description"] = fragment["description"]
        changed = True
    for event, groups in (fragment.get("hooks") or {}).items():
        for group in groups:
            marker = "claude_worker_rewake.py" if any(
                "claude_worker_rewake.py" in str(h.get("command", ""))
                for h in group.get("hooks", [])
            ) else MARKER
            changed |= ensure_hook(data, event, group, marker=marker)
    backup_path = backup(path) if changed and path.exists() else None
    if changed:
        write_json(path, data)
    return changed, backup_path


def install_helper(skill_root: Path, project_root: Path) -> Path:
    tools = project_root / "DeepSeekAndDestroy" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    for name in ("context_checkpoint.py", "check_state.py", "dsd_state.py", "_contract.py", "_rules_snapshot.py", "_roles.py"):
        source = skill_root / "scripts" / name
        destination = tools / name
        shutil.copy2(source, destination)
        destination.chmod(0o755)
    return tools / "context_checkpoint.py"


def install_codex(project_root: Path, skill_root: Path) -> dict[str, Any]:
    path = project_root / ".codex" / "hooks.json"
    changed, backup_path = install_hook_fragment(path, skill_root / "adapters" / "codex" / "hooks.json")
    return {
        "harness": "codex",
        "config": str(path),
        "changed": changed,
        "backup": str(backup_path) if backup_path else None,
        "manual_step": "Open /hooks in Codex and trust the project-local hooks before relying on them.",
    }


def install_claude(project_root: Path, skill_root: Path) -> dict[str, Any]:
    path = project_root / ".claude" / "settings.json"
    changed, backup_path = install_hook_fragment(path, skill_root / "adapters" / "claude" / "settings.fragment.json")
    rewake_source = skill_root / "scripts" / "claude_worker_rewake.py"
    rewake_target = project_root / "DeepSeekAndDestroy" / "tools" / "claude_worker_rewake.py"
    rewake_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rewake_source, rewake_target)
    rewake_target.chmod(0o755)
    return {
        "harness": "claude-code",
        "config": str(path),
        "changed": changed,
        "backup": str(backup_path) if backup_path else None,
        "worker_rewake_helper": str(rewake_target),
    }


def install_plugin_file(project_root: Path, harness: str, destination: Path, source_path: Path) -> dict[str, Any]:
    source = source_path.read_text(encoding="utf-8")
    path = project_root / destination
    changed = not path.exists() or path.read_text(encoding="utf-8") != source
    backup_path = backup(path) if changed and path.exists() else None
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return {"harness": harness, "plugin": str(path), "changed": changed, "backup": str(backup_path) if backup_path else None}


def install_opencode(project_root: Path, skill_root: Path) -> dict[str, Any]:
    result = install_plugin_file(
        project_root, "opencode", Path(".opencode/plugins/dsd-compaction.ts"),
        skill_root / "adapters" / "opencode" / "dsd-compaction.ts",
    )
    result["manual_step"] = "Restart/reload OpenCode so the project-local plugin is active; DSD verify-resume completes post-compaction continuity."
    return result


def install_kilo(project_root: Path, skill_root: Path) -> dict[str, Any]:
    result = install_plugin_file(
        project_root, "kilo", Path(".kilo/plugin/dsd-compaction.ts"),
        skill_root / "adapters" / "kilo" / "dsd-compaction.ts",
    )
    result["manual_step"] = "Restart/reload Kilo so the project-local plugin is active; DSD verify-resume completes post-compaction continuity."
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", default="auto", choices=["auto", "codex", "claude-code", "opencode", "kilo"])
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    project_root = git_root(args.project_root)
    skill_root = args.skill_root.resolve()
    try:
        selected, _confidence, _scores, _commands = select_harness(None if args.harness == "auto" else args.harness)
        if selected == "unknown":
            raise RuntimeError("Harness detection is ambiguous; pass --harness codex|claude-code|opencode|kilo")
        harness = selected
        helper = install_helper(skill_root, project_root)
        if harness == "codex": result = install_codex(project_root, skill_root)
        elif harness == "claude-code": result = install_claude(project_root, skill_root)
        elif harness == "opencode": result = install_opencode(project_root, skill_root)
        else: result = install_kilo(project_root, skill_root)
        result.update({"project_root": str(project_root), "helper": str(helper), "installed_at": utc_stamp()})
        report = project_root / "DeepSeekAndDestroy" / "harness-adapter-installation.md"
        report.write_text("# DeepSeek and Destroy Harness Adapter\n\n```json\n" + json.dumps(result, indent=2) + "\n```\n", encoding="utf-8")
        print(json.dumps(result, indent=2)); return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
