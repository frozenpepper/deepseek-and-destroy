#!/usr/bin/env python3
"""Render the tiny path-only launch prompt for one DSD worker attempt."""
from __future__ import annotations

import argparse
from pathlib import Path

from _rules_snapshot import verify_snapshot

ROLE_PROTOCOL = {
    "implementer": "BUILD.md",
    "fixer": "BUILD.md",
    "reviewer": "REVIEW.md",
    "verification": "REVIEW.md",
    "recovery": "REVIEW.md",
    "phase-auditor": "REVIEW.md",
    "evidence-clerk": "EVIDENCE.md",
    "discovery": None,
    "phase-surveyor": None,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--role", choices=sorted(ROLE_PROTOCOL), required=True)
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
    core = protocol_dir / "CORE.md"
    roles = protocol_dir / "ROLES.md"
    supplement_name = ROLE_PROTOCOL[args.role]
    supplement = protocol_dir / supplement_name if supplement_name else None
    proof = protocol_dir / "PROOF-PATTERNS.md"

    for label, path in (("task", task), ("report", report)):
        try:
            path.relative_to(run_root)
        except ValueError:
            raise SystemExit(f"ERROR: {label} path is outside run root: {path}")

    required = [rules, core, roles, task, proof]
    if supplement:
        required.append(supplement)
    missing = [p for p in required if not p.exists()]
    if missing:
        raise SystemExit("ERROR: missing launch authority: " + ", ".join(map(str, missing)))

    role_label = args.role.upper().replace("-", " ")
    read_lines = [
        f"1. {rules}",
        f"2. {core}",
        f"3. {roles} — obey the {role_label} section only.",
        f"4. {task}",
    ]
    next_index = 5
    if supplement:
        read_lines.append(f"{next_index}. {supplement}")
        next_index += 1
    read_lines.append(f"{next_index}. {proof} — only patterns named by the contract revision are mandatory.")

    prompt = (
        f"DSD {role_label} for {args.task_id}.\n"
        "Read and obey, in order:\n"
        + "\n".join(read_lines)
        + f"\nReport: {report}\n"
        "Resolve ordinary ambiguity from authority; do not ask for routine implementation-scope choices.\n"
        "Create/update the report early; set DSD_REPORT_STATUS: FINAL only at truthful terminal completion.\n"
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
