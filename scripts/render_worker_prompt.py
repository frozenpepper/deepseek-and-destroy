#!/usr/bin/env python3
"""Render one minimal explicit-path DSD worker launch prompt."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from _roles import ROLE_SKILLS
from _rules_snapshot import verify_snapshot
from _task_contract import proof_patterns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--role", choices=sorted(ROLE_SKILLS), required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--worker-rules", type=Path, required=True)
    ap.add_argument("--task", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--evidence", type=Path, action="append", default=[], help="immutable prior evidence file needed by this role; path+sha256 are embedded in the prompt")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    for label, value in (("run-root", args.run_root), ("worker-rules", args.worker_rules), ("task", args.task), ("report", args.report)):
        if not value.is_absolute():
            raise SystemExit(f"ERROR: --{label} must be absolute: {value}")
    if args.output and not args.output.is_absolute():
        raise SystemExit(f"ERROR: --output must be absolute: {args.output}")

    run_root = args.run_root.resolve()
    rules = args.worker_rules.resolve()
    task = args.task.resolve()
    report = args.report.resolve()
    evidence = [p.resolve() for p in args.evidence]
    try:
        rules.relative_to(run_root / "worker-rules")
        task.relative_to(run_root)
        report.relative_to(run_root)
        for path in evidence:
            path.relative_to(run_root)
    except ValueError as exc:
        raise SystemExit(f"ERROR: launch authority must live under the active run: {exc}")
    if rules.name != "WORKER_RULES.md":
        raise SystemExit(f"ERROR: --worker-rules must name WORKER_RULES.md: {rules}")
    try:
        verify_snapshot(rules)
    except ValueError as exc:
        raise SystemExit(f"ERROR: invalid immutable worker-rules snapshot: {exc}")

    protocol = rules.parent / "protocol"
    common = protocol / "COMMON.md"
    role = protocol / ROLE_SKILLS[args.role]
    needed = [rules, common, role, task]
    patterns = proof_patterns(task.read_text(encoding="utf-8", errors="replace"))
    proof = protocol / "PROOF-PATTERNS.md"
    if patterns:
        needed.append(proof)
    needed += evidence
    missing = [p for p in needed if not p.is_file()]
    if missing:
        raise SystemExit("ERROR: missing launch authority: " + ", ".join(map(str, missing)))

    lines = [
        f"DSD {args.role.upper().replace('-', ' ')} — {args.task_id}",
        "Read only these authorities:",
        f"1. {rules}",
        f"2. {common}",
        f"3. {role}",
        f"4. {task}",
    ]
    if patterns:
        lines.append(f"5. {proof} — only: {', '.join(patterns)}")
    if evidence:
        lines.append("Evidence inputs (read as evidence, not authority):")
        for path in evidence:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"- {path} | sha256={digest}")
    lines += [
        f"Report: {report}",
        "Do the bounded role task. Preserve truthful evidence; report format is guidance, not a gate.",
        "No delegation. Final stdout: status + report path only.",
    ]
    prompt = "\n".join(lines) + "\n"

    if args.output:
        output = args.output.resolve()
        try:
            output.relative_to(run_root)
        except ValueError:
            raise SystemExit(f"ERROR: output is outside run root: {output}")
        if output.exists():
            raise SystemExit(f"ERROR: immutable launch prompt already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(prompt, encoding="utf-8")
    else:
        print(prompt, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
