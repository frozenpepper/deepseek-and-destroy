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

from _rules_snapshot import PROTOCOL_NAMES, protocol_fingerprint, sha256_file, verify_snapshot

PROTOCOL_FILES = {
    "CORE.md": "worker/SKILL.md",
    "ROLES.md": "worker/ROLES.md",
    "BUILD.md": "worker/BUILD.md",
    "REVIEW.md": "worker/REVIEW.md",
    "EVIDENCE.md": "worker/EVIDENCE.md",
    "PROOF-PATTERNS.md": "worker/PROOF-PATTERNS.md",
}


def manifest_payload(revision: int, output: Path, protocol_dir: Path) -> dict:
    return {
        "format": "dsd-worker-rules-manifest-v1",
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

    revision_root.parent.mkdir(parents=True, exist_ok=True)
    tmp_root = revision_root.with_name(revision_root.name + ".tmp")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_protocol = tmp_root / "protocol"
    tmp_protocol.mkdir(parents=True, exist_ok=False)
    manifest_lines: list[str] = []
    try:
        for dest_name, rel_source in PROTOCOL_FILES.items():
            source = skill_root / rel_source
            if not source.exists():
                raise FileNotFoundError(f"missing worker protocol source: {source}")
            dest = tmp_protocol / dest_name
            shutil.copyfile(source, dest)
            manifest_lines.append(f"- {dest_name}: `{sha256_file(dest)}`")

        rules = [
            "The launcher fixes the worker working directory to PROJECT ROOT. Do not change directory merely to compensate for a path mistake.",
            "Use the exact project/run/report paths supplied by this rules revision and the immutable task contract; do not invent a parallel run tree.",
            "Do not place credentials, secrets, or private chain-of-thought in reports/logs.",
            "Do not edit orchestration control authority: state.json, worker-rules revisions/manifests, task-contract revisions, launch prompts/reservations, attempt/terminal events, checkpoints, or prior FINAL evidence. Write only the current assigned report/evidence, explicitly assigned log/handover/progress artifacts, and project paths allowed by the role/task contract.",
            "Do not leave a background/daemon/watcher process that can mutate project source, generated deliverables, or terminal evidence after FINAL. Stop task-owned writers before FINAL unless the contract explicitly transfers ownership to managed infrastructure.",
        ]
        rules.extend(args.rule)

        generated = datetime.now(timezone.utc).isoformat()
        final_protocol = protocol_dir
        text = [
            "# DeepSeek and Destroy Worker Rules",
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
            text.append("- NONE RECORDED — the orchestrator must not omit applicable project authority at intake.")
        text += [
            "",
            "## Run-local worker protocol",
            f"- Core: `{final_protocol / 'CORE.md'}`",
            f"- Role contracts: `{final_protocol / 'ROLES.md'}`",
            f"- Build roles: `{final_protocol / 'BUILD.md'}`",
            f"- Review/evidence roles: `{final_protocol / 'REVIEW.md'}`",
            f"- Evidence Clerk: `{final_protocol / 'EVIDENCE.md'}`",
            f"- Proof patterns: `{final_protocol / 'PROOF-PATTERNS.md'}`",
            "",
            "Protocol snapshot hashes:",
            *manifest_lines,
            "",
            "## Stable execution rules for this run",
            *[f"- {rule}" for rule in rules],
            "",
            "## Evidence / finality",
            "- A DSD mechanical fact is trusted only when the current immutable task contract/state explicitly references the exact artifact/attempt identity. A stale baseline or helper file from another contract is not a given fact.",
            "- Semantic claims from handovers/reports/orchestrators are claims, not authority.",
            "- Create the assigned report early. It is not terminal until `DSD_REPORT_STATUS: FINAL` is present in the Decision Packet.",
            "- After FINAL, the report/evidence is immutable. Later changes use a new numbered attempt/report.",
            "- Final stdout is at most three short lines: FINAL status, report path, optional one-line result.",
            "",
            "## Decision boundary",
            "- Resolve ordinary implementation ambiguity from the plan/project authority and canonical architecture; do not ask the orchestrator to pick from routine scope options.",
            "- Return DECISION_REQUIRED/BLOCKED only for a real authority/access/ownership boundary described by the role protocol.",
            "",
        ]
        tmp_output = tmp_root / "WORKER_RULES.md"
        tmp_output.write_text("\n".join(text), encoding="utf-8")
        payload = manifest_payload(args.revision, tmp_output, tmp_protocol)
        payload["path"] = str(output)
        payload["protocol_dir"] = str(protocol_dir)
        tmp_manifest = tmp_root / "MANIFEST.json"
        tmp_manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp_root.rename(revision_root)
    except Exception:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)
        raise

    try:
        emit(args.revision, output, protocol_dir, manifest_path)
    except ValueError as exc:
        print(f"ERROR: created worker-rules revision failed verification: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
