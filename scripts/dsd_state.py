#!/usr/bin/env python3
"""Atomic state transactions for the DSD control plane.

The premium parent chooses contracts, roles, and semantic decisions. This helper only
serializes durable facts so the parent never hand-edits state.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any



def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_path(run_root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = run_root / path
    path = path.resolve()
    try:
        path.relative_to(run_root)
    except ValueError as exc:
        raise ValueError(f"path is outside run root: {path}") from exc
    return path


def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _attempt_event_dir(run_root: Path, attempt: dict[str, Any]) -> Path | None:
    raw = attempt.get("event_dir")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return run_path(run_root, raw)
    except ValueError:
        return None


def _attempt_terminal(run_root: Path, attempt: dict[str, Any]) -> Path | None:
    raw = attempt.get("terminal_event")
    if isinstance(raw, str) and raw.strip():
        try:
            return run_path(run_root, raw)
        except ValueError:
            return None
    event_dir = _attempt_event_dir(run_root, attempt)
    return (event_dir / "terminal.json") if event_dir is not None else None


def _attempt_live(attempt: dict[str, Any]) -> bool:
    return any(pid_alive(attempt.get(key)) for key in ("worker_pid", "monitor_pid", "launcher_pid"))


def archive_current_attempt(
    run_root: Path,
    task: dict[str, Any],
    *,
    allow_incomplete: bool = False,
) -> dict[str, Any] | None:
    """Move the current attempt into factual history without inventing a verdict.

    Terminal/gated attempts archive automatically. A terminal-less attempt archives only
    under an explicit supersede request; if any recorded process is still alive, refuse.
    """
    current = task.get("current_attempt")
    if not isinstance(current, dict):
        return None
    terminal = _attempt_terminal(run_root, current)
    terminal_exists = bool(terminal and terminal.is_file())
    status = str(current.get("status") or task.get("status") or "").lower()
    if not terminal_exists:
        if _attempt_live(current):
            raise ValueError("current attempt is still live; refusing to supersede it")
        if not allow_incomplete:
            raise ValueError(
                "current attempt has no terminal event; lifecycle is incomplete. "
                "Use --supersede-incomplete only after establishing that the old worker cannot still write."
            )
        archived_status = "lifecycle-incomplete"
        disposition = "superseded"
    else:
        archived_status = status or "process-exited"
        disposition = "completed" if archived_status not in {"integrity-failed", "report-recovery"} else archived_status

    entry = dict(current)
    entry["status"] = archived_status
    entry["disposition"] = disposition
    task["last_attempt"] = entry
    task.pop("current_attempt", None)
    return entry


def find_attempt_binding(run_root: Path, task: dict[str, Any], reservation: Path) -> tuple[dict[str, Any] | None, bool]:
    current = task.get("current_attempt")
    if isinstance(current, dict):
        event_dir = _attempt_event_dir(run_root, current)
        if event_dir is not None and event_dir / "launch-reservation.json" == reservation:
            return current, True
    last = task.get("last_attempt")
    if isinstance(last, dict):
        event_dir = _attempt_event_dir(run_root, last)
        if event_dir is not None and event_dir / "launch-reservation.json" == reservation:
            return last, False
    return None, False


def state_and_task(run_root: Path, phase_id: str, task_id: str, *, create: bool = False) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    state_path = run_root / "state.json"
    if not state_path.is_file():
        raise ValueError(f"state.json missing: {state_path}")
    state = load_json(state_path)
    phases = state.setdefault("phases", {}) if create else state.get("phases", {})
    if not isinstance(phases, dict):
        raise ValueError("state.phases is not an object")
    if create:
        phase = phases.setdefault(phase_id, {"status": "in-progress", "tasks": {}})
    else:
        phase = phases.get(phase_id)
        if not isinstance(phase, dict):
            raise ValueError(f"phase not found: {phase_id}")
    tasks = phase.setdefault("tasks", {}) if create else phase.get("tasks", {})
    if not isinstance(tasks, dict):
        raise ValueError(f"{phase_id}.tasks is not an object")
    if create:
        task = tasks.setdefault(task_id, {"status": "prepared"})
    else:
        task = tasks.get(task_id)
        if not isinstance(task, dict):
            raise ValueError(f"task not found: {phase_id}/{task_id}")
    return state_path, state, task


def contract_revision(text: str) -> int:
    match = re.search(r"^Contract revision:\s*r(\d+)\s*$", text, re.I | re.M)
    if not match:
        raise ValueError("contract lacks 'Contract revision: rNNNN'")
    return int(match.group(1))


def load_optional_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    data = json.load(sys.stdin) if raw == "-" else json.loads(Path(raw).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("launch JSON must be an object")
    return data


def bind_contract(args: argparse.Namespace) -> dict[str, Any]:
    run_root = args.run_root.resolve()
    state_path, state, task = state_and_task(run_root, args.phase_id, args.task_id, create=True)
    contract = run_path(run_root, args.contract)
    if not contract.is_file():
        raise ValueError(f"contract missing: {contract}")
    revision = contract_revision(contract.read_text(encoding="utf-8", errors="replace"))
    if isinstance(task.get("current_attempt"), dict):
        archive_current_attempt(run_root, task, allow_incomplete=args.supersede_incomplete)
    last_attempt = task.get("last_attempt") if isinstance(task.get("last_attempt"), dict) else None
    task.clear()
    task.update({
        "status": args.status,
        "current_contract": {"revision": revision, "path": str(contract), "sha256": sha256(contract)},
    })
    if last_attempt:
        task["last_attempt"] = last_attempt
    if args.next_action:
        state["next_action"] = args.next_action
    atomic_json(state_path, state)
    return {"task": f"{args.phase_id}/{args.task_id}", "contract": str(contract), "revision": revision, "status": task["status"], "next_action": state.get("next_action")}


def preflight_attempt(args: argparse.Namespace) -> dict[str, Any]:
    """Validate that a new attempt can be launched before any worker starts."""
    run_root = args.run_root.resolve()
    _, _, task = state_and_task(run_root, args.phase_id, args.task_id)
    intended = run_path(run_root, args.contract)
    current_contract = task.get("current_contract") or {}
    raw = current_contract.get("path")
    if not isinstance(raw, str):
        raise ValueError("task has no current_contract")
    bound = run_path(run_root, raw)
    if intended != bound:
        raise ValueError("launch contract does not match task.current_contract")
    if not intended.is_file() or sha256(intended) != current_contract.get("sha256"):
        raise ValueError("task.current_contract is missing or changed")

    current = task.get("current_attempt")
    if isinstance(current, dict):
        terminal = _attempt_terminal(run_root, current)
        if terminal is None or not terminal.is_file():
            if _attempt_live(current):
                raise ValueError("current attempt is still live; refusing to launch another worker for this task")
            if not args.supersede_incomplete:
                raise ValueError(
                    "current attempt has no terminal event; lifecycle is incomplete. "
                    "Use --supersede-incomplete only after establishing that the old worker cannot still write."
                )
    return {"task": f"{args.phase_id}/{args.task_id}", "ready": True}


def bind_attempt(args: argparse.Namespace) -> dict[str, Any]:
    run_root = args.run_root.resolve()
    state_path, state, task = state_and_task(run_root, args.phase_id, args.task_id)
    event_dir = run_path(run_root, args.event_dir)
    reservation_path = event_dir / "launch-reservation.json"
    if not reservation_path.is_file():
        raise ValueError(f"launch reservation missing: {reservation_path}")
    reservation = load_json(reservation_path)
    reservation_sha = sha256(reservation_path)
    launch = load_optional_json(args.launch_json)
    if launch:
        if launch.get("event_dir") and run_path(run_root, str(launch["event_dir"])) != event_dir:
            raise ValueError("launch JSON event_dir mismatch")
        if launch.get("launch_reservation_sha256") and str(launch["launch_reservation_sha256"]).lower() != reservation_sha:
            raise ValueError("launch JSON reservation hash mismatch")

    current_contract = task.get("current_contract") or {}
    if not isinstance(current_contract.get("path"), str):
        raise ValueError("task has no current_contract")
    current_contract_path = run_path(run_root, current_contract["path"])
    reservation_contract_raw = reservation.get("task_contract")
    if not isinstance(reservation_contract_raw, str):
        raise ValueError("reservation lacks task_contract")
    reservation_contract = run_path(run_root, reservation_contract_raw)
    if reservation_contract != current_contract_path:
        raise ValueError("reservation contract does not match task.current_contract")
    if reservation.get("task_contract_sha256") != current_contract.get("sha256"):
        raise ValueError("reservation contract hash does not match task.current_contract")

    prior = task.get("current_attempt")
    if isinstance(prior, dict):
        prior_dir = _attempt_event_dir(run_root, prior)
        if prior_dir is not None and prior_dir != event_dir:
            archive_current_attempt(run_root, task, allow_incomplete=args.supersede_incomplete)

    attempt_file = event_dir / "attempt.json"
    terminal_file = event_dir / "terminal.json"
    attempt_data = load_json(attempt_file) if attempt_file.is_file() else {}
    terminal_data = load_json(terminal_file) if terminal_file.is_file() else {}
    attempt_no = int(reservation.get("attempt") or 0)
    role = str(reservation.get("role") or "")
    if attempt_no < 1 or not role:
        raise ValueError("reservation lacks valid role/attempt")

    current: dict[str, Any] = {
        "role": role,
        "attempt": attempt_no,
        "event_dir": str(event_dir),
        "launch_reservation": str(reservation_path),
        "launch_reservation_sha256": reservation_sha,
        "terminal_event": str(terminal_file),
        "writes_project": bool(reservation.get("writes_project")),
        "launched_at": attempt_data.get("started_at") or reservation.get("reserved_at"),
    }
    for key in ("worker_pid", "launcher_pid", "session_id", "harness_run_id", "monitor_pid"):
        value = attempt_data.get(key) or terminal_data.get(key) or launch.get(key)
        if value is not None:
            current[key] = value
    if terminal_file.is_file():
        current["liveness"] = "terminal"; status = "process-exited"
        state["orchestrator_wait"] = {"active": False}
    elif attempt_file.is_file():
        current["liveness"] = "confirmed"; status = "in-progress"
    else:
        current["liveness"] = "launching"; status = "launching"
    current["status"] = status
    task["status"] = status
    task["current_attempt"] = current
    if args.next_action:
        state["next_action"] = args.next_action
    monitor_pid = current.get("monitor_pid")
    if status != "process-exited" and (args.wait_kind or monitor_pid):
        state["orchestrator_wait"] = {
            "active": True,
            "kind": args.wait_kind or "external-worker-terminal",
            "terminal_event": str(terminal_file),
            **({"monitor_pid": monitor_pid} if monitor_pid else {}),
        }
    atomic_json(state_path, state)
    return {"task": f"{args.phase_id}/{args.task_id}", "status": status, "role": role, "attempt": attempt_no, "terminal_event": str(terminal_file), "next_action": state.get("next_action")}


def bind_gate(args: argparse.Namespace) -> dict[str, Any]:
    run_root = args.run_root.resolve()
    state_path, state, task = state_and_task(run_root, args.phase_id, args.task_id)
    gate_path = run_path(run_root, args.gate)
    if not gate_path.is_file():
        raise ValueError(f"integrity gate missing: {gate_path}")
    gate = load_json(gate_path)
    gate_reservation_raw = gate.get("launch_reservation")
    if not isinstance(gate_reservation_raw, str):
        raise ValueError("integrity gate lacks launch_reservation binding")
    reservation = run_path(run_root, gate_reservation_raw)
    attempt, is_current = find_attempt_binding(run_root, task, reservation)
    if attempt is None:
        raise ValueError("integrity gate is not bound to any recorded task attempt")
    attempt["integrity_gate"] = {"path": str(gate_path), "sha256": sha256(gate_path)}
    if gate.get("integrity_ok") is True and gate.get("ready_for_interpretation") is True:
        status = "gated"
    elif gate.get("integrity_ok") is True and gate.get("needs_report_recovery") is True:
        status = "report-recovery"
    else:
        status = "integrity-failed"
    attempt["status"] = status
    if is_current:
        task["status"] = status
        state["orchestrator_wait"] = {"active": False}
    if args.next_action:
        state["next_action"] = args.next_action
    atomic_json(state_path, state)
    return {"task": f"{args.phase_id}/{args.task_id}", "status": status, "integrity_gate": str(gate_path), "current": is_current, "next_action": state.get("next_action")}


def _clean_gate(path: Path) -> dict[str, Any]:
    gate = load_json(path)
    if gate.get("integrity_ok") is not True or gate.get("errors"):
        raise ValueError(f"integrity gate is not clean: {path}")
    if gate.get("ready_for_interpretation") is not True:
        raise ValueError(f"report is not available for semantic consumption: {path}")
    return gate


def _attempt_changed_project(run_root: Path, attempt: Any) -> bool:
    """Whether one recorded attempt objectively changed project state."""
    if not isinstance(attempt, dict) or attempt.get("writes_project") is not True:
        return False
    gate_binding = attempt.get("integrity_gate")
    if not isinstance(gate_binding, dict) or not isinstance(gate_binding.get("path"), str):
        return False
    try:
        gate_path = run_path(run_root, gate_binding["path"])
        gate = load_json(gate_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    scope = gate.get("scope")
    return isinstance(scope, dict) and int(scope.get("changed_count") or 0) > 0


def _iso_time(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _terminal_scope_changed(run_root: Path, event_dir: Path, reservation: dict[str, Any]) -> tuple[bool, datetime | None]:
    """Return factual mutation + terminal time from cold immutable attempt evidence.

    New attempts use terminal-bound scope. Historical attempts fall back to an existing
    integrity gate; if neither can prove no movement, treat a writer as potentially
    mutating rather than weakening fresh-review provenance.
    """
    terminal_path = event_dir / "terminal.json"
    if not terminal_path.is_file():
        return bool(reservation.get("writes_project")), None
    terminal = load_json(terminal_path)
    ended = _iso_time(terminal.get("process_ended_at") or terminal.get("ended_at"))
    binding = terminal.get("terminal_scope")
    if isinstance(binding, dict) and isinstance(binding.get("path"), str):
        try:
            diff_path = run_path(run_root, binding["path"])
            expected_sha = binding.get("sha256")
            if not isinstance(expected_sha, str) or sha256(diff_path) != expected_sha.lower():
                return bool(reservation.get("writes_project")), ended
            data = load_json(diff_path)
            changed = bool(data.get("changed") or data.get("git_head_changed"))
            return changed, ended
        except (OSError, ValueError, json.JSONDecodeError):
            return bool(reservation.get("writes_project")), ended
    for gate_path in sorted(event_dir.glob("evidence-gate*.json")):
        try:
            gate = load_json(gate_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        scope = gate.get("scope")
        if isinstance(scope, dict):
            return bool(int(scope.get("changed_count") or 0) > 0 or scope.get("git_head_changed")), ended
    return bool(reservation.get("writes_project")), ended


def _reservation_matches_contract(run_root: Path, reservation: dict[str, Any], contract: Path, contract_sha: str) -> bool:
    raw = reservation.get("task_contract")
    if not isinstance(raw, str) or reservation.get("task_contract_sha256") != contract_sha:
        return False
    try:
        return run_path(run_root, raw) == contract
    except ValueError:
        return False


def _assert_fresh_reviewer(run_root: Path, contract: Path, source_gate: dict[str, Any]) -> None:
    if str(source_gate.get("role") or "").lower() != "reviewer":
        raise ValueError("recorded project mutation requires a fresh Reviewer integrity gate")
    terminal_raw = source_gate.get("terminal_event")
    if not isinstance(terminal_raw, str):
        raise ValueError("Reviewer gate lacks terminal-event provenance")
    reviewer_event = run_path(run_root, terminal_raw).parent
    reviewer_reservation_path = reviewer_event / "launch-reservation.json"
    if not reviewer_reservation_path.is_file():
        raise ValueError("Reviewer launch reservation missing")
    reviewer_reservation = load_json(reviewer_reservation_path)
    reviewer_started = _iso_time(reviewer_reservation.get("reserved_at"))
    if reviewer_started is None:
        raise ValueError("Reviewer launch time missing/invalid")

    task_root = contract.parent.parent
    contract_sha = sha256(contract)
    attempts_root = task_root / "attempts"
    if not attempts_root.is_dir():
        return
    for reservation_path in attempts_root.glob("*/launch-reservation.json"):
        event_dir = reservation_path.parent
        if event_dir == reviewer_event:
            continue
        try:
            reservation = load_json(reservation_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not _reservation_matches_contract(run_root, reservation, contract, contract_sha):
            continue
        if reservation.get("writes_project") is not True:
            continue
        changed, ended = _terminal_scope_changed(run_root, event_dir, reservation)
        if not changed:
            continue
        if ended is None:
            raise ValueError(f"project-writing attempt lacks terminal provenance: {event_dir}")
        if reviewer_started <= ended:
            raise ValueError(
                "fresh Reviewer requirement violated: accepted Reviewer predates later project mutation "
                f"in {event_dir.name}"
            )


def accept_task(args: argparse.Namespace) -> dict[str, Any]:
    """Persist the parent's acceptance; Python validates provenance only."""
    run_root = args.run_root.resolve()
    state_path, state, task = state_and_task(run_root, args.phase_id, args.task_id)
    source_gate_path = run_path(run_root, args.evidence_gate)
    source_gate = _clean_gate(source_gate_path)

    current_contract = task.get("current_contract") or {}
    contract_raw = current_contract.get("path")
    if not isinstance(contract_raw, str):
        raise ValueError("task has no current_contract")
    contract = run_path(run_root, contract_raw)
    if not contract.is_file() or sha256(contract) != current_contract.get("sha256"):
        raise ValueError("current contract missing or changed")
    source_task_raw = source_gate.get("task")
    if not isinstance(source_task_raw, str) or run_path(run_root, source_task_raw) != contract:
        raise ValueError("source gate is not bound to task.current_contract")
    source_scope = source_gate.get("scope")
    source_role = str(source_gate.get("role") or "").lower()
    source_can_write = source_gate.get("writes_project") is True or source_role in {"implementer", "fixer", "verification"}
    source_mutated = source_can_write and isinstance(source_scope, dict) and (
        int(source_scope.get("changed_count") or 0) > 0 or bool(source_scope.get("git_head_changed"))
    )
    # Cold attempt evidence, not bounded hot state, proves Reviewer freshness. Only
    # attempts bound to the current contract revision participate; older revisions stay cold.
    task_root = contract.parent.parent
    contract_sha = sha256(contract)
    project_mutated = source_mutated
    found_current_contract_attempt = False
    attempts_root = task_root / "attempts"
    if attempts_root.is_dir():
        for reservation_path in attempts_root.glob("*/launch-reservation.json"):
            try:
                reservation = load_json(reservation_path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if not _reservation_matches_contract(run_root, reservation, contract, contract_sha):
                continue
            found_current_contract_attempt = True
            if reservation.get("writes_project") is True:
                changed, _ended = _terminal_scope_changed(run_root, reservation_path.parent, reservation)
                project_mutated = project_mutated or changed
    if not found_current_contract_attempt:
        # Historical/synthetic state may predate self-contained attempt directories.
        project_mutated = project_mutated or any(
            _attempt_changed_project(run_root, task.get(key)) for key in ("current_attempt", "last_attempt")
        )
    if project_mutated:
        _assert_fresh_reviewer(run_root, contract, source_gate)

    source_report_raw = source_gate.get("report")
    if not isinstance(source_report_raw, str):
        raise ValueError("source gate lacks report binding")
    source_report = run_path(run_root, source_report_raw)
    source_sha = source_gate.get("report_sha256")
    if not source_report.is_file() or not isinstance(source_sha, str) or sha256(source_report) != source_sha.lower():
        raise ValueError("source report changed after integrity gate")

    if bool(args.semantic_evidence) != bool(args.semantic_evidence_gate):
        raise ValueError("--semantic-evidence and --semantic-evidence-gate must be supplied together")
    if args.semantic_evidence:
        semantic_report = run_path(run_root, args.semantic_evidence)
        semantic_gate_path = run_path(run_root, args.semantic_evidence_gate)
        semantic_gate = _clean_gate(semantic_gate_path)
        semantic_report_raw = semantic_gate.get("report")
        if not isinstance(semantic_report_raw, str) or run_path(run_root, semantic_report_raw) != semantic_report:
            raise ValueError("semantic evidence gate is not bound to semantic evidence")
        semantic_sha = semantic_gate.get("report_sha256")
        if not semantic_report.is_file() or not isinstance(semantic_sha, str) or sha256(semantic_report) != semantic_sha.lower():
            raise ValueError("semantic evidence changed after integrity gate")
    else:
        semantic_report = source_report
        semantic_gate_path = source_gate_path

    task["status"] = "accepted"
    task.pop("current_attempt", None)
    task.pop("last_attempt", None)
    task["accepted"] = {
        "source_gate": {"path": str(source_gate_path), "sha256": sha256(source_gate_path)},
        "semantic_report": {"path": str(semantic_report), "sha256": sha256(semantic_report)},
        "semantic_gate": {"path": str(semantic_gate_path), "sha256": sha256(semantic_gate_path)},
    }
    state["orchestrator_wait"] = {"active": False}
    if args.next_action:
        state["next_action"] = args.next_action
    atomic_json(state_path, state)
    return {"task": f"{args.phase_id}/{args.task_id}", "status": "accepted", "next_action": state.get("next_action")}


def set_next(args: argparse.Namespace) -> dict[str, Any]:
    run_root = args.run_root.resolve()
    state_path = run_root / "state.json"
    state = load_json(state_path)
    state["next_action"] = args.next_action
    if args.execution_status:
        state["execution_status"] = args.execution_status
    atomic_json(state_path, state)
    return {"execution_status": state.get("execution_status"), "next_action": state.get("next_action")}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--run-root", type=Path, required=True)
    common.add_argument("--phase-id", required=True)
    common.add_argument("--task-id", required=True)

    c = sub.add_parser("bind-contract", parents=[common])
    c.add_argument("--contract", required=True)
    c.add_argument("--status", default="prepared")
    c.add_argument("--next-action")
    c.add_argument("--supersede-incomplete", action="store_true", help="exceptional recovery only: preserve a terminal-less prior attempt as lifecycle-incomplete before rebinding the contract")

    pf = sub.add_parser("preflight-attempt", parents=[common])
    pf.add_argument("--contract", required=True)
    pf.add_argument("--supersede-incomplete", action="store_true")

    b = sub.add_parser("bind-attempt", parents=[common])
    b.add_argument("--event-dir", required=True)
    b.add_argument("--launch-json")
    b.add_argument("--next-action")
    b.add_argument("--wait-kind")
    b.add_argument("--supersede-incomplete", action="store_true", help="archive a terminal-less prior attempt as lifecycle-incomplete before binding this new attempt; use only after establishing it cannot still write")

    g = sub.add_parser("bind-gate", parents=[common])
    g.add_argument("--gate", required=True)
    g.add_argument("--next-action")

    a = sub.add_parser("accept-task", aliases=["accept"], parents=[common])
    a.add_argument("--evidence-gate", required=True, help="gate for the report the parent is accepting; for any mutating contract this is the fresh Reviewer gate, not the Implementer gate")
    a.add_argument("--semantic-evidence", help="optional separate Clerk report; omit when the parent consumed the accepted Reviewer/source report directly")
    a.add_argument("--semantic-evidence-gate", help="integrity gate bound to the optional separate --semantic-evidence")
    a.add_argument("--next-action")

    n = sub.add_parser("set-next")
    n.add_argument("--run-root", type=Path, required=True)
    n.add_argument("--next-action", required=True)
    n.add_argument("--execution-status")
    return ap


def main() -> int:
    args = parser().parse_args()
    if not args.run_root.is_absolute():
        print("ERROR: --run-root must be absolute", file=sys.stderr); return 2
    try:
        if args.command == "bind-contract": result = bind_contract(args)
        elif args.command == "preflight-attempt": result = preflight_attempt(args)
        elif args.command == "bind-attempt": result = bind_attempt(args)
        elif args.command == "bind-gate": result = bind_gate(args)
        elif args.command in {"accept-task", "accept"}: result = accept_task(args)
        else: result = set_next(args)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
