#!/usr/bin/env python3
"""Validate DeepSeek and Destroy control-plane state invariants.

This is mechanical consistency checking, not semantic acceptance judgment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from _roles import ZERO_CHANGE_GUARD_ROLES, role_is_project_writer
from _rules_snapshot import sha256_file, verify_snapshot
from _task_contract import allowed_source_changes

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


def attempt_pid(attempt: dict[str, Any]) -> Any:
    return attempt.get("worker_pid") or attempt.get("pid") or attempt.get("monitor_pid")


def task_declares_project_writes(task: dict[str, Any], base: Path) -> bool:
    """Return whether the current immutable contract grants project write paths."""
    contract = task.get("current_contract") or {}
    value = contract.get("path") or task.get("contract_path") or task.get("task_path")
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    try:
        return bool(allowed_source_changes(path.read_text(encoding="utf-8", errors="replace")))
    except (OSError, ValueError):
        return False


def validate_task(task_id: str, task: dict[str, Any], base: Path, worker_rules: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = str(task.get("status", "")).lower()
    attempts = task.get("transport_attempts", 0)
    contract = task.get("current_contract") or {}
    contract_path = contract.get("path") or task.get("contract_path") or task.get("task_path")

    contract_obj: Path | None = None
    if contract:
        revision = contract.get("revision")
        expected_sha = contract.get("sha256")
        if not isinstance(revision, int) or revision < 1:
            errors.append(f"{task_id}: current_contract requires positive integer revision")
        if not existing(contract_path, base):
            errors.append(f"{task_id}: current_contract path is missing")
        elif isinstance(contract_path, str):
            contract_obj = Path(contract_path)
            if not contract_obj.is_absolute():
                contract_obj = base / contract_obj
            contract_obj = contract_obj.resolve()
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            errors.append(f"{task_id}: current_contract requires sha256")
        elif contract_obj and sha256_file(contract_obj) != expected_sha.lower():
            errors.append(f"{task_id}: current_contract hash changed after freeze; create a new revision")

    attempt = task.get("current_attempt") or {}
    role = str(attempt.get("role") or task.get("next_role") or task.get("role") or "").lower()

    if status == "prepared" and contract and contract_obj is None:
        errors.append(f"{task_id}: prepared but immutable task contract is missing")

    if task.get("decomposition_required") is True and status in {"prepared", "launching", "in-progress"}:
        if not role:
            errors.append(f"{task_id}: decomposition_required=true requires explicit next_role/current_attempt.role before launch")
        elif role in ZERO_CHANGE_GUARD_ROLES:
            errors.append(f"{task_id}: decomposition_required=true forbids another mutating launch against the current contract")

    streak = task.get("zero_intended_change_streak", 0)
    if isinstance(streak, int) and streak >= 2 and not task.get("decomposition_required"):
        errors.append(f"{task_id}: zero_intended_change_streak >=2 requires decomposition_required=true")

    reserved_report: str | None = None
    if status in {"launching", "in-progress"}:
        if not isinstance(attempts, int) or attempts < 1:
            errors.append(f"{task_id}: {status} requires transport_attempts >= 1")
        reservation_value = attempt.get("launch_reservation")
        if not existing(reservation_value, base):
            errors.append(f"{task_id}: {status} requires existing launch_reservation")
        else:
            reservation_path = Path(reservation_value)
            if not reservation_path.is_absolute():
                reservation_path = base / reservation_path
            reservation_path = reservation_path.resolve()
            expected_reservation_sha = attempt.get("launch_reservation_sha256")
            try:
                reservation_data = json.loads(reservation_path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"{task_id}: cannot validate launch_reservation: {exc}")
            else:
                reservation_format = reservation_data.get("format")
                if reservation_format is None:
                    reservation_format = "dsd-worker-launch-reservation-v1"  # pre-versioned historical fixture/state
                if reservation_format not in {"dsd-worker-launch-reservation-v1", "dsd-worker-launch-reservation-v2"}:
                    errors.append(f"{task_id}: unsupported launch_reservation format: {reservation_format!r}")
                if reservation_format == "dsd-worker-launch-reservation-v2":
                    if not isinstance(expected_reservation_sha, str) or len(expected_reservation_sha) != 64:
                        errors.append(f"{task_id}: v15 active attempt requires launch_reservation_sha256")
                    elif sha256_file(reservation_path) != expected_reservation_sha.lower():
                        errors.append(f"{task_id}: immutable launch_reservation changed after state binding")

                reserved_role = str(reservation_data.get("role", "")).lower()
                if role and reserved_role != role:
                    errors.append(f"{task_id}: launch_reservation role does not match active role")
                attempt_number = attempt.get("attempt")
                if isinstance(attempt_number, int) and reservation_data.get("attempt") != attempt_number:
                    errors.append(f"{task_id}: launch_reservation attempt number does not match state")

                reserved_contract = reservation_data.get("task_contract")
                reserved_contract_sha = reservation_data.get("task_contract_sha256")
                if contract_obj is None or not isinstance(reserved_contract, str) or Path(reserved_contract).resolve() != contract_obj:
                    errors.append(f"{task_id}: launch_reservation task contract does not match current_contract")
                elif not isinstance(reserved_contract_sha, str) or len(reserved_contract_sha) != 64 or sha256_file(contract_obj) != reserved_contract_sha.lower():
                    errors.append(f"{task_id}: immutable task contract changed after reservation")

                for field, digest_field in (("prompt_file", "prompt_sha256"), ("scope_baseline", "scope_baseline_sha256")):
                    value = reservation_data.get(field)
                    digest = reservation_data.get(digest_field)
                    if not isinstance(value, str):
                        errors.append(f"{task_id}: launch_reservation missing {field}")
                        continue
                    obj = Path(value).resolve()
                    try:
                        obj.relative_to(base.resolve())
                    except ValueError:
                        errors.append(f"{task_id}: launch_reservation {field} is outside run root")
                    if not obj.is_file():
                        errors.append(f"{task_id}: launch_reservation {field} is missing")
                    elif not isinstance(digest, str) or len(digest) != 64 or sha256_file(obj) != digest.lower():
                        errors.append(f"{task_id}: immutable {field} changed after reservation")

                rules_value = reservation_data.get("worker_rules")
                rules_sha = reservation_data.get("worker_rules_sha256")
                if not isinstance(rules_value, str):
                    errors.append(f"{task_id}: launch_reservation missing worker_rules")
                else:
                    rules_obj = Path(rules_value).resolve()
                    if not rules_obj.is_file():
                        errors.append(f"{task_id}: launch_reservation worker_rules missing")
                    elif not isinstance(rules_sha, str) or len(rules_sha) != 64 or sha256_file(rules_obj) != rules_sha.lower():
                        errors.append(f"{task_id}: immutable worker_rules changed after reservation")
                    else:
                        try:
                            snapshot = verify_snapshot(rules_obj)
                        except ValueError as exc:
                            errors.append(f"{task_id}: worker-rules snapshot integrity failed: {exc}")
                        else:
                            manifest = Path(snapshot["manifest"]).resolve()
                            reserved_manifest = reservation_data.get("worker_rules_manifest")
                            reserved_manifest_sha = reservation_data.get("worker_rules_manifest_sha256")
                            if not isinstance(reserved_manifest, str) or Path(reserved_manifest).resolve() != manifest:
                                errors.append(f"{task_id}: launch_reservation worker-rules manifest does not match snapshot")
                            elif not isinstance(reserved_manifest_sha, str) or len(reserved_manifest_sha) != 64 or sha256_file(manifest) != reserved_manifest_sha.lower():
                                errors.append(f"{task_id}: immutable worker-rules manifest changed after reservation")
                reserved_report = reservation_data.get("report") if isinstance(reservation_data.get("report"), str) else None

        identity = attempt_pid(attempt) or attempt.get("harness_run_id") or attempt.get("session_id") or attempt.get("monitor_pid")
        if not identity:
            errors.append(f"{task_id}: {status} requires real worker/monitor/session identity")
        if not attempt.get("launched_at"):
            errors.append(f"{task_id}: {status} requires launched_at")
        if not attempt.get("terminal_event") and not attempt.get("event_dir"):
            errors.append(f"{task_id}: {status} requires terminal_event or event_dir")

    if status == "in-progress":
        pid = attempt_pid(attempt)
        liveness = str(attempt.get("liveness", "")).lower() == "confirmed"
        live = pid_alive(pid) if pid else bool(attempt.get("harness_run_id") or attempt.get("session_id") or attempt.get("monitor_pid"))
        report_path = reserved_report or attempt.get("report_path") or task.get("report_path")
        report_complete = bool(task.get("report_complete")) and existing(report_path, base)
        terminal_exists = existing(attempt.get("terminal_event"), base)
        if not ((live and liveness) or report_complete or terminal_exists):
            errors.append(f"{task_id}: in-progress has neither confirmed live identity nor terminal/complete evidence")

    if status == "waiting-for-worker":
        if not task.get("next_probe_at"):
            errors.append(f"{task_id}: waiting-for-worker requires next_probe_at")
        if not task.get("worker_profile") and not task.get("role_profile"):
            errors.append(f"{task_id}: waiting-for-worker requires a worker profile")

    if status == "process-exited":
        terminal = attempt.get("terminal_event")
        if terminal and not existing(terminal, base):
            errors.append(f"{task_id}: process-exited references missing terminal event")
        if not terminal and not attempt.get("exited_at"):
            errors.append(f"{task_id}: process-exited requires terminal_event or exited_at")

    if status == "evidence-reconciliation" and not task.get("evidence_gate_path"):
        errors.append(f"{task_id}: evidence-reconciliation requires evidence_gate_path")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("state", type=Path)
    ap.add_argument("--for-turn-exit", action="store_true")
    args = ap.parse_args()

    state_path = args.state.resolve()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read {state_path}: {exc}", file=sys.stderr)
        return 2

    base = state_path.parent
    errors: list[str] = []
    status = str(state.get("execution_status", "")).lower()
    next_action = state.get("next_action")

    if status not in TERMINAL:
        if not isinstance(next_action, str) or not next_action.strip():
            errors.append("active run requires a non-empty string next_action")

    worker_rules = state.get("worker_rules") or {}
    if state.get("worker_runtime"):
        rules_revision = worker_rules.get("revision")
        if not isinstance(rules_revision, int) or rules_revision < 1:
            errors.append("active worker runtime requires positive worker_rules.revision")
        rules_path_value = worker_rules.get("path")
        if not existing(rules_path_value, base):
            errors.append("active worker runtime requires existing worker_rules.path")
        expected_rules_sha = worker_rules.get("sha256")
        if not isinstance(expected_rules_sha, str) or len(expected_rules_sha) != 64:
            errors.append("active worker runtime requires worker_rules.sha256")
        elif existing(rules_path_value, base):
            rules_path = Path(rules_path_value)
            if not rules_path.is_absolute():
                rules_path = base / rules_path
            resolved_rules = rules_path.resolve()
            expected_rules_dir = base.resolve() / "worker-rules" / (f"r{rules_revision:04d}" if isinstance(rules_revision, int) and rules_revision >= 1 else "INVALID")
            if resolved_rules != expected_rules_dir / "WORKER_RULES.md":
                errors.append("worker_rules.path must identify the recorded immutable worker-rules/rNNNN/WORKER_RULES.md revision")
            if sha256_file(resolved_rules) != expected_rules_sha.lower():
                errors.append("worker_rules hash changed after run snapshot; create a new rules revision rather than rewriting prior worker authority")

        protocol_dir_value = worker_rules.get("protocol_dir")
        expected_protocol = worker_rules.get("protocol_fingerprint")
        manifest_value = worker_rules.get("manifest")
        expected_manifest_sha = worker_rules.get("manifest_sha256")
        if not existing(protocol_dir_value, base):
            errors.append("active worker runtime requires existing worker_rules.protocol_dir")
        if not isinstance(expected_protocol, str) or len(expected_protocol) != 64:
            errors.append("active worker runtime requires worker_rules.protocol_fingerprint")
        if not existing(manifest_value, base):
            errors.append("active worker runtime requires existing worker_rules.manifest")
        if not isinstance(expected_manifest_sha, str) or len(expected_manifest_sha) != 64:
            errors.append("active worker runtime requires worker_rules.manifest_sha256")
        if existing(rules_path_value, base):
            try:
                snapshot = verify_snapshot(resolved_rules)
            except ValueError as exc:
                errors.append(f"worker-rules snapshot integrity failed: {exc}")
            else:
                if snapshot["protocol_dir"] != str(Path(protocol_dir_value).resolve() if Path(protocol_dir_value).is_absolute() else (base / protocol_dir_value).resolve()):
                    errors.append("worker_rules.protocol_dir does not match immutable manifest")
                if snapshot["protocol_fingerprint"] != str(expected_protocol).lower():
                    errors.append("worker protocol snapshot changed after freeze; create a new worker-rules revision")
                manifest_path = Path(snapshot["manifest"]).resolve()
                state_manifest = Path(manifest_value) if isinstance(manifest_value, str) else Path("__missing__")
                if not state_manifest.is_absolute():
                    state_manifest = base / state_manifest
                if state_manifest.resolve() != manifest_path:
                    errors.append("worker_rules.manifest does not match immutable rules revision")
                elif isinstance(expected_manifest_sha, str) and len(expected_manifest_sha) == 64 and sha256_file(manifest_path) != expected_manifest_sha.lower():
                    errors.append("worker_rules manifest hash changed after freeze")

    availability = state.get("worker_availability") or {}
    if availability.get("status") == "waiting-for-worker" and not availability.get("next_probe_at"):
        errors.append("worker_availability waiting-for-worker requires next_probe_at")

    checkpoint = state.get("context_checkpoint") or {}
    checkpoint_status = str(checkpoint.get("status", "none")).lower()
    valid_checkpoint_statuses = {"none", "prepared", "compacting", "rehydration-required", "resumed", "compaction-failed"}
    if checkpoint_status not in valid_checkpoint_statuses:
        errors.append(f"invalid context_checkpoint status: {checkpoint_status}")
    if checkpoint_status in {"prepared", "compacting", "rehydration-required", "resumed", "compaction-failed"}:
        if not checkpoint.get("sequence"):
            errors.append(f"context_checkpoint {checkpoint_status} requires sequence")
        if not existing(checkpoint.get("checkpoint_path"), base):
            errors.append(f"context_checkpoint {checkpoint_status} requires existing checkpoint_path")
        if not existing(checkpoint.get("manifest_path"), base):
            errors.append(f"context_checkpoint {checkpoint_status} requires existing manifest_path")
    if checkpoint_status == "resumed" and not checkpoint.get("continuity_verified"):
        errors.append("context_checkpoint resumed requires continuity_verified=true")

    any_live = False
    for phase_id, phase in (state.get("phases") or {}).items():
        barrier = phase.get("gate_barrier") or {}
        phase_status = str(phase.get("status", "")).lower()
        if phase_status in {"auditing", "gate-due", "gating"}:
            if str(barrier.get("status", "")).upper() != "CLOSED":
                errors.append(f"{phase_id}: phase audit/gate requires CLOSED gate_barrier")
            snapshot = barrier.get("snapshot")
            if not snapshot:
                errors.append(f"{phase_id}: CLOSED audit/gate barrier requires snapshot")
            elif not existing(snapshot, base):
                errors.append(f"{phase_id}: CLOSED audit/gate barrier snapshot is missing")

        for task_id, task in (phase.get("tasks") or {}).items():
            if not isinstance(task, dict):
                continue
            full_id = f"{phase_id}/{task_id}"
            errors.extend(validate_task(full_id, task, base, worker_rules))
            attempt = task.get("current_attempt") or {}
            task_status = str(task.get("status", "")).lower()
            active_role = str(attempt.get("role") or task.get("next_role") or "").lower()
            if phase_status in {"auditing", "gate-due", "gating"} and task_status in {"launching", "in-progress"}:
                writes_project = bool(attempt.get("writes_project")) or role_is_project_writer(active_role, [])
                if not writes_project and active_role:
                    contract = task.get("current_contract") or {}
                    contract_path = Path(str(contract.get("path", ""))) if isinstance(contract, dict) else None
                    if contract_path and not contract_path.is_absolute():
                        contract_path = base / contract_path
                    if contract_path and contract_path.is_file():
                        try:
                            writes_project = role_is_project_writer(
                                active_role,
                                allowed_source_changes(contract_path.read_text(encoding="utf-8", errors="replace")),
                            )
                        except (OSError, ValueError):
                            writes_project = task_declares_project_writes(task, base)
                if writes_project:
                    errors.append(f"{full_id}: phase barrier cannot be CLOSED while a project-writing attempt is active")
            if task_status == "in-progress" and str(attempt.get("liveness", "")).lower() == "confirmed":
                pid = attempt_pid(attempt)
                if pid:
                    any_live = any_live or pid_alive(pid)
                else:
                    any_live = any_live or bool(attempt.get("harness_run_id") or attempt.get("session_id") or attempt.get("monitor_pid"))

    if args.for_turn_exit and status not in TERMINAL:
        waiting = availability.get("status") == "waiting-for-worker" and bool(availability.get("next_probe_at"))
        compacting = checkpoint_status == "compacting" and bool(checkpoint.get("compacting_at") or checkpoint.get("compaction_requested_at"))
        host_wait_state = state.get("orchestrator_wait") or {}
        host_wait = bool(host_wait_state.get("active"))
        if host_wait:
            terminal_value = host_wait_state.get("terminal_event")
            if not isinstance(terminal_value, str) or not terminal_value.strip():
                errors.append("active orchestrator_wait requires terminal_event")
                host_wait = False
            else:
                terminal_path = Path(terminal_value)
                if not terminal_path.is_absolute():
                    terminal_path = base / terminal_path
                if terminal_path.exists():
                    errors.append("orchestrator_wait is still active but terminal_event already exists; process the event before yielding")
                    host_wait = False
                monitor_pid = host_wait_state.get("monitor_pid")
                if monitor_pid is not None and not pid_alive(monitor_pid):
                    errors.append("active orchestrator_wait monitor_pid is not alive and no terminal event exists")
                    host_wait = False
        if not any_live and not waiting and not compacting and not host_wait:
            errors.append("turn-exit invariant failed: active run has no live worker, host wait, persisted availability wait, or active compaction")
        if checkpoint_status in {"prepared", "rehydration-required"}:
            errors.append(f"turn-exit invariant failed: checkpoint is {checkpoint_status}; complete compaction/rehydration first")

    if errors:
        for error in errors:
            print("ERROR: " + error)
        return 1
    print("STATE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
