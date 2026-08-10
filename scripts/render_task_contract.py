#!/usr/bin/env python3
"""Render one immutable numbered DSD task-contract revision from compact slots.

The premium orchestrator supplies only the changing decision surface. This helper
owns headings, path validation, mechanical-evidence identity, and the resulting
SHA-256 recorded in state. Existing contract revisions are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: str) -> str:
    return " ".join(value.strip().split())


def bullet_lines(values: list[str], empty: str = "NONE") -> list[str]:
    values = [clean(v) for v in values if clean(v)]
    return [f"- {v}" for v in values] if values else [empty]


def absolute_existing(values: list[str], label: str) -> list[Path]:
    result: list[Path] = []
    for raw in values:
        path = Path(raw)
        if not path.is_absolute():
            raise ValueError(f"{label} path must be absolute: {path}")
        path = path.resolve()
        if not path.exists():
            raise ValueError(f"{label} path does not exist: {path}")
        result.append(path)
    return result


def normalize_write_prefix(raw: str) -> str:
    """Return a strict project-relative POSIX path/prefix.

    Broad `.`/empty prefixes and parent traversal are rejected because this section
    is used by the mechanical evidence gate, not just as prose guidance.
    """
    value = raw.strip().replace("\\", "/")
    if not value or value in {".", "./", "/"}:
        raise ValueError("allowed source change cannot be empty, '.', or project root")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"allowed source change must be project-relative without '..': {raw}")
    normalized = path.as_posix().rstrip("/")
    if not normalized:
        raise ValueError(f"invalid allowed source change: {raw}")
    if normalized == "DeepSeekAndDestroy" or normalized.startswith("DeepSeekAndDestroy/"):
        raise ValueError("DeepSeekAndDestroy/** is orchestration evidence, not project-source scope")
    return normalized


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--revision", type=int, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--objective", required=True)
    ap.add_argument("--risk", action="append", default=[])
    ap.add_argument("--acceptance", action="append", default=[])
    ap.add_argument("--task-output", action="append", default=[], help="task-level output/deliverable expectation; role report path is launch-specific")
    ap.add_argument("--authority", action="append", default=[], help="absolute governing source path")
    ap.add_argument("--input", action="append", default=[], help="absolute prior evidence/spec path")
    ap.add_argument("--expected-scope", action="append", default=[])
    ap.add_argument(
        "--write-path", action="append", default=[],
        help="exact project-relative file/directory prefix this task may mutate; repeatable",
    )
    ap.add_argument("--excluded", action="append", default=[])
    ap.add_argument("--mechanical", action="append", default=[], help="absolute immutable/current mechanical evidence path")
    ap.add_argument("--proof", action="append", default=[], help="compact proof-obligation row text")
    ap.add_argument("--verification", action="append", default=[])
    ap.add_argument("--clerk-check", action="append", default=[])
    ap.add_argument("--major-log", type=Path)
    ap.add_argument("--progress-file", type=Path)
    ap.add_argument("--evidence-dir", type=Path)
    args = ap.parse_args()

    if args.revision < 1:
        print("ERROR: --revision must be >= 1", file=sys.stderr)
        return 2
    if len(args.risk) > 3:
        print("ERROR: at most three --risk entries are allowed", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.task_id):
        print("ERROR: --task-id must be a compact filesystem-safe id", file=sys.stderr)
        return 2

    for label, path in (("run-root", args.run_root), ("output", args.output)):
        if not path.is_absolute():
            print(f"ERROR: --{label} must be absolute: {path}", file=sys.stderr)
            return 2
    for label, path in (("major-log", args.major_log), ("progress-file", args.progress_file), ("evidence-dir", args.evidence_dir)):
        if path is not None and not path.is_absolute():
            print(f"ERROR: --{label} must be absolute: {path}", file=sys.stderr)
            return 2

    run_root = args.run_root.resolve()
    output = args.output.resolve()
    if not run_root.is_dir():
        print(f"ERROR: run root does not exist: {run_root}", file=sys.stderr)
        return 2
    try:
        output.relative_to(run_root)
    except ValueError:
        print(f"ERROR: output must live under run root: {output}", file=sys.stderr)
        return 2
    if output.exists():
        print(f"ERROR: immutable contract revision already exists: {output}", file=sys.stderr)
        return 2

    try:
        authorities = absolute_existing(args.authority, "authority")
        inputs = absolute_existing(args.input, "input")
        mechanical = absolute_existing(args.mechanical, "mechanical")
        write_paths = list(dict.fromkeys(normalize_write_prefix(p) for p in args.write_path))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    task_root = output.parent.parent if output.parent.name == "contracts" else output.parent
    evidence_dir = args.evidence_dir.resolve() if args.evidence_dir else task_root / "evidence"
    major_log = args.major_log.resolve() if args.major_log else run_root / "major-findings-and-fixes.md"
    progress = args.progress_file.resolve() if args.progress_file else None
    project_root = None
    for ancestor in [run_root, *run_root.parents]:
        if ancestor.name == "DeepSeekAndDestroy":
            project_root = ancestor.parent
            break
    if project_root is None:
        print("ERROR: run root must live below a DeepSeekAndDestroy directory", file=sys.stderr)
        return 2
    if progress is not None:
        try:
            progress_rel = progress.relative_to(project_root).as_posix()
        except ValueError:
            print(f"ERROR: progress-file must live inside project root: {progress}", file=sys.stderr)
            return 2
        if progress_rel == "DeepSeekAndDestroy" or progress_rel.startswith("DeepSeekAndDestroy/"):
            print("ERROR: progress-file is for project documentation outside DeepSeekAndDestroy; use DSD run artifacts directly for orchestration files", file=sys.stderr)
            return 2
        if not any(progress_rel == prefix or progress_rel.startswith(prefix.rstrip("/") + "/") for prefix in write_paths):
            print(f"ERROR: progress-file must also be covered by --write-path: {progress_rel}", file=sys.stderr)
            return 2
    for label, path in (("evidence-dir", evidence_dir), ("major-log", major_log)):
        try:
            path.relative_to(run_root)
        except ValueError:
            print(f"ERROR: {label} must live under run root: {path}", file=sys.stderr)
            return 2

    acceptance = [clean(x) for x in args.acceptance if clean(x)]
    if acceptance:
        bad = [x for x in acceptance if not re.match(r"AC-\d+\b", x)]
        if bad:
            print("ERROR: each --acceptance must start with a stable AC-* id: " + "; ".join(bad), file=sys.stderr)
            return 2

    mechanical_lines = [
        f"- `{p}` | sha256={sha256(p) if p.is_file() else 'DIRECTORY'}"
        for p in mechanical
    ] or ["NONE"]

    lines = [
        f"# Task {args.task_id} — Contract r{args.revision:04d}",
        f"Contract revision: {args.revision}",
        "",
        "## Unit",
        clean(args.unit),
        "",
        "## Objective",
        clean(args.objective),
        "",
        "## Authority",
        *([f"- `{p}`" for p in authorities] if authorities else ["NONE — resolve from WORKER_RULES governing authority."]),
        "",
        "## Inputs",
        *([f"- `{p}`" for p in inputs] if inputs else ["NONE"]),
        "",
        "## Scope",
        "Expected:",
        *bullet_lines(args.expected_scope),
        "Excluded:",
        *bullet_lines(args.excluded),
        "Mechanical facts (current-contract identity):",
        *mechanical_lines,
        "",
        "## Allowed source changes",
        *([f"- `{p}`" for p in write_paths] if write_paths else ["NONE"]),
        "",
        "## Risk hypotheses",
        *([f"{i}. {clean(v)}" for i, v in enumerate(args.risk, 1)] if args.risk else ["NONE"]),
        "",
        "## Acceptance criteria",
        *([f"- {v}" for v in acceptance] if acceptance else ["ROLE-APPROPRIATE COMPLETION ONLY — no semantic ACs declared."]),
        "",
        "## Proof Obligations",
        *bullet_lines(args.proof),
        "",
        "## Verification",
        *bullet_lines(args.verification),
        "",
        "## Evidence Clerk Checks",
        *bullet_lines(args.clerk_check),
        "",
        "## Deliverables",
        "Task outputs:",
        *bullet_lines(args.task_output),
        "Role report: ASSIGNED BY IMMUTABLE LAUNCH HANDOFF",
        f"Evidence directory: `{evidence_dir}`",
        f"Major log: `{major_log}`",
        f"Configured progress file: `{progress}`" if progress else "Configured progress file: NONE",
        "",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    digest = sha256(output)
    print(json.dumps({
        "format": "dsd-task-contract-v2",
        "task_id": args.task_id,
        "revision": args.revision,
        "path": str(output),
        "sha256": digest,
        "allowed_source_changes": write_paths,
        "task_outputs": [clean(x) for x in args.task_output if clean(x)],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
