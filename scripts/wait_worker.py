#!/usr/bin/env python3
"""Block cheaply until a DSD worker terminal event appears.

The one-second filesystem check happens inside this cheap helper process; it does
not consume orchestrator turns. A timeout is intentionally a non-event so the
orchestrator can immediately re-enter the longest safe wait without inspection.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--event-dir", type=Path, required=True)
    ap.add_argument("--timeout", type=float, default=3600.0)
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    if not args.event_dir.is_absolute():
        print(json.dumps({"status": "invalid-config", "error": "--event-dir must be absolute"}))
        return 2
    terminal = args.event_dir.resolve() / "terminal.json"
    deadline = time.monotonic() + max(0.0, args.timeout)
    while True:
        if terminal.exists():
            try:
                data = json.loads(terminal.read_text(encoding="utf-8"))
            except Exception as exc:
                print(json.dumps({"status": "terminal-malformed", "event": str(terminal), "error": str(exc)}))
                return 2
            print(json.dumps({
                "status": data.get("status"),
                "exit_code": data.get("exit_code"),
                "task_id": data.get("task_id"),
                "role": data.get("role"),
                "report": data.get("report"),
                "session_id": data.get("session_id"),
                "event": str(terminal),
            }))
            return 0 if data.get("status") == "completed" and data.get("exit_code") == 0 else 1
        if time.monotonic() >= deadline:
            print(json.dumps({"status": "timeout", "event": str(terminal)}))
            return 3
        time.sleep(max(0.1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
