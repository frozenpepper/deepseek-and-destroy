#!/usr/bin/env python3
"""Bind a harness-native DSD subagent call to the normal immutable attempt lifecycle.

Use `reserve` immediately before invoking a native subagent/Task tool, then
`finalize` exactly once after that tool returns. The native tool return is the
terminal boundary; semantic PASS/FAIL remains in the worker report and is handled
by the ordinary evidence gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from _roles import ROLE_NAMES
from _rules_snapshot import sha256_file, verify_snapshot
from run_worker import atomic_json, now, reserve_attempt


def absolute(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute: {path}")
    return path.resolve()


def reserve(args: argparse.Namespace) -> int:
    project = absolute(args.project_root, "project-root")
    run = absolute(args.run_root, "run-root")
    if not project.is_dir() or not run.is_dir():
        raise ValueError("project-root and run-root must exist")
    try:
        run.relative_to(project / "DeepSeekAndDestroy")
    except ValueError as exc:
        raise ValueError(f"run-root must live under {project / 'DeepSeekAndDestroy'}") from exc

    paths = {
        "project_root": project,
        "run_root": run,
        "prompt": absolute(args.prompt_file, "prompt-file"),
        "task_contract": absolute(args.task_contract, "task-contract"),
        "worker_rules": absolute(args.worker_rules, "worker-rules"),
        "scope_baseline": absolute(args.scope_baseline, "scope-baseline"),
        "report": absolute(args.report, "report"),
        "event_dir": absolute(args.event_dir, "event-dir"),
        "log": absolute(args.log, "log"),
    }
    for label in ("prompt", "task_contract", "worker_rules", "scope_baseline"):
        if not paths[label].is_file():
            raise ValueError(f"{label} missing: {paths[label]}")
    if paths["worker_rules"].name != "WORKER_RULES.md":
        raise ValueError("worker-rules path must name WORKER_RULES.md")
    snapshot = verify_snapshot(paths["worker_rules"])
    paths["worker_rules_manifest"] = Path(snapshot["manifest"]).resolve()
    try:
        paths["worker_rules"].relative_to(run / "worker-rules")
    except ValueError as exc:
        raise ValueError("worker-rules must live under the run worker-rules tree") from exc
    for label in ("prompt", "task_contract", "scope_baseline", "report", "event_dir", "log"):
        try:
            paths[label].relative_to(run)
        except ValueError as exc:
            raise ValueError(f"{label} is outside run-root: {paths[label]}") from exc
    if args.attempt < 1:
        raise ValueError("attempt must be >= 1")

    shim = SimpleNamespace(task_id=args.task_id, role=args.role, attempt=args.attempt)
    reserved_at, error = reserve_attempt(shim, paths)
    if error or reserved_at is None:
        raise ValueError(error or "attempt reservation failed")
    reservation = paths["event_dir"] / "launch-reservation.json"
    reservation_sha = sha256_file(reservation)
    paths["log"].parent.mkdir(parents=True, exist_ok=True)
    paths["log"].write_text(
        f"DSD native worker reserved for harness={args.harness} at {reserved_at}\n",
        encoding="utf-8",
    )
    atomic_json(paths["event_dir"] / "attempt.json", {
        "format": "dsd-worker-attempt-v3",
        "task_id": args.task_id,
        "role": args.role,
        "attempt": args.attempt,
        "transport": f"{args.harness}-native",
        "launch_reservation": str(reservation),
        "launch_reservation_sha256": reservation_sha,
        "reserved_at": reserved_at,
        "started_at": now(),
    })
    print(json.dumps({
        "status": "reserved",
        "harness": args.harness,
        "event_dir": str(paths["event_dir"]),
        "launch_reservation": str(reservation),
        "launch_reservation_sha256": reservation_sha,
        "report": str(paths["report"]),
        "log": str(paths["log"]),
    }, indent=2))
    return 0


def finalize(args: argparse.Namespace) -> int:
    event_dir = absolute(args.event_dir, "event-dir")
    reservation_path = event_dir / "launch-reservation.json"
    attempt_path = event_dir / "attempt.json"
    terminal_path = event_dir / "terminal.json"
    if terminal_path.exists():
        raise ValueError(f"terminal event already exists: {terminal_path}")
    if not reservation_path.is_file() or not attempt_path.is_file():
        raise ValueError("native attempt is not reserved: launch-reservation.json/attempt.json missing")
    reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    reservation_sha = sha256_file(reservation_path)
    if attempt.get("launch_reservation_sha256") != reservation_sha:
        raise ValueError("immutable launch reservation changed after native reservation")
    role = str(reservation.get("role", ""))
    if role not in ROLE_NAMES:
        raise ValueError(f"invalid reserved role: {role!r}")
    status = args.status
    exit_code = 0 if status == "completed" else (args.exit_code if args.exit_code is not None else 1)
    terminal = {
        "format": "dsd-worker-terminal-v3",
        "status": status,
        "task_id": reservation.get("task_id"),
        "role": role,
        "attempt": reservation.get("attempt"),
        "transport": attempt.get("transport", "native"),
        "exit_code": exit_code,
        "session_id": args.session_id,
        "error": args.error,
        "launch_reservation": str(reservation_path),
        "launch_reservation_sha256": reservation_sha,
        "reserved_at": reservation.get("reserved_at"),
        "started_at": attempt.get("started_at"),
        "ended_at": now(),
    }
    atomic_json(terminal_path, terminal)
    try:
        with Path(reservation["log"]).open("a", encoding="utf-8") as handle:
            handle.write(f"DSD native worker terminal status={status} exit_code={exit_code} at {terminal['ended_at']}\n")
    except OSError:
        # The immutable terminal event is authoritative; logging is diagnostic only.
        pass
    print(json.dumps(terminal, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("reserve", help="reserve immutable attempt authority before native Task invocation")
    r.add_argument("--harness", required=True)
    r.add_argument("--project-root", type=Path, required=True)
    r.add_argument("--run-root", type=Path, required=True)
    r.add_argument("--task-id", required=True)
    r.add_argument("--role", choices=sorted(ROLE_NAMES), required=True)
    r.add_argument("--attempt", type=int, default=1)
    r.add_argument("--prompt-file", type=Path, required=True)
    r.add_argument("--task-contract", type=Path, required=True)
    r.add_argument("--worker-rules", type=Path, required=True)
    r.add_argument("--scope-baseline", type=Path, required=True)
    r.add_argument("--report", type=Path, required=True)
    r.add_argument("--event-dir", type=Path, required=True)
    r.add_argument("--log", type=Path, required=True)
    f = sub.add_parser("finalize", help="write terminal event after native Task invocation returns")
    f.add_argument("--event-dir", type=Path, required=True)
    f.add_argument("--status", choices=("completed", "process-error", "transport-error"), required=True)
    f.add_argument("--exit-code", type=int)
    f.add_argument("--session-id")
    f.add_argument("--error")
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        return reserve(args) if args.command == "reserve" else finalize(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
