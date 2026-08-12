#!/usr/bin/env python3
"""Render one immutable numbered DSD task-contract revision from compact slots.

The premium orchestrator supplies only the changing semantic decision surface.
Inputs may be normal CLI slots or one JSON spec (`--spec FILE`, `--spec -` for
stdin). This helper owns headings, path validation, mechanical-evidence identity,
role-recursion preflight, and the resulting SHA-256 recorded in state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


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


def normalize_project_prefix(raw: str, label: str = "project path") -> str:
    value = raw.strip().replace("\\", "/")
    if not value or value in {".", "./", "/"}:
        raise ValueError(f"{label} cannot be empty, '.', or project root")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be project-relative without '..': {raw}")
    normalized = path.as_posix().rstrip("/")
    if normalized == "DeepSeekAndDestroy" or normalized.startswith("DeepSeekAndDestroy/"):
        raise ValueError(f"{label} cannot target DeepSeekAndDestroy/** orchestration evidence")
    return normalized


def normalize_write_prefix(raw: str) -> str:
    return normalize_project_prefix(raw, "allowed source change")


def read_spec(value: str) -> dict[str, Any]:
    try:
        text = sys.stdin.read() if value == "-" else Path(value).read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON contract spec {value!r}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("contract spec must be one JSON object")
    return data


def scalar_or_cli(spec: dict[str, Any], key: str, cli: Any) -> Any:
    return cli if cli is not None else spec.get(key)


def list_or_cli(spec: dict[str, Any], key: str, cli: list[str] | None) -> list[str]:
    if cli:
        return cli
    value = spec.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"spec field {key!r} must be a list of strings")
    return value


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", help="JSON spec path, or '-' for stdin; CLI values override scalar spec values and non-empty repeatable CLI lists override list fields")
    ap.add_argument("--run-root", type=Path)
    ap.add_argument("--task-id")
    ap.add_argument("--revision", type=int)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--unit")
    ap.add_argument("--objective")
    ap.add_argument("--role", choices=("implementer", "fixer", "reviewer", "verification", "discovery", "phase-surveyor", "recovery", "phase-auditor", "evidence-clerk"), help="optional intended launch role; used only for preflight footgun detection")
    ap.add_argument("--risk", action="append", default=[])
    ap.add_argument("--acceptance", action="append", default=[])
    ap.add_argument("--task-output", action="append", default=[], help="task-level output/deliverable expectation; role report path is launch-specific")
    ap.add_argument("--authority", action="append", default=[], help="absolute governing source path")
    ap.add_argument("--input", action="append", default=[], help="absolute prior evidence/spec path")
    ap.add_argument("--expected-scope", action="append", default=[])
    ap.add_argument("--write-path", action="append", default=[], help="exact project-relative file/directory prefix this task may mutate; repeatable")
    ap.add_argument("--extra-inventory", action="append", default=[], help="project-relative ignored/load-bearing root that the attempt baseline must inventory")
    ap.add_argument("--excluded", action="append", default=[])
    ap.add_argument("--mechanical", action="append", default=[], help="absolute immutable/current mechanical evidence path")
    ap.add_argument("--proof", action="append", default=[], help="compact proof-obligation text")
    ap.add_argument("--proof-pattern", action="append", default=[], help="optional reusable proof recipe tag; worker loads the proof library only when this is non-empty")
    ap.add_argument("--verification", action="append", default=[])
    ap.add_argument("--major-log", type=Path)
    ap.add_argument("--progress-file", type=Path)
    ap.add_argument("--evidence-dir", type=Path)
    return ap


def main() -> int:
    raw = parser().parse_args()
    try:
        spec = read_spec(raw.spec) if raw.spec else {}
        if "clerk_check" in spec:
            raise ValueError("contract field 'clerk_check' was removed in v15.3; Clerk is selected on demand at a parent decision boundary")
        run_root_v = scalar_or_cli(spec, "run_root", str(raw.run_root) if raw.run_root else None) or os.environ.get("DSD_RUN_ROOT")
        output_v = scalar_or_cli(spec, "output", str(raw.output) if raw.output else None)
        task_id = scalar_or_cli(spec, "task_id", raw.task_id)
        revision = scalar_or_cli(spec, "revision", raw.revision)
        unit = scalar_or_cli(spec, "unit", raw.unit)
        objective = scalar_or_cli(spec, "objective", raw.objective)
        role = scalar_or_cli(spec, "role", raw.role)
        required = {"run_root": run_root_v, "task_id": task_id, "revision": revision, "output": output_v, "unit": unit, "objective": objective}
        missing = [k for k, v in required.items() if v is None or (isinstance(v, str) and not v.strip())]
        if missing:
            raise ValueError("missing required contract field(s): " + ", ".join(missing))
        if not isinstance(revision, int):
            raise ValueError("revision must be an integer")

        run_root_path = Path(str(run_root_v))
        output_path = Path(str(output_v))
        if not output_path.is_absolute() and run_root_path.is_absolute():
            output_path = run_root_path / output_path
        args = argparse.Namespace(
            run_root=run_root_path, task_id=str(task_id), revision=revision,
            output=output_path, unit=str(unit), objective=str(objective), role=str(role) if role else None,
            risk=list_or_cli(spec, "risk", raw.risk), acceptance=list_or_cli(spec, "acceptance", raw.acceptance),
            task_output=list_or_cli(spec, "task_output", raw.task_output), authority=list_or_cli(spec, "authority", raw.authority),
            input=list_or_cli(spec, "input", raw.input), expected_scope=list_or_cli(spec, "expected_scope", raw.expected_scope),
            write_path=list_or_cli(spec, "write_path", raw.write_path), extra_inventory=list_or_cli(spec, "extra_inventory", raw.extra_inventory),
            excluded=list_or_cli(spec, "excluded", raw.excluded), mechanical=list_or_cli(spec, "mechanical", raw.mechanical),
            proof=list_or_cli(spec, "proof", raw.proof), proof_pattern=list_or_cli(spec, "proof_pattern", raw.proof_pattern), verification=list_or_cli(spec, "verification", raw.verification),
            major_log=Path(str(scalar_or_cli(spec, "major_log", str(raw.major_log) if raw.major_log else None))) if scalar_or_cli(spec, "major_log", str(raw.major_log) if raw.major_log else None) else None,
            progress_file=Path(str(scalar_or_cli(spec, "progress_file", str(raw.progress_file) if raw.progress_file else None))) if scalar_or_cli(spec, "progress_file", str(raw.progress_file) if raw.progress_file else None) else None,
            evidence_dir=Path(str(scalar_or_cli(spec, "evidence_dir", str(raw.evidence_dir) if raw.evidence_dir else None))) if scalar_or_cli(spec, "evidence_dir", str(raw.evidence_dir) if raw.evidence_dir else None) else None,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.revision < 1:
        print("ERROR: --revision must be >= 1", file=sys.stderr); return 2
    if len(args.risk) > 3:
        print("ERROR: at most three risk entries are allowed", file=sys.stderr); return 2
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.task_id):
        print("ERROR: task-id must be a compact filesystem-safe id", file=sys.stderr); return 2
    valid_roles = {"implementer", "fixer", "reviewer", "verification", "discovery", "phase-surveyor", "recovery", "phase-auditor", "evidence-clerk"}
    if args.role and args.role not in valid_roles:
        print(f"ERROR: invalid role in contract spec: {args.role}", file=sys.stderr); return 2

    for label, path in (("run-root", args.run_root), ("output", args.output)):
        if not path.is_absolute():
            print(f"ERROR: --{label} must be absolute: {path}", file=sys.stderr); return 2
    for label, path in (("major-log", args.major_log), ("progress-file", args.progress_file), ("evidence-dir", args.evidence_dir)):
        if path is not None and not path.is_absolute():
            print(f"ERROR: --{label} must be absolute: {path}", file=sys.stderr); return 2

    run_root = args.run_root.resolve(); output = args.output.resolve()
    if not run_root.is_dir():
        print(f"ERROR: run root does not exist: {run_root}", file=sys.stderr); return 2
    try: output.relative_to(run_root)
    except ValueError:
        print(f"ERROR: output must live under run root: {output}", file=sys.stderr); return 2
    if output.exists():
        print(f"ERROR: immutable contract revision already exists: {output}", file=sys.stderr); return 2

    try:
        authorities = absolute_existing(args.authority, "authority")
        inputs = absolute_existing(args.input, "input")
        mechanical = absolute_existing(args.mechanical, "mechanical")
        write_paths = list(dict.fromkeys(normalize_write_prefix(p) for p in args.write_path))
        extra_inventory = list(dict.fromkeys(normalize_project_prefix(p, "extra inventory root") for p in args.extra_inventory))
        if args.role == "evidence-clerk" and write_paths:
            raise ValueError("Evidence Clerk is always project-read-only; use a bounded writer task for project documentation changes")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2

    task_root = output.parent.parent if output.parent.name == "contracts" else output.parent
    evidence_dir = args.evidence_dir.resolve() if args.evidence_dir else task_root / "evidence"
    major_log = args.major_log.resolve() if args.major_log else run_root / "major-findings-and-fixes.md"
    progress = args.progress_file.resolve() if args.progress_file else None
    project_root = None
    for ancestor in [run_root, *run_root.parents]:
        if ancestor.name == "DeepSeekAndDestroy":
            project_root = ancestor.parent; break
    if project_root is None:
        print("ERROR: run root must live below a DeepSeekAndDestroy directory", file=sys.stderr); return 2
    if progress is not None:
        try: progress_rel = progress.relative_to(project_root).as_posix()
        except ValueError:
            print(f"ERROR: progress-file must live inside project root: {progress}", file=sys.stderr); return 2
        if progress_rel == "DeepSeekAndDestroy" or progress_rel.startswith("DeepSeekAndDestroy/"):
            print("ERROR: progress-file is for project documentation outside DeepSeekAndDestroy; use DSD run artifacts directly for orchestration files", file=sys.stderr); return 2
        if not any(progress_rel == prefix or progress_rel.startswith(prefix.rstrip("/") + "/") for prefix in write_paths):
            print(f"ERROR: progress-file must also be covered by write-path: {progress_rel}", file=sys.stderr); return 2
    for label, path in (("evidence-dir", evidence_dir), ("major-log", major_log)):
        try: path.relative_to(run_root)
        except ValueError:
            print(f"ERROR: {label} must live under run root: {path}", file=sys.stderr); return 2

    acceptance = [clean(x) for x in args.acceptance if clean(x)]
    if acceptance:
        bad = [x for x in acceptance if not re.match(r"AC-\d+\b", x)]
        if bad:
            print("ERROR: each acceptance entry must start with a stable AC-* id: " + "; ".join(bad), file=sys.stderr); return 2

    mechanical_lines = [f"- `{p}` | sha256={sha256(p) if p.is_file() else 'DIRECTORY'}" for p in mechanical] or ["NONE"]
    lines = [f"# Task {args.task_id} — {clean(args.unit)}", f"Contract revision: r{args.revision:04d}", "", "## Objective", clean(args.objective), ""]
    if authorities: lines += ["## Authority", *[f"- `{p}`" for p in authorities], ""]
    if inputs: lines += ["## Inputs", *[f"- `{p}`" for p in inputs], ""]
    if args.expected_scope or args.excluded or mechanical:
        lines += ["## Scope"]
        if args.expected_scope: lines += ["Expected:", *bullet_lines(args.expected_scope)]
        if args.excluded: lines += ["Excluded:", *bullet_lines(args.excluded)]
        if mechanical: lines += ["Mechanical facts (current-contract identity):", *mechanical_lines]
        lines += [""]
    lines += ["## Allowed source changes", *([f"- `{p}`" for p in write_paths] if write_paths else ["NONE"]), ""]
    if extra_inventory:
        lines += ["## Extra scope inventory", *[f"- `{p}`" for p in extra_inventory], ""]
    if args.risk: lines += ["## Risk hypotheses", *[f"{i}. {clean(v)}" for i, v in enumerate(args.risk, 1)], ""]
    lines += ["## Acceptance criteria", *([f"- {v}" for v in acceptance] if acceptance else ["ROLE-APPROPRIATE COMPLETION ONLY — no semantic ACs declared."]), ""]
    if args.proof: lines += ["## Proof Obligations", *bullet_lines(args.proof), ""]
    if args.proof_pattern:
        patterns = [clean(x).upper() for x in args.proof_pattern if clean(x)]
        bad_patterns = [x for x in patterns if not re.fullmatch(r"[A-Z][A-Z0-9-]*", x)]
        if bad_patterns:
            print("ERROR: invalid proof-pattern tag(s): " + ", ".join(bad_patterns), file=sys.stderr); return 2
        lines += ["## Proof patterns", *bullet_lines(list(dict.fromkeys(patterns))), ""]
    if args.verification: lines += ["## Verification", *bullet_lines(args.verification), ""]
    task_outputs = [clean(x) for x in args.task_output if clean(x)]
    if progress: task_outputs.append(f"Maintain configured progress/documentation file when role-authorized: `{progress}`")
    if task_outputs: lines += ["## Task outputs", *[f"- {x}" for x in task_outputs], ""]

    output.parent.mkdir(parents=True, exist_ok=True); output.write_text("\n".join(lines), encoding="utf-8")
    digest = sha256(output)
    print(json.dumps({
        "format": "dsd-task-contract-v4", "task_id": args.task_id, "revision": args.revision,
        "path": str(output), "sha256": digest, "allowed_source_changes": write_paths,
        "extra_scope_inventory": extra_inventory, "task_outputs": [clean(x) for x in args.task_output if clean(x)],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
