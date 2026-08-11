#!/usr/bin/env python3
"""Inspect a DSD Reviewer report against task ACs without judging software semantics.

A canonical Proof Matrix is preferred because it gives a cheap decision surface.
Formatting/coverage that cannot be parsed is a Clerk-normalizable condition, not an
automatic invalidation of a long review. Explicit semantic contradictions remain
hard errors.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

AC_RE = re.compile(r"\bAC-\d+\b", re.IGNORECASE)
DEFECT_RE = re.compile(r"^\s*TASK-RELEVANT\s+DEFECTS\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
VERDICT_RE = re.compile(r"^\s*VERDICT\s*:\s*(PASS|FAIL)\s*$", re.IGNORECASE | re.MULTILINE)
PROOF_HEADING_RE = re.compile(r"^##\s+Proof\s+Matrix\s*$", re.IGNORECASE | re.MULTILINE)
HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


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
    """Parse the canonical table when present; non-table review prose is left for Clerk."""
    rows: dict[str, dict[str, str]] = {}
    for raw in proof_section(text).splitlines():
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
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    task_text = read(args.task)
    review_text = read(args.review)
    task_acs = extract_task_acs(task_text)
    review_acs = set(extract_task_acs(review_text))
    matrix = parse_matrix(review_text)
    errors: list[str] = []
    normalize: list[str] = []

    if not task_acs:
        errors.append("task contains no stable AC-* identifiers")

    verdict_match = VERDICT_RE.search(review_text)
    verdict = verdict_match.group(1).upper() if verdict_match else None
    defect_match = DEFECT_RE.search(review_text)
    defects = defect_match.group(1).strip() if defect_match else None

    if verdict is None:
        errors.append("missing literal VERDICT: PASS|FAIL")

    if not matrix and task_acs:
        normalize.append("canonical Proof Matrix is absent/unparseable")

    # Serialization can be normalized, but a Reviewer that never even accounts
    # for an AC leaves no stable semantic anchor for the Clerk to normalize.
    # Requiring the AC id somewhere is intentionally much weaker than requiring
    # a particular Markdown table shape.
    missing_semantic_acs = [ac for ac in task_acs if ac not in review_acs]
    if missing_semantic_acs:
        errors.append("review does not account for task AC id(s): " + ", ".join(missing_semantic_acs))

    for ac in task_acs:
        row = matrix.get(ac)
        if row is None:
            normalize.append(f"{ac} has no canonical Proof Matrix row")
            continue
        if "error" in row:
            normalize.append(f"{ac}: {row['error']}")
            continue
        if not row["mechanism"] or row["mechanism"].upper() in {"N/A", "NA", "?"}:
            normalize.append(f"{ac}: mechanism explanation is empty/N/A")
        if row["result"] not in {"PASS", "FAIL"}:
            normalize.append(f"{ac}: result is not canonical PASS/FAIL")

    row_failures = sorted(ac for ac, row in matrix.items() if row.get("result") == "FAIL")
    defects_none = defects is not None and defects.upper() == "NONE"
    if verdict == "PASS":
        if row_failures:
            errors.append("VERDICT PASS conflicts with explicit FAIL Proof Matrix rows: " + ", ".join(row_failures))
        if defects is None:
            normalize.append("PASS review omitted Task-relevant defects summary")
        elif not defects_none:
            errors.append("VERDICT PASS conflicts with non-NONE task-relevant defects")

    if args.require_pass and verdict != "PASS":
        errors.append("--require-pass: reviewer verdict is not PASS")
    if args.require_pass:
        for ac in task_acs:
            row = matrix.get(ac, {})
            if row and row.get("result") == "FAIL":
                errors.append(f"--require-pass: {ac} is explicitly FAIL")

    result = {
        "ok": not errors and not normalize,
        "semantic_ok": not errors,
        "normalization_required": bool(normalize),
        "normalization_reasons": list(dict.fromkeys(normalize)),
        "task": str(args.task),
        "review": str(args.review),
        "task_acs": task_acs,
        "review_acs": sorted(review_acs),
        "matrix_acs": sorted(matrix),
        "extra_matrix_acs": sorted(set(matrix) - set(task_acs)),
        "verdict": verdict,
        "task_relevant_defects": defects,
        "errors": errors,
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        state = "PASS" if result["ok"] else "NORMALIZE" if result["semantic_ok"] else "FAIL"
        print("REVIEW CONTRACT: " + state)
        print(f"AC coverage: {len(matrix)}/{len(task_acs)} canonical rows")
        print(f"Reviewer verdict: {verdict or 'MISSING'}")
        for reason in result["normalization_reasons"]:
            print("- normalize: " + reason)
        for error in errors:
            print("- error: " + error)

    if errors:
        return 1
    if normalize:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
