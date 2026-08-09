#!/usr/bin/env python3
"""Install the best project-local DSD compaction adapter for the orchestrator harness.

The installer is idempotent and backs up changed JSON configuration files. It
never edits user-global harness configuration.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

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


def parent_commands(limit: int = 8) -> str:
    commands: list[str] = []
    pid = os.getpid()
    for _ in range(limit):
        try:
            out = subprocess.check_output(["ps", "-o", "ppid=,command=", "-p", str(pid)], text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            break
        parts = out.split(None, 1)
        if len(parts) != 2:
            break
        ppid, command = parts
        commands.append(command.lower())
        try:
            pid = int(ppid)
        except ValueError:
            break
        if pid <= 1:
            break
    return "\n".join(commands)


def detect_harness(explicit: str | None) -> str:
    if explicit and explicit != "auto":
        return explicit
    env = os.environ
    commands = parent_commands()
    signals = {
        "codex": int(bool(env.get("CODEX_HOME") or env.get("CODEX_THREAD_ID"))) * 5 + int("codex" in commands) * 8,
        "claude-code": int(bool(env.get("CLAUDE_PROJECT_DIR") or env.get("CLAUDE_ENV_FILE"))) * 5 + int("claude" in commands) * 8,
        "opencode": int(bool(env.get("OPENCODE_DB") or env.get("OPENCODE_CONFIG"))) * 5 + int("opencode" in commands) * 8,
        "kilo": int(bool(env.get("KILO_BIN_PATH") or env.get("KILO_BWRAP_CACHE"))) * 5 + int("kilo" in commands) * 8,
    }
    ranked = sorted(signals.items(), key=lambda item: item[1], reverse=True)
    if ranked[0][1] <= 0 or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        raise RuntimeError("Harness detection is ambiguous; pass --harness codex|claude-code|opencode|kilo")
    return ranked[0][0]


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


def hook_group(matcher: str | None, command: str, status: str, context_limit: int | None = None) -> dict[str, Any]:
    handler: dict[str, Any] = {"type": "command", "command": command, "statusMessage": status, "timeout": 30}
    if context_limit is not None:
        handler["additionalContextLimit"] = context_limit
    group: dict[str, Any] = {"hooks": [handler]}
    if matcher:
        group["matcher"] = matcher
    return group


def ensure_hook(data: dict[str, Any], event: str, group: dict[str, Any]) -> bool:
    hooks = data.setdefault("hooks", {})
    groups = hooks.setdefault(event, [])
    for existing in groups:
        for handler in existing.get("hooks", []):
            if MARKER in str(handler.get("command", "")) and event.lower() in str(handler.get("command", "")).lower():
                if existing == group:
                    return False
                existing.clear(); existing.update(group); return True
    groups.append(group)
    return True


def install_helper(skill_root: Path, project_root: Path) -> Path:
    tools = project_root / "DeepSeekAndDestroy" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    for name in ("context_checkpoint.py", "check_state.py"):
        source = skill_root / "scripts" / name
        destination = tools / name
        shutil.copy2(source, destination)
        destination.chmod(0o755)
    return tools / "context_checkpoint.py"


def install_codex(project_root: Path) -> dict[str, Any]:
    path = project_root / ".codex" / "hooks.json"
    data = load_json(path)
    data.setdefault("description", "Project hooks including DeepSeek and Destroy continuity checkpoints")
    script = 'python3 "$(git rev-parse --show-toplevel)/DeepSeekAndDestroy/tools/context_checkpoint.py"'
    changed = False
    changed |= ensure_hook(data, "PreCompact", hook_group("^(manual|auto)$", f"{script} hook --harness codex --event precompact", "Preparing DSD context checkpoint"))
    changed |= ensure_hook(data, "PostCompact", hook_group("^(manual|auto)$", f"{script} hook --harness codex --event postcompact", "Recording DSD compaction"))
    changed |= ensure_hook(data, "SessionStart", hook_group("^(compact|resume)$", f"{script} hook --harness codex --event sessionstart", "Reloading DSD run state", 2200))
    backup_path = backup(path) if changed and path.exists() else None
    if changed: write_json(path, data)
    return {"harness": "codex", "config": str(path), "changed": changed, "backup": str(backup_path) if backup_path else None, "manual_step": "Open /hooks in Codex and trust the project-local hooks before relying on them."}


def install_claude(project_root: Path) -> dict[str, Any]:
    path = project_root / ".claude" / "settings.json"
    data = load_json(path)
    script = 'python3 "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}/DeepSeekAndDestroy/tools/context_checkpoint.py"'
    changed = False
    changed |= ensure_hook(data, "PreCompact", hook_group("^(manual|auto)$", f"{script} hook --harness claude-code --event precompact", "Preparing DSD context checkpoint"))
    changed |= ensure_hook(data, "PostCompact", hook_group("^(manual|auto)$", f"{script} hook --harness claude-code --event postcompact", "Recording DSD compaction"))
    changed |= ensure_hook(data, "SessionStart", hook_group("^(compact|resume)$", f"{script} hook --harness claude-code --event sessionstart", "Reloading DSD run state"))
    backup_path = backup(path) if changed and path.exists() else None
    if changed: write_json(path, data)
    return {"harness": "claude-code", "config": str(path), "changed": changed, "backup": str(backup_path) if backup_path else None}


def opencode_plugin_source() -> str:
    return r'''import type { Plugin } from "@opencode-ai/plugin"

export const DeepSeekAndDestroyCompaction: Plugin = async (ctx) => ({
  "experimental.session.compacting": async (_input, output) => {
    const root = process.env.DSD_PROJECT_ROOT || ctx.worktree || ctx.directory
    const script = `${root}/DeepSeekAndDestroy/tools/context_checkpoint.py`
    const prepare = Bun.spawnSync(["python3", script, "--project-root", root, "prepare", "--harness", "opencode", "--reason", "opencode-native-precompact"], { stdout: "pipe", stderr: "pipe" })
    if (prepare.exitCode === 4) return
    if (prepare.exitCode !== 0) {
      const stderr = new TextDecoder().decode(prepare.stderr).trim()
      output.context.push(`\n## DeepSeek and Destroy checkpoint warning\nCheckpoint preparation failed: ${stderr}\n`)
      return
    }
    const instruction = Bun.spawnSync(["python3", script, "--project-root", root, "instruction"], { stdout: "pipe", stderr: "pipe" })
    output.context.push(`\n## DeepSeek and Destroy durable continuation\n${new TextDecoder().decode(instruction.stdout).trim()}\n`)
  },
})
'''


def install_plugin(project_root: Path, harness: str, directory: str, source: str) -> dict[str, Any]:
    path = project_root / directory / "plugins" / "dsd-compaction.ts"
    changed = not path.exists() or path.read_text(encoding="utf-8") != source
    backup_path = backup(path) if changed and path.exists() else None
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return {"harness": harness, "plugin": str(path), "changed": changed, "backup": str(backup_path) if backup_path else None}


def install_opencode(project_root: Path) -> dict[str, Any]:
    result = install_plugin(project_root, "opencode", ".opencode", opencode_plugin_source())
    result["manual_step"] = "Restart/reload OpenCode so the project-local plugin is active; DSD verify-resume completes post-compaction continuity."
    return result


def kilo_plugin_source() -> str:
    return r'''import type { Plugin } from "@kilocode/plugin"

export const DeepSeekAndDestroyCompaction: Plugin = async (ctx) => ({
  "experimental.session.compacting": async (_input, output) => {
    const root = process.env.DSD_PROJECT_ROOT || ctx.worktree || ctx.directory
    const script = `${root}/DeepSeekAndDestroy/tools/context_checkpoint.py`
    const prepare = Bun.spawnSync(["python3", script, "--project-root", root, "prepare", "--harness", "kilo", "--reason", "kilo-native-precompact"], { stdout: "pipe", stderr: "pipe" })
    if (prepare.exitCode === 4) return
    if (prepare.exitCode !== 0) {
      const stderr = new TextDecoder().decode(prepare.stderr).trim()
      output.context.push(`\n## DeepSeek and Destroy checkpoint warning\nCheckpoint preparation failed: ${stderr}\n`)
      return
    }
    const instruction = Bun.spawnSync(["python3", script, "--project-root", root, "instruction"], { stdout: "pipe", stderr: "pipe" })
    output.context.push(`\n## DeepSeek and Destroy durable continuation\n${new TextDecoder().decode(instruction.stdout).trim()}\n`)
  },
})
'''


def install_kilo(project_root: Path) -> dict[str, Any]:
    result = install_plugin(project_root, "kilo", ".kilo", kilo_plugin_source())
    result["manual_step"] = "Before trusting automatic Kilo compaction for an irreplaceable run, observe a real compaction creating a DSD checkpoint; otherwise use KILOCODE.md manual/fresh-session continuity."
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
        harness = detect_harness(args.harness)
        helper = install_helper(skill_root, project_root)
        if harness == "codex": result = install_codex(project_root)
        elif harness == "claude-code": result = install_claude(project_root)
        elif harness == "kilo": result = install_kilo(project_root)
        else: result = install_opencode(project_root)
        result.update({"project_root": str(project_root), "helper": str(helper), "installed_at": utc_stamp()})
        report = project_root / "DeepSeekAndDestroy" / "compaction-adapter-installation.md"
        report.write_text("# DeepSeek and Destroy Compaction Adapter\n\n```json\n" + json.dumps(result, indent=2) + "\n```\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
