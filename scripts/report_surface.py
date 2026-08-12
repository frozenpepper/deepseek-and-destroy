#!/usr/bin/env python3
"""Return a small, deliberately non-semantic prefix of a worker report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def surface(path: Path, *, max_lines: int = 12, max_chars: int = 2400) -> list[str]:
    lines: list[str] = []
    used = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        remaining = max_chars - used
        if remaining <= 0 or len(lines) >= max_lines:
            break
        if len(line) > remaining:
            line = line[: max(0, remaining - 1)] + "…"
        lines.append(line)
        used += len(line)
        if used >= max_chars:
            break
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--lines", type=int, default=12)
    ap.add_argument("--chars", type=int, default=2400)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    report = args.report.resolve()
    if not report.is_file():
        raise SystemExit(f"ERROR: report missing: {report}")
    lines = surface(report, max_lines=max(1, args.lines), max_chars=max(200, args.chars))
    if args.json:
        print(json.dumps({"report": str(report), "surface": lines}, indent=2, sort_keys=True))
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
