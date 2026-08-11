#!/usr/bin/env python3
"""Render the tiny explicit-path launch prompt for one DSD worker attempt."""
from __future__ import annotations

import argparse
from pathlib import Path

from _roles import ROLE_SKILLS
from _rules_snapshot import verify_snapshot


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--role", choices=sorted(ROLE_SKILLS), required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--worker-rules", type=Path, required=True, help="exact immutable worker-rules revision for this attempt")
    ap.add_argument("--task", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    for label, value in (("run-root", args.run_root), ("worker-rules", args.worker_rules), ("task", args.task), ("report", args.report)):
        if not value.is_absolute():
            raise SystemExit(f"ERROR: --{label} must be an absolute path: {value}")
    if args.output and not args.output.is_absolute():
        raise SystemExit(f"ERROR: --output must be an absolute path: {args.output}")

    run_root = args.run_root.resolve()
    task = args.task.resolve()
    report = args.report.resolve()
    rules = args.worker_rules.resolve()
    try:
        rules.relative_to(run_root / "worker-rules")
    except ValueError:
        raise SystemExit(f"ERROR: worker rules must be an immutable revision under {run_root / 'worker-rules'}: {rules}")
    if rules.name != "WORKER_RULES.md":
        raise SystemExit(f"ERROR: --worker-rules must name WORKER_RULES.md: {rules}")
    try:
        verify_snapshot(rules)
    except ValueError as exc:
        raise SystemExit(f"ERROR: invalid immutable worker-rules snapshot: {exc}")

    protocol_dir = rules.parent / "protocol"
    common = protocol_dir / "COMMON.md"
    role_skill = protocol_dir / ROLE_SKILLS[args.role]
    proof = protocol_dir / "PROOF-PATTERNS.md"

    for label, path in (("task", task), ("report", report)):
        try:
            path.relative_to(run_root)
        except ValueError:
            raise SystemExit(f"ERROR: {label} path is outside run root: {path}")

    required = [rules, common, role_skill, task, proof]
    missing = [p for p in required if not p.exists()]
    if missing:
        raise SystemExit("ERROR: missing launch authority: " + ", ".join(map(str, missing)))

    role_label = args.role.upper().replace("-", " ")
    prompt = (
        f"DSD {role_label} for {args.task_id}.\n"
        "Read and obey, in order:\n"
        f"1. {rules}\n"
        f"2. {common}\n"
        f"3. {role_skill} — this exact role skill defines your job.\n"
        f"4. {task}\n"
        f"5. {proof} — only patterns named by the contract revision are mandatory.\n"
        f"Report: {report}\n"
        "Resolve ordinary ambiguity from authority; do not ask for routine implementation-scope choices.\n"
        "Create/update the report early. Prefer the canonical Decision Packet/report shape, but preserve semantic evidence rather than sacrificing completed work to clerical formatting.\n"
        "Mark DSD_REPORT_STATUS: FINAL at truthful terminal completion when possible; the gate/Clerk handles non-semantic clerical defects.\n"
        "Final stdout <=3 short lines: FINAL <status>, report path, optional one-line result.\n"
    )

    if args.output:
        output = args.output.resolve()
        try:
            output.relative_to(run_root)
        except ValueError:
            raise SystemExit(f"ERROR: output path is outside run root: {output}")
        if output.exists():
            raise SystemExit(f"ERROR: immutable launch prompt already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(prompt, encoding="utf-8")
    else:
        print(prompt, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
