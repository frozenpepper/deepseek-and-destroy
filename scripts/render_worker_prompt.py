#!/usr/bin/env python3
"""Render one tiny explicit-path DSD worker handoff."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from _contract import proof_pattern_tags
from _roles import ROLE_SKILLS
from _rules_snapshot import verify_snapshot


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--role", choices=sorted(ROLE_SKILLS), required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--worker-rules", type=Path, required=True)
    ap.add_argument("--task", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--input", action="append", default=[])
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    for label, value in (("run-root", args.run_root), ("worker-rules", args.worker_rules), ("task", args.task), ("report", args.report)):
        if not value.is_absolute():
            raise SystemExit(f"ERROR: --{label} must be absolute: {value}")
    if args.output and not args.output.is_absolute():
        raise SystemExit(f"ERROR: --output must be absolute: {args.output}")

    run_root = args.run_root.resolve()
    task = args.task.resolve()
    report = args.report.resolve()
    rules = args.worker_rules.resolve()
    try:
        rules.relative_to(run_root / "worker-rules")
    except ValueError:
        raise SystemExit(f"ERROR: worker rules must be under {run_root / 'worker-rules'}: {rules}")
    if rules.name != "WORKER_RULES.md":
        raise SystemExit("ERROR: --worker-rules must name WORKER_RULES.md")
    try:
        verify_snapshot(rules)
    except ValueError as exc:
        raise SystemExit(f"ERROR: invalid worker-rules snapshot: {exc}")

    protocol = rules.parent / "protocol"
    common = protocol / "COMMON.md"
    role_skill = protocol / ROLE_SKILLS[args.role]
    proof = protocol / "PROOF-PATTERNS.md"
    task_text = task.read_text(encoding="utf-8", errors="replace")
    load_proof = args.role != "evidence-clerk" and bool(proof_pattern_tags(task_text))

    for label, path in (("task", task), ("report", report)):
        try:
            path.relative_to(run_root)
        except ValueError:
            raise SystemExit(f"ERROR: {label} path is outside run root: {path}")

    inputs = [Path(x).resolve() for x in args.input]
    for path in inputs:
        try:
            path.relative_to(run_root)
        except ValueError:
            raise SystemExit(f"ERROR: input is outside run root: {path}")
        if not path.exists():
            raise SystemExit(f"ERROR: input missing: {path}")

    required = [rules, common, role_skill, task] + ([proof] if load_proof else [])
    missing = [p for p in required if not p.exists()]
    if missing:
        raise SystemExit("ERROR: missing launch authority: " + ", ".join(map(str, missing)))

    reads = [rules, common, role_skill, task] + ([proof] if load_proof else [])
    lines = [f"DSD {args.role.upper().replace('-', ' ')} for {args.task_id}.", "Read, in order:"]
    lines += [f"{i}. {path}" for i, path in enumerate(reads, 1)]
    if inputs:
        def digest(path: Path) -> str:
            h = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()
        lines += ["Additional exact inputs (path + SHA-256):", *[f"- {path} | {digest(path)}" for path in inputs]]
    lines += [
        f"Report: {report}",
        "This attempt has its own report path. Make that report self-contained; start it early and keep it current.",
        "Do the bounded role task from authority. Preserve truthful semantic evidence; report formatting is not a protocol.",
        "Final stdout: report path plus at most one short conclusion.",
    ]
    prompt = "\n".join(lines) + "\n"

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
