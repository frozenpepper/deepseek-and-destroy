#!/usr/bin/env python3
"""Install DSD orchestrator-harness integration without changing worker transport.

OpenCode CLI remains the default DSD worker transport. This installer configures
how the *orchestrator* observes external worker completion and handles compaction.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def install_helpers(skill_root: Path, project_root: Path) -> list[str]:
    tool_dir = project_root / "DeepSeekAndDestroy" / "tools"
    tool_dir.mkdir(parents=True, exist_ok=True)
    names = [
        "context_checkpoint.py",
        "check_state.py",
        "_rules_snapshot.py",
        "wait_worker.py",
        "claude_worker_rewake.py",
    ]
    copied: list[str] = []
    for name in names:
        src = skill_root / "scripts" / name
        if not src.is_file():
            raise FileNotFoundError(f"required DSD helper missing: {src}")
        dst = tool_dir / name
        shutil.copy2(src, dst)
        copied.append(str(dst))
    return copied


def merge_claude_hooks(project_root: Path) -> str:
    settings = project_root / ".claude" / "settings.json"
    data: dict = {}
    if settings.is_file():
        data = json.loads(settings.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Claude settings must be a JSON object: {settings}")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Claude settings hooks must be an object")

    def ensure(event: str, entry: dict) -> None:
        rows = hooks.setdefault(event, [])
        if not isinstance(rows, list):
            raise ValueError(f"Claude hooks.{event} must be a list")
        marker = "DeepSeekAndDestroy/tools"
        command = entry["hooks"][0]["command"]
        for existing in rows:
            for handler in existing.get("hooks", []):
                if marker in str(handler.get("command", "")) and handler.get("command") == command:
                    return
        rows.append(entry)

    checkpoint = str((project_root / "DeepSeekAndDestroy" / "tools" / "context_checkpoint.py").resolve())
    ensure(
        "PreCompact",
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f'python3 "{checkpoint}" --project-root "{project_root}" hook --harness claude-code --event precompact',
                    "timeout": 30,
                    "statusMessage": "Checkpointing DSD run",
                }
            ]
        },
    )
    ensure(
        "PostCompact",
        {
            "hooks": [
                {
                    "type": "command",
                    "command": f'python3 "{checkpoint}" --project-root "{project_root}" hook --harness claude-code --event postcompact',
                    "timeout": 30,
                    "statusMessage": "Recording DSD compaction",
                }
            ]
        },
    )
    ensure(
        "SessionStart",
        {
            "matcher": "^(compact|resume)$",
            "hooks": [
                {
                    "type": "command",
                    "command": f'python3 "{checkpoint}" --project-root "{project_root}" hook --harness claude-code --event sessionstart',
                    "timeout": 30,
                    "statusMessage": "Reloading DSD run",
                }
            ],
        },
    )
    write_json(settings, data)
    return str(settings)


def install_claude(skill_root: Path, project_root: Path) -> dict:
    helpers = install_helpers(skill_root, project_root)
    settings = merge_claude_hooks(project_root)
    return {
        "harness": "claude-code",
        "worker_transport": "opencode-cli",
        "wait_mode": "native-background-task-or-async-rewake",
        "settings": settings,
        "helpers": helpers,
        "note": (
            "Launch run_worker.py as a Claude background Bash task when available. "
            "Claude's native task completion wakes the orchestrator; do not poll. "
            "For detached external launches, use wait_worker.py or an async hook wrapper "
            "with claude_worker_rewake.py."
        ),
    }


def install_generic(skill_root: Path, project_root: Path, harness: str) -> dict:
    helpers = install_helpers(skill_root, project_root)
    return {
        "harness": harness,
        "worker_transport": "opencode-cli",
        "wait_mode": "blocking-terminal-event",
        "helpers": helpers,
        "note": "Use the strongest native blocking/background-task primitive available; otherwise wait_worker.py blocks on DSD terminal-event state with sparse fallback checks.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--harness", required=True, choices=["claude-code", "codex", "opencode", "generic"])
    parser.add_argument("--out")
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    skill_root = Path(args.skill_root).expanduser().resolve()
    if args.harness == "claude-code":
        result = install_claude(skill_root, project_root)
    else:
        result = install_generic(skill_root, project_root, args.harness)

    if args.out:
        write_json(Path(args.out).expanduser().resolve(), result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
