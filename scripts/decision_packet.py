#!/usr/bin/env python3
"""Extract compact Decision Packets from DeepSeek and Destroy worker reports."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def extract(path: Path, max_lines: int) -> list[str]:
    lines = path.read_text(errors="replace").splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().lower() == "## decision packet"), None)
    if start is None:
        raise ValueError("missing '## Decision Packet' section")
    out = [lines[start]]
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        out.append(line)
        if len(out) >= max_lines:
            out.append("[Decision Packet truncated by extractor]")
            break
    return out


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
