#!/usr/bin/env python3
"""Prove objective DSD attempt facts: authority, transport, report presence, and scope.

This gate never interprets worker prose or decides software correctness. Semantic
meaning belongs to the parent or Evidence Clerk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from _roles import ROLE_NAMES, role_is_project_writer
from _rules_snapshot import sha256_file, verify_snapshot

from _task_contract import allowed_source_changes, extra_scope_inventory

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def path_allowed(path: str, prefixes: list[str]) -> bool:
    normalized = PurePosixPath(path.replace("\\", "/")).as_posix()
    return any(normalized == p or normalized.startswith(p.rstrip("/") + "/") for p in prefixes)


def next_numbered_path(base: Path) -> Path:
    if not base.exists():
        return base
    for index in range(2, 10000):
        candidate = base.with_name(f"{base.stem}-{index:02d}{base.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot allocate immutable evidence path near {base}")


def run_scope_compare(skill_root: Path, project_root: Path, baseline: Path, output: Path) -> tuple[int, dict[str, Any]]:
    cp = subprocess.run([
        sys.executable, str(skill_root / "scripts" / "scope_snapshot.py"), "compare",
        "--root", str(project_root), "--baseline", str(baseline), "--output", str(output),
    ], text=True, capture_output=True, check=False)
    data = json.loads(output.read_text()) if output.exists() else {}
    return cp.returncode, data


def reservation_from_terminal(terminal_path: Path, terminal: dict[str, Any], run_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    fmt = terminal.get("format")
    if fmt == "dsd-worker-terminal-v3":
        value = terminal.get("launch_reservation")
        digest = terminal.get("launch_reservation_sha256")
        if not isinstance(value, str):
            return None, ["terminal launch_reservation binding missing"]
        path = Path(value).resolve()
        try:
            path.relative_to(run_root)
        except ValueError:
            errors.append(f"terminal launch_reservation is outside run root: {path}")
        if not path.is_file():
            return None, errors + [f"launch reservation missing: {path}"]
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append("terminal launch_reservation_sha256 missing/invalid")
        elif sha256_file(path) != digest.lower():
            errors.append("immutable launch reservation changed after worker lifecycle binding")
        try:
            reservation = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return None, errors + [f"launch reservation unreadable: {exc}"]
        if reservation.get("format") not in {"dsd-worker-launch-reservation-v1", "dsd-worker-launch-reservation-v2"}:
            errors.append(f"unsupported launch reservation format: {reservation.get('format')!r}")
        return reservation, errors

    if fmt == "dsd-worker-terminal-v2":
        # Historical v14 evidence repeated immutable authority directly in terminal.
        return dict(terminal), errors
    return None, [f"unsupported terminal event format: {fmt!r}"]


def authority_matches(reservation: dict[str, Any], *, run_root: Path, task: Path, report: Path, baseline: Path, log: Path | None, role: str) -> list[str]:
    errors: list[str] = []
    reserved_role = str(reservation.get("role", "")).lower()
    if reserved_role != role.lower():
        errors.append(f"launch reservation role mismatch: expected {role}, got {reserved_role!r}")

    bindings: dict[str, Path] = {"report": report, "task_contract": task, "scope_baseline": baseline}
    if log is not None:
        bindings["log"] = log
    for field, expected in bindings.items():
        actual = reservation.get(field)
        if not isinstance(actual, str) or Path(actual).resolve() != expected:
            errors.append(f"launch reservation {field} binding mismatch: expected {expected}, got {actual!r}")

    for field, path in (("task_contract", task), ("scope_baseline", baseline)):
        expected_hash = reservation.get(field + "_sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            errors.append(f"launch reservation {field}_sha256 missing/invalid")
        elif path.is_file() and sha256_file(path) != expected_hash.lower():
            errors.append(f"immutable {field} changed after launch reservation")

    prompt_value = reservation.get("prompt_file")
    prompt_hash = reservation.get("prompt_sha256")
    if not isinstance(prompt_value, str):
        errors.append("launch reservation prompt_file binding missing")
    else:
        prompt_path = Path(prompt_value).resolve()
        try:
            prompt_path.relative_to(run_root)
        except ValueError:
            errors.append(f"launch prompt is outside run root: {prompt_path}")
        if not prompt_path.is_file():
            errors.append(f"launch prompt missing: {prompt_path}")
        elif not isinstance(prompt_hash, str) or len(prompt_hash) != 64:
            errors.append("launch reservation prompt_sha256 missing/invalid")
        elif sha256_file(prompt_path) != prompt_hash.lower():
            errors.append("immutable launch prompt changed after reservation")

    rules_value = reservation.get("worker_rules")
    rules_hash = reservation.get("worker_rules_sha256")
    if not isinstance(rules_value, str):
        errors.append("launch reservation worker_rules binding missing")
    else:
        rules_path = Path(rules_value).resolve()
        try:
            rules_path.relative_to(run_root / "worker-rules")
        except ValueError:
            errors.append(f"worker_rules is outside run worker-rules tree: {rules_path}")
        if not rules_path.is_file():
            errors.append(f"worker_rules missing: {rules_path}")
        elif not isinstance(rules_hash, str) or len(rules_hash) != 64:
            errors.append("launch reservation worker_rules_sha256 missing/invalid")
        elif sha256_file(rules_path) != rules_hash.lower():
            errors.append("immutable worker_rules changed after launch reservation")
        else:
            try:
                snapshot = verify_snapshot(rules_path)
            except ValueError as exc:
                errors.append(f"worker-rules snapshot integrity failed: {exc}")
            else:
                manifest_path = Path(snapshot["manifest"]).resolve()
                manifest_value = reservation.get("worker_rules_manifest")
                manifest_hash = reservation.get("worker_rules_manifest_sha256")
                if not isinstance(manifest_value, str) or Path(manifest_value).resolve() != manifest_path:
                    errors.append("launch reservation worker_rules_manifest binding mismatch")
                elif not isinstance(manifest_hash, str) or len(manifest_hash) != 64:
                    errors.append("launch reservation worker_rules_manifest_sha256 missing/invalid")
                elif sha256_file(manifest_path) != manifest_hash.lower():
                    errors.append("immutable worker-rules manifest changed after launch reservation")
    return errors


def terminal_matches_attempt(candidate: Path, data: dict[str, Any], run_root: Path, task: Path, report: Path, baseline: Path, log: Path | None, role: str) -> bool:
    reservation, errs = reservation_from_terminal(candidate, data, run_root)
    if reservation is None or errs:
        return False
    return not authority_matches(reservation, run_root=run_root, task=task, report=report, baseline=baseline, log=log, role=role)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--task", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--terminal-event", type=Path)
    ap.add_argument("--log", type=Path)
    ap.add_argument("--role", choices=sorted(ROLE_NAMES), required=True)
    ap.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--scope-baseline", type=Path, required=True)
    ap.add_argument("--scope-output", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    if not args.run_root.is_absolute():
        print("ERROR: --run-root must be absolute", file=sys.stderr); return 2
    run_root = args.run_root.resolve()
    if not run_root.is_dir():
        print(f"ERROR: run root missing/not directory: {run_root}", file=sys.stderr); return 2

    def run_path(value: Path | None) -> Path | None:
        if value is None:
            return None
        return value.resolve() if value.is_absolute() else (run_root / value).resolve()

    task = run_path(args.task); report = run_path(args.report); baseline = run_path(args.scope_baseline)
    assert task is not None and report is not None and baseline is not None
    project_root = args.project_root.resolve()
    log = run_path(args.log)
    terminal_event = run_path(args.terminal_event)
    scope_output = run_path(args.scope_output)
    output_arg = run_path(args.output)
    skill_root = args.skill_root.resolve()

    for label, path in (("task", task), ("report", report), ("terminal-event", terminal_event), ("log", log), ("scope-output", scope_output), ("output", output_arg)):
        if path is None:
            continue
        try:
            path.relative_to(run_root)
        except ValueError:
            print(f"ERROR: {label} path is outside run root: {path}", file=sys.stderr); return 2

    errors: list[str] = []
    warnings: list[str] = []
    terminal: dict[str, Any] = {}
    reservation: dict[str, Any] = {}

    if terminal_event is None:
        candidates: list[Path] = []
        for candidate in run_root.rglob("terminal.json"):
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                continue
            if terminal_matches_attempt(candidate.resolve(), data, run_root, task, report, baseline, log, args.role):
                candidates.append(candidate.resolve())
        if len(candidates) == 1:
            terminal_event = candidates[0]
        elif not candidates:
            errors.append("no launcher terminal event uniquely binds this attempt")
        else:
            errors.append("multiple terminal events match this attempt; pass --terminal-event explicitly")

    if terminal_event is not None:
        if not terminal_event.is_file():
            errors.append(f"terminal event missing: {terminal_event}")
        else:
            try:
                terminal = json.loads(terminal_event.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"terminal event unreadable: {exc}")
            else:
                if str(terminal.get("status", "")).lower() != "completed" or terminal.get("exit_code") != 0:
                    errors.append(f"worker transport not successfully completed: status={terminal.get('status')!r} exit_code={terminal.get('exit_code')!r}")
                reservation_obj, terminal_errors = reservation_from_terminal(terminal_event, terminal, run_root)
                errors.extend(terminal_errors)
                if reservation_obj is not None:
                    reservation = reservation_obj
                    errors.extend(authority_matches(reservation, run_root=run_root, task=task, report=report, baseline=baseline, log=log, role=args.role))

    if not task.is_file():
        errors.append(f"task missing: {task}")
        task_text = ""
    else:
        task_text = read(task)
    try:
        allowed_writes = allowed_source_changes(task_text)
        required_extra_inventory = extra_scope_inventory(task_text)
    except ValueError as exc:
        errors.append(str(exc)); allowed_writes = []; required_extra_inventory = []

    report_state = "missing"
    report_sha = None
    report_bytes = None
    report_recovery_required = False
    if not report.is_file():
        report_recovery_required = True
    else:
        report_sha = sha256_file(report)
        report_bytes = report.stat().st_size
        skeleton_sha = reservation.get("report_skeleton_sha256") if reservation else None
        if isinstance(skeleton_sha, str) and report_sha == skeleton_sha.lower():
            report_state = "unchanged-skeleton"
            report_recovery_required = True
        else:
            report_state = "substantive"

    scope_result: dict[str, Any] | None = None
    if not baseline.is_file():
        errors.append(f"SCOPE-BASELINE-MISSING: {baseline}")
    elif not project_root.is_dir():
        errors.append(f"project root missing/not directory: {project_root}")
    else:
        try:
            baseline_data = json.loads(baseline.read_text(encoding="utf-8"))
            if baseline_data.get("inventory_mode") != "git-worktree":
                errors.append("SCOPE-BASELINE-UNSAFE: terminal gate requires a git-worktree snapshot")
            exclusions = [str(x).strip("/") for x in baseline_data.get("exclude_prefixes", [])]
            if exclusions != ["DeepSeekAndDestroy"]:
                errors.append("SCOPE-BASELINE-UNSAFE: only DeepSeekAndDestroy may be excluded")
            baseline_extra = [str(x).strip("/") for x in baseline_data.get("extra_inventory_roots", []) if isinstance(x, str)]
            missing_extra = [root for root in required_extra_inventory if root not in baseline_extra]
            if missing_extra:
                errors.append("SCOPE-BASELINE-MISSING-EXTRA-INVENTORY: " + ", ".join(missing_extra))
            out = scope_output or next_numbered_path(report.with_name("scope-diff.json").resolve())
            if scope_output and out.exists():
                raise ValueError(f"immutable scope output already exists: {out}")
            rc, scope_result = run_scope_compare(skill_root, project_root, baseline, out)
            if rc not in (0, 1):
                errors.append("scope comparison helper failed")
            changed = scope_result.get("changed", []) if isinstance(scope_result, dict) else []
            changed_paths = [str(entry.get("path", "")) for entry in changed if entry.get("path")]
            if role_is_project_writer(args.role, allowed_writes):
                outside = [p for p in changed_paths if not path_allowed(p, allowed_writes)]
                if outside:
                    errors.append(f"SCOPE-DRIFT: {len(outside)} path(s) outside Allowed source changes: " + ", ".join(outside[:12]))
            elif changed_paths:
                errors.append(f"READONLY-SCOPE-MOVED: {len(changed_paths)} project path(s); use Recovery, never semantic normalization")
        except Exception as exc:
            errors.append(f"scope comparison failed: {exc}")

    # Report recovery is an evidence-availability route, not a software verdict.
    # It stays separate from hard integrity failures so a cheap Clerk may inspect
    # exact-attempt output/log locations without rerunning a long technical worker.
    ok = not errors and not report_recovery_required
    result = {
        "format": "dsd-evidence-gate-v4",
        "role": args.role,
        "ok": ok,
        "mechanical_ok": not errors,
        "report_recovery_required": report_recovery_required,
        "report_state": report_state,
        "report_bytes": report_bytes,
        "errors": errors,
        "warnings": warnings,
        "run_root": str(run_root),
        "task": str(task),
        "report": str(report),
        "report_sha256": report_sha,
        "terminal_event": str(terminal_event) if terminal_event else None,
        "terminal": terminal,
        "launch_reservation": reservation,
        "log": str(log) if log else None,
        "allowed_source_changes": allowed_writes,
        "required_extra_scope_inventory": required_extra_inventory,
        "scope": scope_result,
    }

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if output_arg:
        output_arg.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_arg.open("x", encoding="utf-8") as handle:
                handle.write(rendered + "\n")
        except FileExistsError:
            print(f"ERROR: immutable evidence-gate output already exists: {output_arg}", file=sys.stderr); return 2
    if args.json:
        print(rendered)
    else:
        state = "CLEAN" if ok else "REPORT RECOVERY" if report_recovery_required and not errors else "FAIL"
        print("EVIDENCE GATE: " + state)
        print(f"Report: {report}")
        if errors:
            print("Errors: " + "; ".join(errors))
    if errors:
        return 1
    if report_recovery_required:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
