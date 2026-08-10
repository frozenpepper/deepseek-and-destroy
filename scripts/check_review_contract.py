#!/usr/bin/env python3
"""Structurally validate a DSD task/reviewer proof contract.

This helper does NOT judge software correctness. It checks that the reviewer
covered every task AC in a Proof Matrix and that fast-path metadata is internally
consistent with the review's own declared defects/results.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

AC_RE = re.compile(r"\bAC-\d+\b", re.IGNORECASE)
FAST_RE = re.compile(r"^\s*FAST-PATH\s+ELIGIBLE\s*:\s*(YES|NO)\b", re.IGNORECASE | re.MULTILINE)
DEFECT_RE = re.compile(r"^\s*TASK-RELEVANT\s+DEFECTS\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
VERDICT_RE = re.compile(r"^\s*VERDICT\s*:\s*(PASS|FAIL)\s*$", re.IGNORECASE | re.MULTILINE)
PROOF_HEADING_RE = re.compile(r"^##\s+Proof\s+Matrix\s*$", re.IGNORECASE | re.MULTILINE)
HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"ERROR: cannot read {path}: {exc}") from exc


def ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        item = item.upper()
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def extract_task_acs(text: str) -> list[str]:
    return ordered_unique(AC_RE.findall(text))


def proof_section(text: str) -> str:
    match = PROOF_HEADING_RE.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = HEADING_RE.search(text, start)
    return text[start : next_heading.start() if next_heading else len(text)]


def parse_matrix(text: str) -> dict[str, dict[str, str]]:
    section = proof_section(text)
    rows: dict[str, dict[str, str]] = {}
    for raw in section.splitlines():
        line = raw.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        match = AC_RE.fullmatch(cells[0])
        if not match:
            continue
        ac = match.group(0).upper()
        if len(cells) < 7:
            rows[ac] = {"error": f"matrix row has {len(cells)} columns; expected >=7"}
            continue
        rows[ac] = {
            "mechanism": cells[1],
            "positive": cells[2],
            "negative": cells[3],
            "dimensions": cells[4],
            "counterexample": cells[5],
            "result": cells[6].upper(),
        }
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True, help="immutable DSD task-contract revision")
    parser.add_argument("--review", type=Path, required=True, help="review report")
    parser.add_argument("--require-pass", action="store_true", help="also require reviewer PASS + all rows PASS")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()

    task_text = read(args.task)
    review_text = read(args.review)
    task_acs = extract_task_acs(task_text)
    matrix = parse_matrix(review_text)
    errors: list[str] = []

    if not task_acs:
        errors.append("task contains no stable AC-* identifiers")
    if not matrix:
        errors.append("review contains no parseable ## Proof Matrix rows")

    for ac in task_acs:
        row = matrix.get(ac)
        if row is None:
            errors.append(f"missing Proof Matrix row for {ac}")
            continue
        if "error" in row:
            errors.append(f"{ac}: {row['error']}")
            continue
        if not row["mechanism"] or row["mechanism"].upper() in {"N/A", "NA", "?"}:
            errors.append(f"{ac}: mechanism explanation is empty/N/A")
        if row["result"] not in {"PASS", "FAIL"}:
            errors.append(f"{ac}: result must be PASS or FAIL, got {row['result']!r}")

    extra = sorted(set(matrix) - set(task_acs))

    fast_match = FAST_RE.search(review_text)
    defect_match = DEFECT_RE.search(review_text)
    verdict_match = VERDICT_RE.search(review_text)
    fast = fast_match.group(1).upper() if fast_match else None
    defects = defect_match.group(1).strip() if defect_match else None
    verdict = verdict_match.group(1).upper() if verdict_match else None

    if fast is None:
        errors.append("missing FAST-PATH ELIGIBLE: YES|NO")
    if defects is None:
        errors.append("missing TASK-RELEVANT DEFECTS: ...")
    if verdict is None:
        errors.append("missing literal VERDICT: PASS|FAIL")

    row_failures = sorted(ac for ac, row in matrix.items() if row.get("result") == "FAIL")
    defects_none = defects is not None and defects.upper() == "NONE"

    if fast == "YES":
        if not defects_none:
            errors.append("FAST-PATH YES conflicts with non-NONE/missing task-relevant defects")
        if verdict != "PASS":
            errors.append("FAST-PATH YES requires VERDICT: PASS")
        if row_failures:
            errors.append("FAST-PATH YES conflicts with FAIL Proof Matrix rows: " + ", ".join(row_failures))
        missing = [ac for ac in task_acs if ac not in matrix]
        if missing:
            errors.append("FAST-PATH YES conflicts with missing AC rows")

    if verdict == "PASS":
        if row_failures:
            errors.append("VERDICT PASS conflicts with FAIL Proof Matrix rows: " + ", ".join(row_failures))
        if not defects_none:
            errors.append("VERDICT PASS requires TASK-RELEVANT DEFECTS: NONE")

    if args.require_pass:
        if verdict != "PASS":
            errors.append("--require-pass: reviewer verdict is not PASS")
        for ac in task_acs:
            if matrix.get(ac, {}).get("result") != "PASS":
                errors.append(f"--require-pass: {ac} is not PASS")
        if fast != "YES":
            errors.append("--require-pass: FAST-PATH ELIGIBLE is not YES")

    result = {
        "ok": not errors,
        "task": str(args.task),
        "review": str(args.review),
        "task_acs": task_acs,
        "matrix_acs": sorted(matrix),
        "extra_matrix_acs": extra,
        "verdict": verdict,
        "fast_path": fast,
        "task_relevant_defects": defects,
        "errors": errors,
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("REVIEW CONTRACT: " + ("PASS" if result["ok"] else "FAIL"))
        print(f"AC coverage: {len(matrix)}/{len(task_acs)} matrix rows (task ACs)")
        if extra:
            print("Extra matrix ACs: " + ", ".join(extra))
        print(f"Reviewer verdict: {verdict or 'MISSING'}")
        print(f"Fast-path: {fast or 'MISSING'}")
        print(f"Task-relevant defects: {defects or 'MISSING'}")
        for error in errors:
            print("- " + error)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
