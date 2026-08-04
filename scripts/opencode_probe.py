#!/usr/bin/env python3
"""Run a minimal isolated OpenCode worker health probe."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROMPT = "Reply with exactly HEALTHCHECK OK and nothing else. Do not modify files."


def cleanup(db: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(str(db) + suffix).unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args()

    if not shutil.which("opencode"):
        print("PROBE ERROR: opencode executable not found", file=sys.stderr)
        return 2

    project_root = args.project_root.resolve()
    db = args.db.resolve()
    db.parent.mkdir(parents=True, exist_ok=True)

    try:
        models = subprocess.run(
            ["opencode", "models"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("PROBE ERROR: `opencode models` timed out", file=sys.stderr)
        return 3

    model_tokens = set(re.findall(r"[A-Za-z0-9._:-]+/[A-Za-z0-9._:-]+", models.stdout))
    if args.model not in model_tokens:
        print(f"PROBE ERROR: exact model id not present in `opencode models`: {args.model}")
        return 4

    env = os.environ.copy()
    env["OPENCODE_DB"] = str(db)
    title = f"dsd-healthcheck-{int(time.time())}"
    cmd = [
        "opencode", "run", "--model", args.model, "--auto", "--title", title,
        "--dir", str(project_root), PROMPT,
    ]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout_seconds,
            check=False,
        )
        output = result.stdout
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        print("PROBE ERROR: worker probe timed out", file=sys.stderr)
        if args.log:
            args.log.parent.mkdir(parents=True, exist_ok=True)
            args.log.write_text(output)
        return 5
    finally:
        if not args.keep_db:
            cleanup(db)

    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(output)

    ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    lines = [ansi.sub("", line).strip() for line in output.splitlines()]
    if result.returncode == 0 and "HEALTHCHECK OK" in lines:
        print("HEALTHCHECK OK")
        return 0

    print(f"PROBE FAIL: exit={result.returncode}")
    if output:
        print(output[-2000:])
    return 6


if __name__ == "__main__":
    raise SystemExit(main())
