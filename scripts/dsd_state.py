#!/usr/bin/env python3
"""Perform small validated DSD state transitions without hand-written JSON heredocs.

This is intentionally not a generic JSON patcher. It exposes only common mechanical
transitions while preserving semantic decisions in the orchestrator. Every mutation
is written to a sibling candidate file, checked with check_state.py, then atomically
replaces state.json only when mechanically valid.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from _roles import role_is_project_writer
from _task_contract import allowed_source_changes


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_absolute():
        raise ValueError("--state must be absolute")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("state.json must contain one object")
    return data


def task_ref(state: dict[str, Any], phase_id: str, task_id: str) -> dict[str, Any]:
    try:
        task = state["phases"][phase_id]["tasks"][task_id]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"state has no task {phase_id}/{task_id}") from exc
    if not isinstance(task, dict):
        raise ValueError(f"state task {phase_id}/{task_id} is not an object")
    return task


def set_next(state: dict[str, Any], next_action: str) -> None:
    if not next_action.strip():
        raise ValueError("next_action cannot be empty")
    state["next_action"] = next_action.strip()


def commit_checked(state_path: Path, state: dict[str, Any], check_state: Path) -> None:
    candidate = state_path.with_name(state_path.name + ".candidate")
    if candidate.exists():
        candidate.unlink()
    candidate.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cp = subprocess.run([sys.executable, str(check_state), str(candidate)], text=True, capture_output=True, check=False)
    if cp.returncode != 0:
        candidate.unlink(missing_ok=True)
        message = (cp.stdout or cp.stderr).strip()
        raise ValueError("candidate state failed check_state.py; original left untouched:\n" + message)
    os.replace(candidate, state_path)


def bind_contract(args: argparse.Namespace, state: dict[str, Any]) -> None:
    task = task_ref(state, args.phase, args.task)
    contract = args.contract.resolve()
    if not contract.is_file():
        raise ValueError(f"contract missing: {contract}")
    task["current_contract"] = {"revision": args.revision, "path": str(contract), "sha256": sha256_file(contract)}
    task["status"] = args.status
    if args.next_role:
        task["next_role"] = args.next_role
    set_next(state, args.next_action)


def bind_attempt(args: argparse.Namespace, state: dict[str, Any]) -> None:
    task = task_ref(state, args.phase, args.task)
    reservation_path = args.reservation.resolve()
    if not reservation_path.is_file():
        raise ValueError(f"launch reservation missing: {reservation_path}")
    reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    if reservation.get("task_id") != args.task:
        raise ValueError(f"reservation task_id {reservation.get('task_id')!r} != {args.task!r}")
    role = str(reservation.get("role", ""))
    attempt_no = reservation.get("attempt")
    if args.role and role != args.role:
        raise ValueError(f"reservation role {role!r} != requested {args.role!r}")
    if args.attempt is not None and attempt_no != args.attempt:
        raise ValueError(f"reservation attempt {attempt_no!r} != requested {args.attempt!r}")
    current_contract = task.get("current_contract") or {}
    contract_path = Path(str(reservation.get("task_contract", ""))).resolve()
    if current_contract and Path(str(current_contract.get("path", ""))).resolve() != contract_path:
        raise ValueError("reservation task contract does not match state current_contract")
    event_dir = reservation_path.parent
    attempt: dict[str, Any] = {
        "role": role,
        "attempt": attempt_no,
        "event_dir": str(event_dir),
        "launch_reservation": str(reservation_path),
        "launch_reservation_sha256": sha256_file(reservation_path),
        "terminal_event": str(event_dir / "terminal.json"),
        "writes_project": role_is_project_writer(role, allowed_source_changes(contract_path.read_text(encoding="utf-8", errors="replace"))),
        "launched_at": reservation.get("reserved_at"),
    }
    if args.worker_pid is not None:
        attempt["worker_pid"] = args.worker_pid
    if args.monitor_pid is not None:
        attempt["monitor_pid"] = args.monitor_pid
    if args.session_id:
        attempt["session_id"] = args.session_id
    if args.liveness:
        attempt["liveness"] = args.liveness
    task["current_attempt"] = attempt
    task["next_role"] = role
    task["status"] = args.status
    if isinstance(attempt_no, int):
        task["transport_attempts"] = max(int(task.get("transport_attempts", 0) or 0), attempt_no)
    set_next(state, args.next_action)



def mark_attempt(args: argparse.Namespace, state: dict[str, Any]) -> None:
    task = task_ref(state, args.phase, args.task)
    attempt = task.get("current_attempt") or {}
    if not isinstance(attempt, dict) or not attempt:
        raise ValueError(f"state task {args.phase}/{args.task} has no current_attempt")
    if args.status == "process-exited":
        terminal = Path(str(attempt.get("terminal_event", "")))
        if not terminal.is_absolute():
            terminal = args.state.parent / terminal
        if not terminal.exists():
            raise ValueError(f"cannot mark process-exited before terminal event exists: {terminal}")
    task["status"] = args.status
    if args.evidence_gate:
        gate = args.evidence_gate.resolve()
        if not gate.is_file():
            raise ValueError(f"evidence gate missing: {gate}")
        task["evidence_gate_path"] = str(gate)
    set_next(state, args.next_action)

def accept(args: argparse.Namespace, state: dict[str, Any]) -> None:
    task = task_ref(state, args.phase, args.task)
    if args.evidence_gate:
        gate_path = args.evidence_gate.resolve()
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("ok") is not True:
            raise ValueError("cannot accept from an evidence gate whose ok field is not true")
        contract = task.get("current_contract") or {}
        gate_task = gate.get("task")
        if gate_task and contract.get("path") and Path(str(gate_task)).resolve() != Path(str(contract["path"])).resolve():
            raise ValueError("acceptance evidence gate is bound to a different task contract")
        task["accepted_evidence_gate"] = str(gate_path)
        task["accepted_evidence_gate_sha256"] = sha256_file(gate_path)
    previous = task.pop("current_attempt", None)
    if previous:
        task["last_attempt"] = previous
    task["status"] = "accepted"
    task["next_role"] = args.next_role if args.next_role else None
    state.pop("orchestrator_wait", None)
    set_next(state, args.next_action)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", type=Path, required=True)
    ap.add_argument("--check-state", type=Path, default=Path(__file__).resolve().with_name("check_state.py"))
    sub = ap.add_subparsers(dest="command", required=True)

    n = sub.add_parser("set-next")
    n.add_argument("--next-action", required=True)

    c = sub.add_parser("bind-contract")
    c.add_argument("--phase", required=True); c.add_argument("--task", required=True)
    c.add_argument("--contract", type=Path, required=True); c.add_argument("--revision", type=int, required=True)
    c.add_argument("--status", default="prepared"); c.add_argument("--next-role")
    c.add_argument("--next-action", required=True)

    b = sub.add_parser("bind-attempt")
    b.add_argument("--phase", required=True); b.add_argument("--task", required=True)
    b.add_argument("--reservation", type=Path, required=True); b.add_argument("--role")
    b.add_argument("--attempt", type=int); b.add_argument("--status", choices=("launching", "in-progress", "process-exited", "evidence-reconciliation"), default="in-progress")
    b.add_argument("--worker-pid", type=int); b.add_argument("--monitor-pid", type=int); b.add_argument("--session-id"); b.add_argument("--liveness", choices=("confirmed", "unknown"))
    b.add_argument("--next-action", required=True)

    m = sub.add_parser("mark-attempt")
    m.add_argument("--phase", required=True); m.add_argument("--task", required=True)
    m.add_argument("--status", choices=("process-exited", "evidence-reconciliation"), required=True)
    m.add_argument("--evidence-gate", type=Path)
    m.add_argument("--next-action", required=True)

    a = sub.add_parser("accept")
    a.add_argument("--phase", required=True); a.add_argument("--task", required=True)
    a.add_argument("--evidence-gate", type=Path); a.add_argument("--next-role")
    a.add_argument("--next-action", required=True)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        state_path = args.state.resolve() if args.state.is_absolute() else args.state
        state = load_state(state_path)
        if args.command == "set-next": set_next(state, args.next_action)
        elif args.command == "bind-contract": bind_contract(args, state)
        elif args.command == "bind-attempt": bind_attempt(args, state)
        elif args.command == "mark-attempt": mark_attempt(args, state)
        elif args.command == "accept": accept(args, state)
        else: raise ValueError(f"unknown command {args.command}")
        commit_checked(state_path, state, args.check_state.resolve())
        print(json.dumps({"status": "updated", "command": args.command, "state": str(state_path), "next_action": state.get("next_action")}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
