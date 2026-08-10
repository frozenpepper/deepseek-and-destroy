#!/usr/bin/env python3
"""Install the optional contributed Kilo DSD compaction adapter project-locally."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def git_root(start: Path) -> Path:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return Path(out).resolve() if out else start.resolve()
    except Exception:
        return start.resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, default=Path.cwd())
    ap.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = ap.parse_args()
    project = git_root(args.project_root)
    skill = args.skill_root.resolve()
    contrib = Path(__file__).resolve().parent
    try:
        plugin_src = contrib / "dsd-compaction.ts"
        plugin_dst = project / ".kilo" / "plugins" / "dsd-compaction.ts"
        plugin_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plugin_src, plugin_dst)
        tools = project / "DeepSeekAndDestroy" / "tools"
        tools.mkdir(parents=True, exist_ok=True)
        for name in ("context_checkpoint.py", "check_state.py"):
            src = skill / "scripts" / name
            dst = tools / name
            shutil.copy2(src, dst)
            dst.chmod(0o755)
        print(plugin_dst)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
