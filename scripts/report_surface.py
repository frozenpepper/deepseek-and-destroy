#!/usr/bin/env python3
"""Return the first bounded non-empty lines of a worker report.

This is context trimming only. It does not search for or interpret semantic markers.
If the prefix is insufficient, use Evidence Clerk or open exact evidence.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def extract(path: Path, max_lines: int) -> list[str]:
    if max_lines < 1:
        raise ValueError("max_lines must be >=1")
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        out.append(line)
        if len(out) >= max_lines:
            break
    if not out:
        raise ValueError("report contains no usable preview")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--max-lines", type=int, default=16)
    args = ap.parse_args()
    status = 0
    for path in args.reports:
        print(f"===== {path} =====")
        try:
            print("\n".join(extract(path, args.max_lines)))
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr); status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
