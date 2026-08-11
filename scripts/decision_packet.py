#!/usr/bin/env python3
"""Extract a compact parent-facing decision surface from DSD worker reports.

Canonical ``## Decision Packet`` sections are preferred, but a long worker's useful
semantic evidence must not become unreadable merely because that heading was missed.
For noncanonical reports this helper extracts the most useful terminal fields and a
small amount of surrounding evidence; Evidence Clerk normalization remains the
proper route when a canonical packet is required for acceptance.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FIELD_RE = re.compile(
    r"^(?:DSD_REPORT_STATUS|Verdict|Goal / result|Goal/result|Verification|"
    r"Task-relevant defects|Clerk checks|Evidence)\s*:",
    re.IGNORECASE,
)


def _canonical(lines: list[str], max_lines: int) -> list[str] | None:
    start = next((i for i, line in enumerate(lines) if line.strip().lower() == "## decision packet"), None)
    if start is None:
        return None
    out = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        out.append(line)
        if len(out) >= max_lines:
            out.append("[Decision Packet truncated by extractor]")
            break
    return out


def _fallback(lines: list[str], max_lines: int) -> list[str]:
    selected: list[str] = ["## Decision Surface (noncanonical report)"]
    seen: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or not FIELD_RE.match(stripped):
            continue
        key = stripped.split(":", 1)[0].lower()
        if key in seen:
            continue
        seen.add(key)
        selected.append(stripped)
        if len(selected) >= max_lines:
            return selected

    # If the worker omitted canonical fields too, preserve a bounded semantic
    # glimpse rather than forcing the premium parent to open the whole report.
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped in selected:
            continue
        selected.append(stripped)
        if len(selected) >= max_lines:
            break
    if len(selected) == 1:
        raise ValueError("report contains no usable decision surface")
    selected.append("[Noncanonical report; use Evidence Clerk normalization before acceptance when required]")
    return selected


def extract(path: Path, max_lines: int) -> list[str]:
    lines = path.read_text(errors="replace").splitlines()
    return _canonical(lines, max_lines) or _fallback(lines, max_lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--max-lines", type=int, default=20)
    args = ap.parse_args()
    status = 0
    for path in args.reports:
        print(f"===== {path} =====")
        try:
            print("\n".join(extract(path, args.max_lines)))
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
