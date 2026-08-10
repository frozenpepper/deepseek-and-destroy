#!/usr/bin/env python3
"""Rewake Claude Code when a detached DSD OpenCode worker reaches terminal state.

Installed as a Claude Code PostToolUse:Bash command hook with asyncRewake=true.
For ordinary Bash calls it exits immediately. When the Bash result is the JSON
emitted by `run_worker.py --detach`, it waits cheaply on that attempt's
`terminal.json` and exits 2 with a tiny system reminder. Claude Code's documented
asyncRewake behavior then wakes an idle Claude without model-level polling.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def launched_event_path(payload: dict[str, Any]) -> Path | None:
    if str(payload.get("tool_name", "")) != "Bash":
        return None
    response = payload.get("tool_response")
    candidates: list[str] = []
    if isinstance(response, dict):
        stdout = response.get("stdout")
        if isinstance(stdout, str):
            candidates.append(stdout)
    elif isinstance(response, str):
        candidates.append(response)

    for text in candidates:
        fragments = [text.strip(), *[line.strip() for line in text.splitlines()[::-1]]]
        seen: set[str] = set()
        for fragment in fragments:
            if not fragment or fragment in seen:
                continue
            seen.add(fragment)
            try:
                value = json.loads(fragment)
            except Exception:
                continue
            if not isinstance(value, dict) or value.get("status") != "launched":
                continue
            terminal = value.get("terminal_event")
            if isinstance(terminal, str) and terminal.strip():
                return Path(terminal)
    return None


def safe_terminal(path: Path, payload: dict[str, Any]) -> Path | None:
    if not path.is_absolute():
        return None
    terminal = path.resolve()
    root_value = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
    if not isinstance(root_value, str) or not root_value.strip():
        return None
    project = Path(root_value).resolve()
    durable = project / "DeepSeekAndDestroy"
    try:
        terminal.relative_to(durable)
    except ValueError:
        return None
    return terminal


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(__doc__ or "Claude Code async re-wake hook helper.")
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    event = launched_event_path(payload)
    if event is None:
        return 0
    terminal = safe_terminal(event, payload)
    if terminal is None:
        return 0

    try:
        timeout = float(os.environ.get("DSD_CLAUDE_REWAKE_TIMEOUT_SECONDS", "604700"))
    except ValueError:
        timeout = 604700.0
    deadline = time.monotonic() + max(1.0, timeout)
    while time.monotonic() < deadline:
        if terminal.is_file():
            try:
                data = json.loads(terminal.read_text(encoding="utf-8"))
                status = str(data.get("status", "unknown"))
            except Exception:
                status = "terminal-event-ready"
            print(
                "DSD external worker reached terminal state.\n"
                f"Terminal event: {terminal}\n"
                f"Status: {status}. Read/classify terminal.json and update state once; run the evidence gate only for a successful completed exit, then execute next_action.",
                file=sys.stderr,
            )
            return 2
        time.sleep(1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
