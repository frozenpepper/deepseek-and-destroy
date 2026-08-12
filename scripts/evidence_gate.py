#!/usr/bin/env python3
"""Verify one DSD worker attempt's objective integrity envelope.

This gate deliberately does *not* interpret engineering meaning in worker prose.
It proves only facts Python can establish reliably: immutable launch authority,
process/native lifecycle, report artifact state, worker-rules integrity, and project
scope movement. Semantic interpretation belongs to Evidence Clerk / the premium
orchestrator.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from _contract import allowed_source_changes, role_writes_project
from _roles import ROLE_NAMES
from _rules_snapshot import sha256_file, verify_snapshot


def resolve_run_binding(run_root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = run_root / path
    return path.resolve()


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


def reservation_from_terminal(terminal: dict[str, Any], run_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    fmt = terminal.get("format")
    if fmt == "dsd-worker-terminal-v3":
        value = terminal.get("launch_reservation")
        digest = terminal.get("launch_reservation_sha256")
        if not isinstance(value, str):
            return None, ["terminal launch_reservation binding missing"]
        path = resolve_run_binding(run_root, value)
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


def authority_matches(
    reservation: dict[str, Any], *, run_root: Path, task: Path, report: Path,
    baseline: Path, log: Path | None, role: str,
) -> list[str]:
    errors: list[str] = []
    reserved_role = str(reservation.get("role", "")).lower()
    if reserved_role != role.lower():
        errors.append(f"launch reservation role mismatch: expected {role}, got {reserved_role!r}")

    bindings: dict[str, Path] = {"report": report, "task_contract": task, "scope_baseline": baseline}
    if log is not None:
        bindings["log"] = log
    for field, expected in bindings.items():
        actual = reservation.get(field)
        if not isinstance(actual, str) or resolve_run_binding(run_root, actual) != expected:
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
        prompt_path = resolve_run_binding(run_root, prompt_value)
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
        rules_path = resolve_run_binding(run_root, rules_value)
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
                if not isinstance(manifest_value, str) or resolve_run_binding(run_root, manifest_value) != manifest_path:
                    errors.append("launch reservation worker_rules_manifest binding mismatch")
                elif not isinstance(manifest_hash, str) or len(manifest_hash) != 64:
                    errors.append("launch reservation worker_rules_manifest_sha256 missing/invalid")
                elif sha256_file(manifest_path) != manifest_hash.lower():
                    errors.append("immutable worker-rules manifest changed after launch reservation")
    return errors


def terminal_matches_attempt(
    data: dict[str, Any], run_root: Path, task: Path, report: Path,
    baseline: Path, log: Path | None, role: str,
) -> bool:
    reservation, errs = reservation_from_terminal(data, run_root)
    if reservation is None or errs:
        return False
    return not authority_matches(
        reservation, run_root=run_root, task=task, report=report,
        baseline=baseline, log=log, role=role,
    )


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
    if not args.project_root.is_absolute():
        print(f"ERROR: --project-root must be absolute: {args.project_root}", file=sys.stderr); return 2

    def run_path(value: Path | None) -> Path | None:
        if value is None:
            return None
        return (value if value.is_absolute() else run_root / value).resolve()

    task = run_path(args.task); report = run_path(args.report); baseline = run_path(args.scope_baseline)
    assert task is not None and report is not None and baseline is not None
    project_root = args.project_root.resolve()
    log = run_path(args.log)
    terminal_event = run_path(args.terminal_event)
    skill_root = args.skill_root.resolve()
    for label, path in (("task", task), ("report", report), ("terminal-event", terminal_event), ("log", log)):
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
            if terminal_matches_attempt(data, run_root, task, report, baseline, log, args.role):
                candidates.append(candidate.resolve())
        if len(candidates) == 1:
            terminal_event = candidates[0]
        elif not candidates:
            errors.append("no terminal event uniquely binds this attempt")
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
                    errors.append(f"worker lifecycle not completed/0: status={terminal.get('status')!r} exit={terminal.get('exit_code')!r}")
                reservation_obj, terminal_errors = reservation_from_terminal(terminal, run_root)
                errors.extend(terminal_errors)
                if reservation_obj is not None:
                    reservation = reservation_obj
                    errors.extend(authority_matches(
                        reservation, run_root=run_root, task=task, report=report,
                        baseline=baseline, log=log, role=args.role,
                    ))

    if not task.is_file():
        errors.append(f"task missing: {task}")
        task_text = ""
    else:
        task_text = task.read_text(encoding="utf-8", errors="replace")

    reserved_writes = reservation.get("writes_project") if reservation else None
    if isinstance(reserved_writes, bool):
        writes_project = reserved_writes
    else:
        writes_project = role_writes_project(args.role, task_text)
        warnings.append("historical attempt lacks writes_project reservation; capability derived from role + contract")
    try:
        allowed_writes = allowed_source_changes(task_text) if writes_project else []
    except ValueError as exc:
        errors.append(str(exc)); allowed_writes = []

    report_state = "missing"
    report_sha: str | None = None
    if report.is_file():
        report_sha = sha256_file(report)
        skeleton_sha = reservation.get("report_skeleton_sha256") if reservation else None
        report_state = "launcher-skeleton" if isinstance(skeleton_sha, str) and report_sha == skeleton_sha.lower() else "present"

    scope_diff: Path | None = None
    scope_summary: dict[str, Any] = {}
    if not baseline.exists():
        errors.append(f"SCOPE-BASELINE-MISSING: {baseline}")
    elif not project_root.is_dir():
        errors.append(f"project root missing/not directory: {project_root}")
    else:
        try:
            baseline_data = json.loads(baseline.read_text(encoding="utf-8"))
            if baseline_data.get("inventory_mode") != "git-worktree":
                errors.append("SCOPE-BASELINE-UNSAFE: terminal gate requires git-worktree inventory")
            exclusions = [str(x).strip("/") for x in baseline_data.get("exclude_prefixes", [])]
            if exclusions != ["DeepSeekAndDestroy"]:
                errors.append("SCOPE-BASELINE-UNSAFE: only DeepSeekAndDestroy may be excluded")
            requested = run_path(args.scope_output)
            base_out = (terminal_event.parent if terminal_event is not None else report.parent) / "scope-diff.json"
            scope_diff = requested if requested is not None else next_numbered_path(base_out)
            if requested is not None and scope_diff.exists():
                raise ValueError(f"immutable scope output already exists: {scope_diff}")
            rc, scope_result = run_scope_compare(skill_root, project_root, baseline, scope_diff)
            if rc not in (0, 1):
                errors.append("scope comparison helper failed")
            changed = scope_result.get("changed", []) if isinstance(scope_result, dict) else []
            changed_paths = [str(x.get("path", "")) for x in changed if x.get("path")]
            outside = [p for p in changed_paths if writes_project and not path_allowed(p, allowed_writes)]
            if outside:
                errors.append(f"SCOPE-DRIFT: {len(outside)} path(s) outside Allowed source changes: " + ", ".join(outside[:12]))
            if not writes_project and changed_paths:
                errors.append(f"READONLY-SCOPE-MOVED: {len(changed_paths)} project path(s)")
            scope_summary = {
                "baseline": str(baseline),
                "diff": str(scope_diff),
                "changed_count": len(changed_paths),
                "added_count": len(scope_result.get("added", [])),
                "removed_count": len(scope_result.get("removed", [])),
                "modified_count": len(scope_result.get("modified", [])),
                "extra_inventory": list(baseline_data.get("extra_inventory_specs", [])),
            }
        except Exception as exc:
            errors.append(f"scope comparison failed: {exc}")

    ready = not errors and report_state == "present"
    needs_report_recovery = not errors and report_state != "present"
    reservation_path = terminal.get("launch_reservation") if terminal else None
    reservation_sha = terminal.get("launch_reservation_sha256") if terminal else None

    result = {
        "format": "dsd-integrity-gate-v2",
        "integrity_ok": not errors,
        "ready_for_interpretation": ready,
        "needs_report_recovery": needs_report_recovery,
        "role": args.role,
        "writes_project": writes_project,
        "allowed_source_changes": allowed_writes,
        "task": str(task),
        "task_sha256": sha256_file(task) if task.is_file() else None,
        "report": str(report),
        "report_sha256": report_sha,
        "report_state": report_state,
        "terminal_event": str(terminal_event) if terminal_event else None,
        "terminal_event_sha256": sha256_file(terminal_event) if terminal_event and terminal_event.is_file() else None,
        "launch_reservation": reservation_path,
        "launch_reservation_sha256": reservation_sha,
        "log": str(log) if log else None,
        "scope": scope_summary,
        "errors": errors,
        "warnings": warnings,
    }

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output_path = run_path(args.output)
        assert output_path is not None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_path.open("x", encoding="utf-8") as handle:
                handle.write(rendered + "\n")
        except FileExistsError:
            print(f"ERROR: immutable integrity gate exists: {output_path}", file=sys.stderr); return 2
    if args.json:
        print(rendered)
    else:
        state = "READY" if ready else "REPORT-RECOVERY" if needs_report_recovery else "FAIL"
        print(f"INTEGRITY GATE: {state}")
        print(f"Report: {report} ({report_state})")
        if scope_diff:
            print(f"Scope diff: {scope_diff}")
        if errors:
            print("Errors: " + "; ".join(errors))
    if errors:
        return 1
    if needs_report_recovery:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
