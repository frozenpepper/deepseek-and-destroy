#!/usr/bin/env python3
"""Install DSD's role-separated Kilo Code subagents."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
AGENTS = ("dsd-mutating-worker", "dsd-readonly-worker")


def stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git_root(start: Path) -> Path:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Path(out).resolve() if out else start.resolve()
    except Exception:
        return start.resolve()


def verify_model(model: str) -> None:
    if not shutil.which("kilo"):
        raise RuntimeError("`kilo` executable not found on PATH")
    try:
        result = subprocess.run(
            ["kilo", "models"], text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=60, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("`kilo models` timed out") from exc
    if result.returncode != 0:
        tail = result.stdout[-2000:] if result.stdout else ""
        raise RuntimeError(f"`kilo models` exited {result.returncode}: {tail}")
    tokens = set(re.findall(r"[A-Za-z0-9._:~-]+(?:/[A-Za-z0-9._:~-]+){1,2}", result.stdout))
    if model not in tokens:
        raise RuntimeError(
            f"model '{model}' not found in `kilo models`; configure auth/provider or choose an available id"
        )


def backup(path: Path) -> str | None:
    if not path.exists():
        return None
    dst = path.with_name(path.name + f".dsd-backup-{stamp()}")
    shutil.copy2(path, dst)
    return str(dst)


def install_set(skill_root: Path, target: Path, model: str) -> list[dict[str, object]]:
    template_dir = skill_root / "adapters" / "kilo" / "agents"
    target.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, object]] = []
    for name in AGENTS:
        template = template_dir / f"{name}.md"
        if not template.exists():
            raise RuntimeError(f"missing Kilo template: {template}")
        rendered = template.read_text(encoding="utf-8").replace("{{MODEL}}", model)
        destination = target / f"{name}.md"
        changed = not destination.exists() or destination.read_text(encoding="utf-8") != rendered
        old = backup(destination) if changed else None
        if changed:
            destination.write_text(rendered, encoding="utf-8")
        out.append({"agent": name, "path": str(destination), "changed": changed, "backup": old})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--global", dest="global_install", action="store_true")
    parser.add_argument("--skip-model-verify", action="store_true")
    args = parser.parse_args()

    project = git_root(args.project_root)
    skill = args.skill_root.resolve()
    try:
        if not args.skip_model_verify:
            verify_model(args.model)
        entries = [
            {**e, "scope": "project"}
            for e in install_set(skill, project / ".kilo" / "agents", args.model)
        ]
        if args.global_install:
            entries.extend(
                {**e, "scope": "global"}
                for e in install_set(skill, Path.home() / ".config" / "kilo" / "agents", args.model)
            )
        result = {
            "model": args.model,
            "model_verified": not args.skip_model_verify,
            "project_root": str(project),
            "global_install": args.global_install,
            "agents": entries,
            "installed_at": stamp(),
            "next_step": "Run `kilo agent list` and confirm both DSD subagents are registered.",
        }
        report_dir = project / "DeepSeekAndDestroy"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "kilo-agent-installation.md").write_text(
            "# DeepSeek and Destroy Kilo Agent Installation\n\n```json\n"
            + json.dumps(result, indent=2) + "\n```\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
