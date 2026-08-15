#!/usr/bin/env python3
"""Validate objective DSD run-state invariants.

This checker validates durable bindings, lifecycle facts, and resume/turn-exit consistency. It does not infer engineering meaning, task verdicts,
or orchestration strategy from prose/state hints.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from _rules_snapshot import sha256_file, verify_snapshot

TERMINAL_RUN = {"completed", "human-blocked", "paused-by-user", "abandoned"}
ACTIVE_ATTEMPT = {"launching", "in-progress"}
POST_ATTEMPT = {"process-exited", "gated", "report-recovery", "integrity-failed"}


def resolve(base: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def inside(base: Path, path: Path) -> bool:
    try:
        path.relative_to(base.resolve())
        return True
    except ValueError:
        return False


def existing(base: Path, raw: Any) -> Path | None:
    path = resolve(base, raw)
    return path if path is not None and path.exists() else None


def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def validate_binding(base: Path, label: str, binding: Any, errors: list[str]) -> Path | None:
    if not isinstance(binding, dict):
        errors.append(f"{label} binding missing")
        return None
    path = resolve(base, binding.get("path"))
    digest = binding.get("sha256")
    if path is None:
        errors.append(f"{label}.path missing")
        return None
    if not path.is_file():
        errors.append(f"{label} path missing: {path}")
        return None
    if not isinstance(digest, str) or len(digest) != 64:
        errors.append(f"{label}.sha256 missing/invalid")
    elif sha256_file(path) != digest.lower():
        errors.append(f"{label} changed after binding")
    return path


def validate_worker_rules(base: Path, state: dict[str, Any], errors: list[str]) -> None:
    runtime = state.get("worker_runtime")
    if not runtime:
        return
    rules = state.get("worker_rules")
    if not isinstance(rules, dict):
        errors.append("active worker runtime requires worker_rules binding")
        return
    revision = rules.get("revision")
    if not isinstance(revision, int) or revision < 1:
        errors.append("worker_rules.revision must be a positive integer")
    rules_path = validate_binding(base, "worker_rules", rules, errors)
    if rules_path is None:
        return
    expected = base.resolve() / "worker-rules" / f"r{revision:04d}" / "WORKER_RULES.md" if isinstance(revision, int) and revision >= 1 else None
    if expected is not None and rules_path != expected:
        errors.append("worker_rules.path is not the recorded immutable worker-rules revision")
    try:
        snapshot = verify_snapshot(rules_path)
    except ValueError as exc:
        errors.append(f"worker-rules snapshot integrity failed: {exc}")
        return
    # State may keep these convenience bindings; if present they must agree.
    for key, actual in (
        ("protocol_dir", snapshot["protocol_dir"]),
        ("protocol_fingerprint", snapshot["protocol_fingerprint"]),
        ("manifest", snapshot["manifest"]),
        ("manifest_sha256", sha256_file(Path(snapshot["manifest"]))),
    ):
        if key in rules:
            value = rules.get(key)
            if key in {"protocol_dir", "manifest"} and isinstance(value, str):
                value = str(resolve(base, value))
            if str(value) != str(actual):
                errors.append(f"worker_rules.{key} disagrees with immutable snapshot")


def load_reservation(base: Path, task_id: str, task: dict[str, Any], errors: list[str]) -> tuple[dict[str, Any] | None, Path | None]:
    attempt = task.get("current_attempt")
    if not isinstance(attempt, dict):
        return None, None
    event_dir = resolve(base, attempt.get("event_dir"))
    if event_dir is None or not inside(base, event_dir):
        errors.append(f"{task_id}: current_attempt.event_dir missing/outside run")
        return None, None
    reservation_path = event_dir / "launch-reservation.json"
    if not reservation_path.is_file():
        errors.append(f"{task_id}: launch reservation missing")
        return None, event_dir
    expected_sha = attempt.get("launch_reservation_sha256")
    if isinstance(expected_sha, str) and len(expected_sha) == 64:
        if sha256_file(reservation_path) != expected_sha.lower():
            errors.append(f"{task_id}: launch reservation changed after binding")
    try:
        data = json.loads(reservation_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{task_id}: cannot read launch reservation: {exc}")
        return None, event_dir
    if not isinstance(data, dict):
        errors.append(f"{task_id}: launch reservation is not an object")
        return None, event_dir
    if attempt.get("role") and str(attempt.get("role")) != str(data.get("role")):
        errors.append(f"{task_id}: current_attempt role disagrees with reservation")
    if "writes_project" in attempt and bool(attempt.get("writes_project")) != bool(data.get("writes_project")):
        errors.append(f"{task_id}: current_attempt writes_project disagrees with reservation")
    if isinstance(attempt.get("attempt"), int) and attempt.get("attempt") != data.get("attempt"):
        errors.append(f"{task_id}: current_attempt number disagrees with reservation")
    return data, event_dir


def validate_attempt(base: Path, task_id: str, task: dict[str, Any], contract_path: Path | None, errors: list[str]) -> None:
    status = str(task.get("status", "")).lower()
    if status not in ACTIVE_ATTEMPT | POST_ATTEMPT:
        return
    attempt = task.get("current_attempt")
    if not isinstance(attempt, dict):
        errors.append(f"{task_id}: {status} requires current_attempt")
        return
    reservation, event_dir = load_reservation(base, task_id, task, errors)
    if reservation is None or event_dir is None:
        return
    if contract_path is not None:
        reserved_contract = resolve(base, reservation.get("task_contract"))
        if reserved_contract is None or reserved_contract != contract_path:
            errors.append(f"{task_id}: reservation contract disagrees with current_contract")
        elif reservation.get("task_contract_sha256") != sha256_file(contract_path):
            errors.append(f"{task_id}: current contract changed after launch reservation")
    for field, digest_field in (("prompt_file", "prompt_sha256"), ("scope_baseline", "scope_baseline_sha256"), ("worker_rules", "worker_rules_sha256")):
        raw = reservation.get(field)
        digest = reservation.get(digest_field)
        path = resolve(base, raw) if isinstance(raw, str) else None
        if path is None or not path.is_file():
            errors.append(f"{task_id}: reservation {field} missing")
        elif not isinstance(digest, str) or len(digest) != 64 or sha256_file(path) != digest.lower():
            errors.append(f"{task_id}: immutable {field} changed after reservation")
    terminal = event_dir / "terminal.json"
    if status in POST_ATTEMPT and not terminal.is_file():
        errors.append(f"{task_id}: {status} requires terminal.json")
    if status in ACTIVE_ATTEMPT:
        identity = attempt.get("worker_pid") or attempt.get("monitor_pid") or attempt.get("session_id") or attempt.get("harness_run_id")
        if not identity:
            errors.append(f"{task_id}: {status} requires worker/session identity")
        if not attempt.get("launched_at"):
            errors.append(f"{task_id}: {status} requires launched_at")
    if status in {"gated", "report-recovery", "integrity-failed"}:
        validate_binding(base, f"{task_id}.current_attempt.integrity_gate", attempt.get("integrity_gate"), errors)


def validate_last_attempt(base: Path, task_id: str, task: dict[str, Any], errors: list[str]) -> None:
    entry = task.get("last_attempt")
    if entry is None:
        return
    if not isinstance(entry, dict):
        errors.append(f"{task_id}: last_attempt must be an object")
        return
    event_dir = resolve(base, entry.get("event_dir"))
    if event_dir is None or not inside(base, event_dir):
        errors.append(f"{task_id}.last_attempt.event_dir missing/outside run")
        return
    reservation = event_dir / "launch-reservation.json"
    if not reservation.is_file():
        errors.append(f"{task_id}.last_attempt: launch reservation missing")
    digest = entry.get("launch_reservation_sha256")
    if isinstance(digest, str) and len(digest) == 64 and reservation.is_file() and sha256_file(reservation) != digest.lower():
        errors.append(f"{task_id}.last_attempt: launch reservation changed after archival")
    status = str(entry.get("status") or "").lower()
    terminal = event_dir / "terminal.json"
    if status != "lifecycle-incomplete" and not terminal.is_file():
        errors.append(f"{task_id}.last_attempt: archived {status or 'attempt'} requires terminal.json")
    gate = entry.get("integrity_gate")
    if gate is not None:
        validate_binding(base, f"{task_id}.last_attempt.integrity_gate", gate, errors)

def validate_task(base: Path, task_id: str, task: dict[str, Any], errors: list[str]) -> None:
    contract = task.get("current_contract")
    contract_path = None
    if contract:
        contract_path = validate_binding(base, f"{task_id}.current_contract", contract, errors)
        revision = contract.get("revision") if isinstance(contract, dict) else None
        if not isinstance(revision, int) or revision < 1:
            errors.append(f"{task_id}: current_contract.revision must be positive")
    validate_last_attempt(base, task_id, task, errors)
    validate_attempt(base, task_id, task, contract_path, errors)
    if str(task.get("status", "")).lower() == "accepted":
        accepted = task.get("accepted")
        if not isinstance(accepted, dict):
            errors.append(f"{task_id}: accepted task requires accepted evidence bindings")
        else:
            validate_binding(base, f"{task_id}.accepted.source_gate", accepted.get("source_gate"), errors)
            validate_binding(base, f"{task_id}.accepted.semantic_report", accepted.get("semantic_report"), errors)
            validate_binding(base, f"{task_id}.accepted.semantic_gate", accepted.get("semantic_gate"), errors)


def validate_checkpoint(base: Path, state: dict[str, Any], errors: list[str]) -> str:
    checkpoint = state.get("context_checkpoint") or {}
    status = str(checkpoint.get("status", "none")).lower()
    valid = {"none", "prepared", "compacting", "rehydration-required", "resumed", "compaction-failed"}
    if status not in valid:
        errors.append(f"invalid context_checkpoint status: {status}")
        return status
    if status != "none":
        if not checkpoint.get("sequence"):
            errors.append(f"context_checkpoint {status} requires sequence")
        if existing(base, checkpoint.get("checkpoint_path")) is None:
            errors.append(f"context_checkpoint {status} requires checkpoint_path")
        if existing(base, checkpoint.get("manifest_path")) is None:
            errors.append(f"context_checkpoint {status} requires manifest_path")
    if status == "resumed" and checkpoint.get("continuity_verified") is not True:
        errors.append("context_checkpoint resumed requires continuity_verified=true")
    return status


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("state", type=Path)
    ap.add_argument("--for-turn-exit", action="store_true")
    args = ap.parse_args()
    state_path = args.state.resolve()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("state is not an object")
    except Exception as exc:
        print(f"ERROR: cannot read {state_path}: {exc}", file=sys.stderr)
        return 2
    base = state_path.parent
    errors: list[str] = []
    run_status = str(state.get("execution_status", "")).lower()
    if run_status not in TERMINAL_RUN and not str(state.get("next_action") or "").strip():
        errors.append("active run requires next_action")
    validate_worker_rules(base, state, errors)
    checkpoint_status = validate_checkpoint(base, state, errors)

    any_live = False
    for phase_id, phase in (state.get("phases") or {}).items():
        if not isinstance(phase, dict):
            continue
        for task_name, task in (phase.get("tasks") or {}).items():
            if not isinstance(task, dict):
                continue
            full = f"{phase_id}/{task_name}"
            validate_task(base, full, task, errors)
            attempt = task.get("current_attempt") or {}
            if str(task.get("status", "")).lower() == "in-progress" and isinstance(attempt, dict):
                pid = attempt.get("worker_pid") or attempt.get("monitor_pid")
                if pid_alive(pid) or attempt.get("session_id") or attempt.get("harness_run_id"):
                    any_live = True

    if args.for_turn_exit and run_status not in TERMINAL_RUN:
        compacting = checkpoint_status == "compacting"
        host_wait = state.get("orchestrator_wait") or {}
        active_wait = bool(host_wait.get("active"))
        if active_wait:
            terminal = resolve(base, host_wait.get("terminal_event"))
            if terminal is None:
                errors.append("active orchestrator_wait requires terminal_event")
                active_wait = False
            elif terminal.exists():
                errors.append("orchestrator_wait still active after terminal event; process the event before yielding")
                active_wait = False
            monitor = host_wait.get("monitor_pid")
            if monitor is not None and not pid_alive(monitor):
                errors.append("orchestrator_wait monitor is not alive")
                active_wait = False
        if not (any_live or compacting or active_wait):
            errors.append("turn-exit invariant failed: no live worker, active wait/backoff, or compaction")
        if checkpoint_status in {"prepared", "rehydration-required"}:
            errors.append(f"turn-exit invariant failed: checkpoint is {checkpoint_status}")

    if errors:
        for error in errors:
            print("ERROR: " + error)
        return 1
    print("STATE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
