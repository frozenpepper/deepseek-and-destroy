#!/usr/bin/env python3
"""Mechanical pre-acceptance evidence gate for DSD worker attempts.

This gate does not judge semantic correctness. It verifies terminal/report binding,
immutable rule provenance, declared source-write boundaries, structural reviewer
contracts, and simple declared arithmetic/provenance checks before premium
orchestrator acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from _rules_snapshot import verify_rules_manifest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def normalize_repo_path(raw: str) -> str:
    s = raw.replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s.rstrip("/")


def git_changed_paths(project_root: Path, baseline_ref: str) -> set[str]:
    proc = subprocess.run(
        ["git", "-C", str(project_root), "diff", "--name-only", baseline_ref, "--"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return {normalize_repo_path(line.strip()) for line in proc.stdout.splitlines() if line.strip()}


def path_allowed(path: str, allowed: list[str]) -> bool:
    p = normalize_repo_path(path)
    for raw in allowed:
        a = normalize_repo_path(raw)
        if not a:
            continue
        if a.endswith("/**"):
            prefix = a[:-3].rstrip("/")
            if p == prefix or p.startswith(prefix + "/"):
                return True
        elif p == a:
            return True
    return False


def extract_int(text: str, label: str) -> int | None:
    m = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*(\d+)\s*$", text)
    return int(m.group(1)) if m else None


def check_report_arithmetic(text: str) -> list[str]:
    errors: list[str] = []
    total = extract_int(text, "TEST TOTAL")
    passed = extract_int(text, "TEST PASS")
    failed = extract_int(text, "TEST FAIL")
    skipped = extract_int(text, "TEST SKIP")
    values = [passed, failed, skipped]
    if total is not None and all(v is not None for v in values):
        if total != sum(v for v in values if v is not None):
            errors.append(f"test arithmetic inconsistent: total={total}, parts={values}")
    return errors


def run_review_contract(skill_root: Path, task: Path, review: Path) -> list[str]:
    helper = skill_root / "scripts" / "check_review_contract.py"
    proc = subprocess.run(
        [sys.executable, str(helper), "--task", str(task), "--review", str(review)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return [proc.stderr.strip() or proc.stdout.strip() or "review contract validation failed"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skill-root", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--rules-manifest")
    parser.add_argument("--baseline-ref")
    parser.add_argument("--allowed-write", action="append", default=[])
    parser.add_argument("--clerk-report")
    parser.add_argument("--clerk-gate")
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    skill_root = Path(args.skill_root).expanduser().resolve()
    task_path = Path(args.task).expanduser().resolve()
    event_path = Path(args.event).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    findings: list[str] = []
    if not event_path.is_file():
        findings.append("terminal event missing")
        event: dict[str, Any] = {}
    else:
        try:
            event = load_json(event_path)
        except Exception as exc:
            findings.append(f"terminal event unreadable: {exc}")
            event = {}

    if not report_path.is_file():
        findings.append("declared report missing")
        report_text = ""
    else:
        report_text = report_path.read_text(encoding="utf-8", errors="replace")
        if not report_text.strip() or "PLACEHOLDER" in report_text or "TODO" in report_text:
            findings.append("declared report is empty/skeleton/placeholder")
        findings.extend(check_report_arithmetic(report_text))

    if event:
        expected_report = event.get("report_path")
        if expected_report and Path(str(expected_report)).expanduser().resolve() != report_path:
            findings.append("terminal event report_path does not match gated report")
        event_hash = event.get("report_sha256")
        if report_path.is_file() and event_hash and sha256_file(report_path) != event_hash:
            findings.append("gated report bytes differ from terminal event binding")
        if event.get("exit_code") not in (0, None):
            findings.append(f"worker process exit code was {event.get('exit_code')}")

    rules_manifest = args.rules_manifest or event.get("rules_manifest") if event else args.rules_manifest
    if rules_manifest:
        findings.extend(verify_rules_manifest(Path(str(rules_manifest)).expanduser().resolve()))

    role = str(event.get("role") or "").lower() if event else ""
    if role in {"reviewer", "verification", "verification-worker", "phase-auditor"} and report_path.is_file():
        findings.extend(run_review_contract(skill_root, task_path, report_path))

    allowed = [normalize_repo_path(x) for x in args.allowed_write if normalize_repo_path(x)]
    if args.baseline_ref and allowed:
        try:
            changed = git_changed_paths(project_root, args.baseline_ref)
            outside = sorted(p for p in changed if not path_allowed(p, allowed))
            if outside:
                findings.append("source changes outside declared allowed-write boundary: " + ", ".join(outside))
        except Exception as exc:
            findings.append(f"cannot verify source write boundary: {exc}")

    # A Clerk overlay is usable only if its own gate exists, is CLEAN, and binds
    # the exact Clerk report bytes. This prevents stale clean results being reused.
    if args.clerk_report or args.clerk_gate:
        if not (args.clerk_report and args.clerk_gate):
            findings.append("clerk overlay requires both --clerk-report and --clerk-gate")
        else:
            clerk_report = Path(args.clerk_report).expanduser().resolve()
            clerk_gate = Path(args.clerk_gate).expanduser().resolve()
            if not clerk_report.is_file() or not clerk_gate.is_file():
                findings.append("clerk overlay report/gate missing")
            else:
                try:
                    cg = load_json(clerk_gate)
                    if cg.get("status") != "CLEAN":
                        findings.append("clerk evidence gate is not CLEAN")
                    if cg.get("report_path") != str(clerk_report):
                        findings.append("clerk gate does not bind declared clerk report path")
                    if cg.get("report_sha256") != sha256_file(clerk_report):
                        findings.append("clerk gate does not bind current clerk report bytes")
                except Exception as exc:
                    findings.append(f"clerk gate unreadable: {exc}")

    status = "CLEAN" if not findings else "FINDINGS"
    result = {
        "status": status,
        "task_path": str(task_path),
        "event_path": str(event_path),
        "report_path": str(report_path),
        "report_sha256": sha256_file(report_path) if report_path.is_file() else None,
        "findings": findings,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
