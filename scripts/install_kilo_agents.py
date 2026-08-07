#!/usr/bin/env python3
"""Install the role-separated DSD subagents for the Kilo Code worker profile.

Resolves the effective worker model and verifies it against `kilo models`
before writing anything, so a typo or unavailable model fails loudly instead
of being silently baked into an agent file. Project-local install is the
default; global install requires the explicit --global flag and is never
performed silently.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
AGENT_NAMES = ("dsd-mutating-worker", "dsd-readonly-worker")


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git_root(start: Path) -> Path:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
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


def resolve_model(explicit: str | None) -> str:
    return explicit or DEFAULT_MODEL


def verify_model(model: str) -> None:
    """Fail loudly if `model` is not an id kilo actually reports, rather than
    baking an unresolvable model into a committed agent file."""
    if not shutil.which("kilo"):
        raise RuntimeError("`kilo` executable not found on PATH. Install with: npm install -g @kilocode/cli")
    try:
        result = subprocess.run(
            ["kilo", "models"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("`kilo models` timed out") from exc
    tokens = set(re.findall(r"[A-Za-z0-9._:~-]+(?:/[A-Za-z0-9._:~-]+){1,2}", result.stdout))
    if model not in tokens:
        close = sorted(t for t in tokens if model.split("/")[-1].split("-")[0] in t)
        hint = f" Similar available ids: {', '.join(close[:8])}" if close else ""
        raise RuntimeError(
            f"model '{model}' not found in `kilo models` output.{hint} "
            "Run `kilo auth` if the provider needs a credential, then retry."
        )


def render_agent(template_path: Path, model: str) -> str:
    return template_path.read_text(encoding="utf-8").replace("{{MODEL}}", model)


def install_agents(skill_root: Path, target_dir: Path, model: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    template_dir = skill_root / "adapters" / "kilo" / "agents"
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in AGENT_NAMES:
        template = template_dir / f"{name}.md"
        if not template.exists():
            raise RuntimeError(f"missing template: {template}")
        rendered = render_agent(template, model)
        destination = target_dir / f"{name}.md"
        changed = not destination.exists() or destination.read_text(encoding="utf-8") != rendered
        backup_path = backup(destination) if changed and destination.exists() else None
        if changed:
            destination.write_text(rendered, encoding="utf-8")
        results.append(
            {
                "agent": name,
                "path": str(destination),
                "changed": changed,
                "backup": str(backup_path) if backup_path else None,
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--model", default=None, help=f"provider/model id (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--global",
        dest="do_global",
        action="store_true",
        help="also install to ~/.config/kilo/agents/ (never done by default; "
        "the skill does not silently modify global configuration)",
    )
    parser.add_argument(
        "--skip-model-verify",
        action="store_true",
        help="skip the `kilo models` existence check (not recommended)",
    )
    args = parser.parse_args()

    project_root = git_root(args.project_root)
    skill_root = args.skill_root.resolve()
    model = resolve_model(args.model)

    try:
        if not args.skip_model_verify:
            verify_model(model)

        installs: list[dict[str, object]] = []
        project_target = project_root / ".kilo" / "agents"
        installs.extend(
            {**entry, "scope": "project"} for entry in install_agents(skill_root, project_target, model)
        )

        if args.do_global:
            global_target = Path.home() / ".config" / "kilo" / "agents"
            installs.extend(
                {**entry, "scope": "global"} for entry in install_agents(skill_root, global_target, model)
            )

        result = {
            "model": model,
            "model_verified": not args.skip_model_verify,
            "project_root": str(project_root),
            "global_install": args.do_global,
            "agents": installs,
            "installed_at": utc_stamp(),
            "next_step": "Confirm with `kilo agent list` that dsd-mutating-worker and "
            "dsd-readonly-worker appear (subagent), then delegate via the orchestrator's "
            "task tool per KILOCODE.md.",
        }
        report_dir = project_root / "DeepSeekAndDestroy"
        report_dir.mkdir(parents=True, exist_ok=True)
        report = report_dir / "kilo-agent-installation.md"
        report.write_text(
            "# DeepSeek and Destroy Kilo Agent Installation\n\n```json\n"
            + __import__("json").dumps(result, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        print(__import__("json").dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
