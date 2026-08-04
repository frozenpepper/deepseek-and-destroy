#!/usr/bin/env python3
"""Validate DeepSeek and Destroy run-state invariants.

This is an operational consistency check, not a replacement for orchestrator
judgment. It catches impossible states such as `in-progress` without a real
attempt or `waiting-for-worker` without a next probe.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

TERMINAL = {"completed", "human-blocked", "paused-by-user", "abandoned"}


def existing(path_value: Any, base: Path) -> bool:
    if not isinstance(path_value, str) or not path_value.strip():
        return False
    path = Path(path_value)
    if not path.is_absolute():
        path = base / path
    return path.exists()


def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def validate_task(task_id: str, task: dict[str, Any], base: Path) -> list[str]:
    errors: list[str] = []
    status = str(task.get("status", ""))
    attempts = task.get("transport_attempts", 0)
    prompt_path = task.get("prompt_path") or task.get("task_path")
    report_path = task.get("report_path")
    attempt = task.get("current_attempt") or {}

    if status == "prepared":
        if not existing(prompt_path, base):
            errors.append(f"{task_id}: prepared but audited prompt/task artifact is missing")

    if status in {"launching", "in-progress"}:
        if not isinstance(attempts, int) or attempts < 1:
            errors.append(f"{task_id}: {status} requires transport_attempts >= 1")
        if not existing(prompt_path, base):
            errors.append(f"{task_id}: {status} requires an existing prompt/task artifact")
        identity = attempt.get("pid") or attempt.get("harness_run_id") or attempt.get("session_id")
        if not identity:
            errors.append(f"{task_id}: {status} requires a real worker identity")
        if not attempt.get("launched_at"):
            errors.append(f"{task_id}: {status} requires launched_at")

    if status == "in-progress":
        liveness = str(attempt.get("liveness", "")).lower() == "confirmed"
        if attempt.get("pid"):
            live = pid_alive(attempt.get("pid")) and liveness
        else:
            live = bool(attempt.get("harness_run_id") or attempt.get("session_id")) and liveness
        report_complete = bool(task.get("report_complete")) and existing(report_path, base)
        if not ((live and liveness) or report_complete):
            errors.append(
                f"{task_id}: in-progress requires a live confirmed worker or a complete existing report"
            )

    if status == "waiting-for-worker":
        if not task.get("next_probe_at"):
            errors.append(f"{task_id}: waiting-for-worker requires next_probe_at")
        if not task.get("worker_profile") and not task.get("role_profile"):
            errors.append(f"{task_id}: waiting-for-worker requires a worker profile")

    if status == "process-exited" and not attempt.get("exited_at"):
        errors.append(f"{task_id}: process-exited requires exited_at")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path, help="Path to run state.json")
    parser.add_argument("--for-turn-exit", action="store_true", help="Also require a live worker, active wait/probe, or terminal state")
    args = parser.parse_args()

    state_path = args.state.resolve()
    try:
        state = json.loads(state_path.read_text())
    except Exception as exc:
        print(f"ERROR: cannot read {state_path}: {exc}", file=sys.stderr)
        return 2

    base = state_path.parent
    errors: list[str] = []

    status = str(state.get("execution_status", "")).lower()
    next_action = state.get("next_action")
    if status not in TERMINAL and not isinstance(next_action, str):
        errors.append("active run requires a string next_action")
    elif status not in TERMINAL and not next_action.strip():
        errors.append("active run requires a non-empty next_action")

    availability = state.get("worker_availability") or {}
    if availability.get("status") == "waiting-for-worker" and not availability.get("next_probe_at"):
        errors.append("worker_availability waiting-for-worker requires next_probe_at")

    any_live = False
    for phase_id, phase in (state.get("phases") or {}).items():
        for task_id, task in (phase.get("tasks") or {}).items():
            if isinstance(task, dict):
                errors.extend(validate_task(f"{phase_id}/{task_id}", task, base))
                attempt = task.get("current_attempt") or {}
                if task.get("status") == "in-progress" and str(attempt.get("liveness", "")).lower() == "confirmed":
                    if attempt.get("pid"):
                        any_live = any_live or pid_alive(attempt.get("pid"))
                    else:
                        any_live = any_live or bool(attempt.get("harness_run_id") or attempt.get("session_id"))

    if args.for_turn_exit and status not in TERMINAL:
        waiting = availability.get("status") == "waiting-for-worker" and bool(availability.get("next_probe_at"))
        if not any_live and not waiting:
            errors.append("turn-exit invariant failed: active run has no live worker and no persisted wait/probe")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
