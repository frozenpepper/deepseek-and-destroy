#!/usr/bin/env python3
"""Render one immutable DSD task contract from one compact JSON spec."""
from __future__ import annotations

import argparse, hashlib, json, re, sys
from pathlib import Path, PurePosixPath
from typing import Any

FIELDS = {
    "run_root", "phase_id", "task_id", "revision", "output", "title", "objective",
    "authority", "inputs", "write_paths", "extra_inventory", "acceptance",
    "proof_obligations", "proof_patterns", "verification", "risks",
}
RETIRED = {"clerk_check", "clerk_checks", "evidence_clerk_checks"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: Any) -> str:
    return " ".join(str(value).strip().split())


def load_spec(raw: str) -> dict[str, Any]:
    data = json.load(sys.stdin) if raw == "-" else json.loads(Path(raw).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("contract spec must be one JSON object")
    retired = sorted(set(data) & RETIRED)
    if retired:
        raise ValueError("retired Clerk-recursion field present; Clerk is chosen only at semantic consumption boundaries")
    unknown = sorted(set(data) - FIELDS)
    if unknown:
        raise ValueError("unknown contract spec field(s): " + ", ".join(unknown))
    return data


def array(spec: dict[str, Any], name: str) -> list[str]:
    value = spec.get(name, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"spec field {name!r} must be an array")
    return [str(x) for x in value]


def project_root_from_run(run_root: Path) -> Path:
    for ancestor in [run_root, *run_root.parents]:
        if ancestor.name == "DeepSeekAndDestroy":
            return ancestor.parent.resolve()
    raise ValueError("run_root must live below DeepSeekAndDestroy/")


def existing_paths(values: list[str], project: Path, label: str) -> list[Path]:
    out = []
    for raw in values:
        p = Path(raw)
        p = (project / p).resolve() if not p.is_absolute() else p.resolve()
        if not p.exists():
            raise ValueError(f"{label} path does not exist: {p}")
        out.append(p)
    return out


def project_prefix(raw: str, label: str) -> str:
    value = raw.strip().replace("\\", "/")
    path = PurePosixPath(value)
    if not value or value in {".", "./", "/"} or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe {label}: {raw}")
    normalized = path.as_posix().rstrip("/")
    if normalized == "DeepSeekAndDestroy" or normalized.startswith("DeepSeekAndDestroy/"):
        raise ValueError(f"{label} cannot target DeepSeekAndDestroy/**")
    return normalized


def next_revision(directory: Path) -> int:
    nums = []
    if directory.is_dir():
        for p in directory.glob("r*.md"):
            m = re.fullmatch(r"r(\d+)\.md", p.name, re.I)
            if m: nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", required=True, help="JSON spec path or '-' for stdin")
    args = ap.parse_args()
    try:
        spec = load_spec(args.spec)
        for required in ("run_root", "task_id", "objective"):
            if not clean(spec.get(required, "")):
                raise ValueError(f"{required} is required")

        run = Path(str(spec["run_root"]))
        if not run.is_absolute(): raise ValueError("run_root must be absolute")
        run = run.resolve()
        if not run.is_dir(): raise ValueError(f"run root does not exist: {run}")
        project = project_root_from_run(run)

        task_id = str(spec["task_id"])
        phase_id = spec.get("phase_id")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", task_id): raise ValueError("task_id must be filesystem-safe")
        if phase_id is not None and not re.fullmatch(r"[A-Za-z0-9._-]+", str(phase_id)):
            raise ValueError("phase_id must be filesystem-safe")

        raw_output = spec.get("output")
        raw_revision = spec.get("revision")
        if raw_output is None:
            if phase_id is None: raise ValueError("phase_id is required when output is omitted")
            directory = run / "phases" / str(phase_id) / "tasks" / task_id / "contracts"
            revision = int(raw_revision) if raw_revision is not None else next_revision(directory)
            output = directory / f"r{revision:04d}.md"
        else:
            output = Path(str(raw_output)); output = (run / output).resolve() if not output.is_absolute() else output.resolve()
            try: output.relative_to(run)
            except ValueError as exc: raise ValueError(f"output must live under run root: {output}") from exc
            if raw_revision is not None: revision = int(raw_revision)
            else:
                m = re.fullmatch(r"r(\d+)\.md", output.name, re.I)
                revision = int(m.group(1)) if m else next_revision(output.parent)
        if revision < 1: raise ValueError("revision must be >= 1")
        if output.exists(): raise ValueError(f"immutable contract already exists: {output}")

        authority = existing_paths(array(spec, "authority"), project, "authority")
        inputs = existing_paths(array(spec, "inputs"), project, "input")
        writes = list(dict.fromkeys(project_prefix(x, "write_path") for x in array(spec, "write_paths")))
        inventory = list(dict.fromkeys(project_prefix(x, "extra_inventory") for x in array(spec, "extra_inventory")))
        acceptance_raw = [clean(x) for x in array(spec, "acceptance") if clean(x)]
        acceptance = [x if re.match(r"AC-\d+\b", x, re.I) else f"AC-{i:03d} — {x}" for i, x in enumerate(acceptance_raw, 1)]

        lines = [f"# Task {task_id} — {clean(spec.get('title') or task_id)}", f"Contract revision: r{revision:04d}", "", "## Objective", clean(spec["objective"]), ""]
        if authority: lines += ["## Authority", *[f"- `{p}`" for p in authority], ""]
        if inputs: lines += ["## Inputs", *[f"- `{p}`" for p in inputs], ""]
        lines += ["## Allowed source changes", *([f"- `{p}`" for p in writes] if writes else ["NONE"]), ""]
        for heading, values in (
            ("Extra scope inventory", inventory), ("Acceptance criteria", acceptance),
            ("Proof obligations", [clean(x) for x in array(spec, "proof_obligations") if clean(x)]),
            ("Proof patterns", [clean(x) for x in array(spec, "proof_patterns") if clean(x)]),
            ("Verification", [clean(x) for x in array(spec, "verification") if clean(x)]),
            ("Risk hypotheses", [clean(x) for x in array(spec, "risks") if clean(x)]),
        ):
            if values: lines += [f"## {heading}", *[f"- {x}" for x in values], ""]

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(json.dumps({"format":"dsd-task-contract-v6","task_id":task_id,"revision":revision,"path":str(output),"sha256":sha256(output),"writes_project":bool(writes)}, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
