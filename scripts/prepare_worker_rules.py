#!/usr/bin/env python3
"""Create one immutable versioned DSD run-level worker-rules snapshot.

Stable worker/harness/project rules are written once per revision so the premium
orchestrator never retypes them in task prompts and old attempts always keep the
exact protocol they actually received.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from _roles import ROLE_SKILLS
from _rules_snapshot import MANIFEST_FORMAT, PROTOCOL_NAMES, protocol_fingerprint, sha256_file, verify_snapshot

PROTOCOL_FILES = {
    "COMMON.md": "worker/COMMON.md",
    "PROOF-PATTERNS.md": "worker/PROOF-PATTERNS.md",
    **{path: f"worker/{path}" for path in ROLE_SKILLS.values()},
}


def manifest_payload(revision: int, output: Path, protocol_dir: Path) -> dict:
    return {
        "format": MANIFEST_FORMAT,
        "revision": revision,
        "path": str(output),
        "sha256": sha256_file(output),
        "protocol_dir": str(protocol_dir),
        "protocol_fingerprint": protocol_fingerprint(protocol_dir),
        "protocol": {name: sha256_file(protocol_dir / name) for name in PROTOCOL_NAMES},
    }


def emit(revision: int, output: Path, protocol_dir: Path, manifest_path: Path) -> None:
    result = verify_snapshot(output)
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--revision", type=int, default=1)
    ap.add_argument("--project-instruction", action="append", default=[])
    ap.add_argument("--rule", action="append", default=[], help="stable run-specific execution rule")
    ap.add_argument("--model", default="opencode-go/deepseek-v4-flash")
    ap.add_argument("--worker-harness", default="opencode-cli")
    ap.add_argument("--reuse-existing", action="store_true", help="verify and reuse this exact immutable rules revision")
    args = ap.parse_args()

    if args.revision < 1:
        print("ERROR: --revision must be >= 1", file=sys.stderr)
        return 2
    for label, value in (("project-root", args.project_root), ("run-root", args.run_root), ("plan", args.plan)):
        if not value.is_absolute():
            print(f"ERROR: --{label} must be an absolute path: {value}", file=sys.stderr)
            return 2
    project_root = args.project_root.resolve()
    run_root = args.run_root.resolve()
    skill_root = args.skill_root.resolve()
    plan = args.plan.resolve()

    try:
        run_root.relative_to(project_root / "DeepSeekAndDestroy")
    except ValueError:
        print(f"ERROR: run root must live under {project_root / 'DeepSeekAndDestroy'}: {run_root}", file=sys.stderr)
        return 2
    if not project_root.is_dir():
        print(f"ERROR: project root does not exist: {project_root}", file=sys.stderr)
        return 2
    if not skill_root.is_dir():
        print(f"ERROR: skill root does not exist: {skill_root}", file=sys.stderr)
        return 2
    if not plan.exists():
        print(f"ERROR: plan does not exist: {plan}", file=sys.stderr)
        return 2

    revision_root = run_root / "worker-rules" / f"r{args.revision:04d}"
    protocol_dir = revision_root / "protocol"
    output = revision_root / "WORKER_RULES.md"
    manifest_path = revision_root / "MANIFEST.json"
    required_existing = [output, manifest_path, *[protocol_dir / name for name in PROTOCOL_NAMES]]
    if revision_root.exists():
        if args.reuse_existing and all(path.is_file() for path in required_existing):
            try:
                emit(args.revision, output, protocol_dir, manifest_path)
            except ValueError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2
            return 0
        print(
            f"ERROR: worker-rule revision is immutable once created: {revision_root}. "
            "Use --reuse-existing for the exact revision or create the next revision; never overwrite historical worker instructions.",
            file=sys.stderr,
        )
        return 2

    instruction_args = [Path(p) for p in args.project_instruction]
    relative_instructions = [p for p in instruction_args if not p.is_absolute()]
    if relative_instructions:
        print("ERROR: --project-instruction paths must be absolute: " + ", ".join(map(str, relative_instructions)), file=sys.stderr)
        return 2
    instructions = [p.resolve() for p in instruction_args]
    missing = [p for p in instructions if not p.exists()]
    if missing:
        print("ERROR: project instruction file(s) missing: " + ", ".join(map(str, missing)), file=sys.stderr)
        return 2

    # Build into a temporary sibling first so an interrupted copy cannot leave a
    # seemingly valid partial immutable revision.
    revision_root.parent.mkdir(parents=True, exist_ok=True)
    tmp_root = revision_root.with_name(revision_root.name + ".tmp")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_protocol = tmp_root / "protocol"
    tmp_protocol.mkdir(parents=True, exist_ok=False)
    try:
        for dest_name, rel_source in PROTOCOL_FILES.items():
            source = skill_root / rel_source
            if not source.exists():
                raise FileNotFoundError(f"missing worker protocol source: {source}")
            dest = tmp_protocol / dest_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)

        rules = [
            "Launcher working directory is PROJECT ROOT; use the exact supplied run/report paths.",
        ]
        rules.extend(args.rule)

        generated = datetime.now(timezone.utc).isoformat()
        text = [
            "# DeepSeek and Destroy Run Rules",
            "",
            f"Revision: {args.revision}",
            f"Generated: {generated}",
            f"Project root: `{project_root}`",
            f"Run root: `{run_root}`",
            f"Authoritative plan: `{plan}`",
            f"Worker harness: `{args.worker_harness}`",
            f"Worker model: `{args.model}`",
            "",
            "## Governing project instructions",
        ]
        if instructions:
            text.extend(f"- `{p}`" for p in instructions)
        else:
            text.append("- NONE")
        if rules:
            text += ["", "## Run-specific rules", *[f"- {rule}" for rule in rules]]
        text += [
            "",
            "Universal behavior is in COMMON.md; specialist behavior is in the exact selected role SKILL.md.",
            "",
        ]
        tmp_output = tmp_root / "WORKER_RULES.md"
        tmp_output.write_text("\n".join(text), encoding="utf-8")
        payload = manifest_payload(args.revision, tmp_output, tmp_protocol)
        # Record final durable paths, while preserving hashes calculated from the
        # completed temporary tree that is about to be atomically renamed.
        payload["path"] = str(output)
        payload["protocol_dir"] = str(protocol_dir)
        (tmp_root / "MANIFEST.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp_root.rename(revision_root)
    except Exception as exc:
        shutil.rmtree(tmp_root, ignore_errors=True)
        print(f"ERROR: cannot create worker-rule revision: {exc}", file=sys.stderr)
        return 2

    try:
        emit(args.revision, output, protocol_dir, manifest_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
