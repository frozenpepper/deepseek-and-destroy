#!/usr/bin/env python3
"""Claude async hook helper for DSD OpenCode worker completion wakeups."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="Path to DSD terminal-event.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    event_path = Path(args.event).expanduser().resolve()
    if not event_path.is_file():
        print(f"DSD worker completion event missing: {event_path}", file=sys.stderr)
        return 0
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"DSD worker completion event unreadable: {exc}", file=sys.stderr)
        return 0

    role = str(event.get("role") or "worker")
    task = str(event.get("task_id") or event.get("title") or "unknown-task")
    exit_code = event.get("exit_code")
    report = event.get("report_path") or "unknown-report"
    print(f"DSD {role} finished for {task} (exit {exit_code}). Reconcile {report} through the Evidence Gate.", file=sys.stderr)
    # Claude async hook convention: exit 2 wakes/interjects into an idle session.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
