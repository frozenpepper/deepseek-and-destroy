#!/usr/bin/env python3
"""Run DSD's cheap terminal evidence gate.

Mechanical/integrity failures are hard. Clerical representation defects are routed
to Evidence Clerk when the underlying immutable attempt/evidence remains trustworthy.
The helper does not judge software correctness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from _roles import CONTRACT_SCOPED_WRITER_ROLES, ROLE_TERMINALS
from _rules_snapshot import sha256_file, verify_snapshot

STATUS_RE = re.compile(r"^\s*DSD_REPORT_STATUS\s*:\s*(\S+)\s*$", re.I | re.M)
CLERK_RE = re.compile(r"^\s*Clerk\s+checks\s*:\s*(.+?)\s*$", re.I | re.M)
VERIFICATION_RE = re.compile(r"^\s*Verification\s*:\s*(.+?)\s*$", re.I | re.M)
ROLE_RE = re.compile(r"^\s*Role\s*:\s*(.+?)\s*$", re.I | re.M)
TASK_RE = re.compile(r"^\s*Task\s*:\s*(.+?)\s*$", re.I | re.M)
VERDICT_LINE_RE = re.compile(r"^\s*Verdict\s*:\s*([A-Z][A-Z_-]*)\s*$", re.I | re.M)
COUNTER_RE = re.compile(r"\b(total|passed|pass|failed|fail|skipped|skip|other)\s*=\s*(\d+)\b", re.I)
CHECK_ID_RE = re.compile(r"\b(?:[A-Z][A-Z0-9]*-\d+|VERIFICATION-ARITHMETIC)\b")
NATURAL_TOTAL_RE = re.compile(r"\b(\d+)\s+(?:tests?|checks?|cases?)\b", re.I)
NATURAL_PASS_RE = re.compile(r"\b(\d+)\s+(?:pass(?:ed)?|passing)\b", re.I)
NATURAL_FAIL_RE = re.compile(r"\b(\d+)\s+(?:fail(?:ed)?|failing|failures?)\b", re.I)
NATURAL_SKIP_RE = re.compile(r"\b(\d+)\s+(?:skip(?:ped)?|skipping)\b", re.I)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.I | re.M)
    m = pattern.search(text)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", text[start:], re.M)
    end = start + nxt.start() if nxt else len(text)
    return re.sub(r"<!--.*?-->", "", text[start:end], flags=re.S).strip()


def task_clerk_checks(text: str) -> str:
    return markdown_section(text, "Evidence Clerk Checks") or "NONE"


def allowed_source_changes(text: str) -> list[str]:
    section = markdown_section(text, "Allowed source changes")
    if not section or section.strip().upper() == "NONE":
        return []
    result: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        value = stripped[1:].strip().strip("`").replace("\\", "/").rstrip("/")
        if not value or value.upper() == "NONE":
            continue
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {".", "./"}:
            raise ValueError(f"unsafe Allowed source changes entry: {value}")
        result.append(path.as_posix())
    return list(dict.fromkeys(result))


def path_allowed(path: str, prefixes: list[str]) -> bool:
    normalized = PurePosixPath(path.replace("\\", "/")).as_posix()
    return any(normalized == p or normalized.startswith(p.rstrip("/") + "/") for p in prefixes)


def arithmetic_error(report: str) -> str | None:
    m = VERIFICATION_RE.search(report)
    if not m:
        return None
    line = m.group(1)
    counts = {k.lower(): int(v) for k, v in COUNTER_RE.findall(line)}
    total = counts.get("total")
    if total is not None:
        passed = counts.get("passed", counts.get("pass", 0))
        failed = counts.get("failed", counts.get("fail", 0))
        skipped = counts.get("skipped", counts.get("skip", 0))
        other = counts.get("other", 0)
        component_sum = passed + failed + skipped + other
        return None if total == component_sum else f"verification arithmetic inconsistent: total={total} but components sum to {component_sum}"

    total_m = NATURAL_TOTAL_RE.search(line)
    pass_m = NATURAL_PASS_RE.search(line)
    fail_m = NATURAL_FAIL_RE.search(line)
    skip_m = NATURAL_SKIP_RE.search(line)
    if total_m and (pass_m or fail_m or skip_m):
        natural_total = int(total_m.group(1))
        component_sum = sum(int(x.group(1)) for x in (pass_m, fail_m, skip_m) if x)
        if natural_total != component_sum:
            return f"verification arithmetic inconsistent: total={natural_total} but reported pass/fail/skip components sum to {component_sum}"
    return None


def run_review_contract(skill_root: Path, task: Path, report: Path, require_pass: bool) -> dict[str, Any]:
    cmd = [sys.executable, str(skill_root / "scripts" / "check_review_contract.py"), "--task", str(task), "--review", str(report), "--json"]
    if require_pass:
        cmd.append("--require-pass")
    cp = subprocess.run(cmd, text=True, capture_output=True, check=False)
    raw = (cp.stdout or cp.stderr).strip()
    try:
        data = json.loads(raw)
    except Exception:
        return {"semantic_ok": False, "normalization_required": False, "errors": ["review-contract helper returned unreadable output"], "raw": raw[:2000]}
    data["helper_exit_code"] = cp.returncode
    return data


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
    ap.add_argument("--role", choices=sorted(ROLE_TERMINALS), required=True)
    ap.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--scope-baseline", type=Path, required=True)
    ap.add_argument("--scope-output", type=Path)
    ap.add_argument("--require-review-pass", action="store_true")
    ap.add_argument("--clerk-report", type=Path)
    ap.add_argument("--clerk-gate", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    if not args.run_root.is_absolute():
        print("ERROR: --run-root must be absolute", file=sys.stderr); return 2
    run_root = args.run_root.resolve()
    if not run_root.is_dir():
        print(f"ERROR: run root missing/not directory: {run_root}", file=sys.stderr); return 2
    required_paths = (("task", args.task), ("report", args.report), ("project-root", args.project_root), ("scope-baseline", args.scope_baseline))
    for label, value in required_paths:
        if not value.is_absolute():
            print(f"ERROR: --{label} must be absolute: {value}", file=sys.stderr); return 2
    optional_paths = (("terminal-event", args.terminal_event), ("log", args.log), ("scope-output", args.scope_output), ("clerk-report", args.clerk_report), ("clerk-gate", args.clerk_gate), ("output", args.output))
    for label, value in optional_paths:
        if value is not None and not value.is_absolute():
            print(f"ERROR: --{label} must be absolute: {value}", file=sys.stderr); return 2
    if (args.clerk_report is None) != (args.clerk_gate is None):
        print("ERROR: --clerk-report and --clerk-gate must be supplied together", file=sys.stderr); return 2

    task = args.task.resolve(); report = args.report.resolve(); project_root = args.project_root.resolve(); baseline = args.scope_baseline.resolve()
    log = args.log.resolve() if args.log else None
    terminal_event = args.terminal_event.resolve() if args.terminal_event else None
    skill_root = args.skill_root.resolve()
    for label, path in (("task", task), ("report", report), *[(name, value.resolve()) for name, value in optional_paths if value is not None and name != "output"]):
        try:
            path.relative_to(run_root)
        except ValueError:
            print(f"ERROR: {label} path is outside run root: {path}", file=sys.stderr); return 2

    errors: list[str] = []
    warnings: list[str] = []
    normalizable_reasons: list[str] = []
    location_recovery_reasons: list[str] = []
    declared_clerk_reasons: list[str] = []
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
            errors.append("no launcher terminal event uniquely binds this report/task/scope attempt")
        else:
            errors.append("multiple launcher terminal events match this report/task/scope attempt; pass --terminal-event explicitly")

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
                    errors.append(f"terminal attempt is not a successful completed worker exit: status={terminal.get('status')!r} exit_code={terminal.get('exit_code')!r}")
                reservation_obj, terminal_errors = reservation_from_terminal(terminal_event, terminal, run_root)
                errors.extend(terminal_errors)
                if reservation_obj is not None:
                    reservation = reservation_obj
                    errors.extend(authority_matches(reservation, run_root=run_root, task=task, report=report, baseline=baseline, log=log, role=args.role))

    clerk_report = args.clerk_report.resolve() if args.clerk_report else None
    clerk_gate = args.clerk_gate.resolve() if args.clerk_gate else None
    clerk_verdict: str | None = None
    clerk_text = ""
    if clerk_report:
        if not clerk_report.is_file():
            errors.append(f"clerk report missing: {clerk_report}")
        else:
            clerk_text = read(clerk_report)
            verdict_m = VERDICT_LINE_RE.search(clerk_text)
            if not verdict_m:
                errors.append("clerk report missing Verdict: CLEAN|DISCREPANCY|MALFORMED")
            else:
                clerk_verdict = verdict_m.group(1).upper().replace("-", "_")
                if clerk_verdict not in ROLE_TERMINALS["evidence-clerk"]:
                    errors.append(f"invalid Evidence Clerk verdict: {clerk_verdict}")
                elif clerk_verdict != "CLEAN":
                    errors.append(f"clerk reconciliation is {clerk_verdict}, not CLEAN")
        if clerk_gate is None or not clerk_gate.is_file():
            errors.append(f"clean clerk evidence-gate artifact missing: {clerk_gate}")
        else:
            try:
                clerk_gate_data = json.loads(clerk_gate.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"clerk evidence-gate unreadable: {exc}")
            else:
                if clerk_gate_data.get("format") not in {"dsd-evidence-gate-v2", "dsd-evidence-gate-v3"}:
                    errors.append("clerk evidence-gate has unsupported format")
                if clerk_gate_data.get("role") != "evidence-clerk":
                    errors.append("clerk evidence-gate role is not evidence-clerk")
                if clerk_gate_data.get("report") != str(clerk_report):
                    errors.append("clerk evidence-gate report binding does not match --clerk-report")
                bound_sha = clerk_gate_data.get("report_sha256")
                if not isinstance(bound_sha, str) or len(bound_sha) != 64:
                    errors.append("clerk evidence-gate lacks report_sha256 binding")
                elif clerk_report.is_file() and sha256_file(clerk_report) != bound_sha.lower():
                    errors.append("clerk report changed after its clean evidence gate")
                if clerk_gate_data.get("ok") is not True or clerk_gate_data.get("clerk_required"):
                    errors.append("clerk report was not itself accepted by a clean terminal evidence gate")
                if clerk_gate_data.get("errors"):
                    errors.append("clerk evidence-gate contains errors")

    if not task.exists():
        errors.append(f"task missing: {task}"); task_text = ""
    else:
        task_text = read(task)
    try:
        allowed_writes = allowed_source_changes(task_text)
    except ValueError as exc:
        errors.append(str(exc)); allowed_writes = []

    report_text = ""
    actual_verdict: str | None = None
    report_unrecovered = False
    if not report.exists():
        report_unrecovered = True
        location_recovery_reasons.append(f"RC-004 REPORT-MISSING: expected {report}; Clerk may locate/copy only exact-attempt evidence")
    else:
        report_text = read(report)
        current_report_sha = sha256_file(report)
        skeleton_sha = reservation.get("report_skeleton_sha256") if reservation else None
        status_m = STATUS_RE.search(report_text)
        status = status_m.group(1).upper() if status_m else None
        terminal_format = terminal.get("format")
        if isinstance(skeleton_sha, str) and current_report_sha == skeleton_sha.lower():
            report_unrecovered = True
            location_recovery_reasons.append("RC-004 REPORT-UNCHANGED-SKELETON: canonical report is still the exact launcher skeleton")
        elif terminal_format == "dsd-worker-terminal-v2" and status == "SKELETON":
            # Historical v14 attempts did not bind the launcher's skeleton hash.
            # Preserve the old explicit marker as a recovery signal, not as a
            # substantive Reviewer/worker report that can fail semantic checks.
            report_unrecovered = True
            location_recovery_reasons.append("RC-004 REPORT-LEGACY-SKELETON: historical canonical report is still marked SKELETON")
        elif status != "FINAL":
            if args.role == "evidence-clerk":
                errors.append("Evidence Clerk report must explicitly mark DSD_REPORT_STATUS: FINAL; Clerk reconciliation cannot recurse")
            else:
                normalizable_reasons.append("RC-002 REPORT-FINALITY: substantive report lacks canonical DSD_REPORT_STATUS: FINAL")

        if not report_unrecovered:
            verdict_m = VERDICT_LINE_RE.search(report_text)
            expected_role = args.role.lower()
            if not verdict_m:
                errors.append("report missing role terminal Verdict line")
            else:
                actual_verdict = verdict_m.group(1).upper().replace("-", "_")
                if actual_verdict not in ROLE_TERMINALS[expected_role]:
                    allowed = ", ".join(sorted(v.replace("_", "-") for v in ROLE_TERMINALS[expected_role]))
                    errors.append(f"invalid {expected_role} terminal verdict {actual_verdict.replace('_', '-')}; expected one of: {allowed}")

            # Worker-authored identity is optional/readability-only. Immutable launch
            # reservation is authority; conflicting prose is ignored but surfaced.
            role_m = ROLE_RE.search(report_text)
            if role_m:
                prose_role = role_m.group(1).strip().lower().replace("_", "-").replace(" ", "-")
                if prose_role != expected_role:
                    warnings.append(f"ignored worker-authored Role mismatch ({prose_role}); launch reservation says {expected_role}")
            task_m = TASK_RE.search(report_text)
            expected_task = str(reservation.get("task_id", "")).strip() if reservation else ""
            if task_m and expected_task and task_m.group(1).strip() != expected_task:
                warnings.append(f"ignored worker-authored Task mismatch ({task_m.group(1).strip()}); launch reservation says {expected_task}")

            arith = arithmetic_error(report_text)
            if arith:
                declared_clerk_reasons.append("VERIFICATION-ARITHMETIC: " + arith)
            report_clerk = CLERK_RE.search(report_text)
            if report_clerk and not report_clerk.group(1).strip().upper().startswith("NONE"):
                declared_clerk_reasons.append("REPORT-DECLARED: " + report_clerk.group(1).strip())

    checks = task_clerk_checks(task_text)
    if checks.strip().upper() != "NONE":
        declared_clerk_reasons.append("TASK-EVIDENCE-CHECKS: " + " ".join(checks.split())[:800])

    review_contract: dict[str, Any] | None = None
    if args.role == "reviewer" and report_text and not report_unrecovered:
        review_contract = run_review_contract(skill_root, task, report, args.require_review_pass)
        if not review_contract.get("semantic_ok", False):
            errors.extend("review proof contract: " + str(x) for x in review_contract.get("errors", []) or ["semantic validation failed"])
        elif review_contract.get("normalization_required"):
            reasons = "; ".join(str(x) for x in review_contract.get("normalization_reasons", []))[:1200]
            normalizable_reasons.append("RC-001 REVIEW-PROOF-NORMALIZATION: " + reasons)

    scope_result: dict[str, Any] | None = None
    if not baseline.exists():
        errors.append(f"SCOPE-BASELINE-MISSING: {baseline}")
    elif not project_root.is_dir():
        errors.append(f"project root missing/not directory: {project_root}")
    else:
        try:
            baseline_data = json.loads(baseline.read_text())
            if baseline_data.get("inventory_mode") != "git-worktree":
                errors.append("SCOPE-BASELINE-UNSAFE: terminal evidence gate requires a git-worktree scope snapshot")
            exclusions = [str(x).strip("/") for x in baseline_data.get("exclude_prefixes", [])]
            if "DeepSeekAndDestroy" not in exclusions or any(x != "DeepSeekAndDestroy" for x in exclusions):
                errors.append("SCOPE-BASELINE-UNSAFE: only DeepSeekAndDestroy may be excluded from the terminal project-scope snapshot")
            out = args.scope_output.resolve() if args.scope_output else next_numbered_path(report.with_name(report.stem + "-scope-diff.json").resolve())
            if args.scope_output and out.exists():
                raise ValueError(f"immutable scope output already exists: {out}; use a new numbered path")
            rc, scope_result = run_scope_compare(skill_root, project_root, baseline, out)
            if rc not in (0, 1):
                errors.append("scope comparison helper failed")
            changed = scope_result.get("changed", []) if isinstance(scope_result, dict) else []
            changed_paths = [str(entry.get("path", "")) for entry in changed if entry.get("path")]
            if args.role in CONTRACT_SCOPED_WRITER_ROLES:
                outside = [p for p in changed_paths if not path_allowed(p, allowed_writes)]
                if outside:
                    errors.append(f"SCOPE-DRIFT: {len(outside)} changed project path(s) outside Allowed source changes: " + ", ".join(outside[:12]))
            elif changed_paths:
                errors.append(f"READONLY-SCOPE-MOVED: {len(changed_paths)} project path(s); enter recovery, not clerical reconciliation")
        except Exception as exc:
            errors.append(f"scope comparison failed: {exc}")

    declared_clerk_reasons = list(dict.fromkeys(declared_clerk_reasons))
    normalizable_reasons = list(dict.fromkeys(normalizable_reasons))
    location_recovery_reasons = list(dict.fromkeys(location_recovery_reasons))
    all_normalizable = declared_clerk_reasons + normalizable_reasons
    required_ids = sorted(set(CHECK_ID_RE.findall("\n".join(all_normalizable))))
    if all_normalizable and not required_ids:
        errors.append("Evidence Clerk work requires stable check ids (for example P-001, RC-001, or VERIFICATION-ARITHMETIC)")

    # Evidence Clerk is the terminal normalization layer, not a recursive role.
    # Its own clerical/report defects fail this attempt so the parent can launch a
    # fresh Clerk if warranted; they never route Clerk -> Clerk.
    if args.role == "evidence-clerk" and (all_normalizable or location_recovery_reasons):
        reasons = all_normalizable + location_recovery_reasons
        errors.append("Evidence Clerk terminal evidence cannot require another Evidence Clerk: " + "; ".join(reasons))
        all_normalizable = []
        normalizable_reasons = []
        location_recovery_reasons = []
        required_ids = []

    unresolved_normalizable = all_normalizable
    if clerk_verdict == "CLEAN":
        missing_ids = [check_id for check_id in required_ids if check_id not in clerk_text]
        if missing_ids:
            errors.append("CLEAN clerk report does not cover required check id(s): " + ", ".join(missing_ids))
        else:
            unresolved_normalizable = []

    # Missing/unchanged canonical report cannot be waived by prose. A Clerk may
    # recover an exact-attempt report, but the originating attempt must be re-gated
    # after the canonical report path actually changes.
    clerk_reasons = unresolved_normalizable + location_recovery_reasons
    fast_path_eligible = bool(args.role == "reviewer" and actual_verdict == "PASS" and not errors and not clerk_reasons)
    clerk_overlay = {
        "path": str(clerk_report) if clerk_report else None,
        "verdict": clerk_verdict,
        "authoritative_for_check_ids": required_ids if clerk_verdict == "CLEAN" and not unresolved_normalizable else [],
        "normalizes_clerical_representation": bool(clerk_verdict == "CLEAN" and required_ids and not unresolved_normalizable),
    }
    if clerk_overlay["normalizes_clerical_representation"]:
        warnings.append("CLEAN Evidence Clerk overlay normalizes assigned clerical checks: " + ", ".join(required_ids))

    result = {
        "format": "dsd-evidence-gate-v3",
        "role": args.role,
        "ok": not errors and not clerk_reasons,
        "structural_ok": not errors,
        "clerk_required": bool(clerk_reasons),
        "clerk_reasons": clerk_reasons,
        "declared_clerk_reasons": declared_clerk_reasons,
        "normalizable_report_reasons": normalizable_reasons,
        "report_recovery_reasons": location_recovery_reasons,
        "clerk_reconciliation": clerk_overlay,
        "clerk_gate": str(clerk_gate) if clerk_gate else None,
        "fast_path_eligible": fast_path_eligible,
        "verdict": actual_verdict,
        "errors": errors,
        "warnings": warnings,
        "run_root": str(run_root),
        "task": str(task),
        "report": str(report),
        "report_sha256": sha256_file(report) if report.is_file() else None,
        "terminal_event": str(terminal_event) if terminal_event else None,
        "terminal": terminal,
        "launch_reservation": reservation,
        "log": str(log) if log else None,
        "allowed_source_changes": allowed_writes,
        "review_contract": review_contract,
        "scope": scope_result,
    }

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output_path = args.output.resolve(); output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_path.open("x", encoding="utf-8") as handle:
                handle.write(rendered + "\n")
        except FileExistsError:
            print(f"ERROR: immutable evidence-gate output already exists: {output_path}; use a new numbered path", file=sys.stderr); return 2
    if args.json:
        print(rendered)
    else:
        state = "CLEAN" if result["ok"] else "CLERK REQUIRED" if result["clerk_required"] and not errors else "FAIL"
        print("EVIDENCE GATE: " + state)
        print(f"Report: {report}")
        if clerk_reasons: print("Clerk: " + "; ".join(clerk_reasons))
        if errors: print("Errors: " + "; ".join(errors))
    if errors:
        return 1
    if clerk_reasons:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
