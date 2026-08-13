#!/usr/bin/env python3
"""Create and rehydrate DeepSeek and Destroy context checkpoints.

This script keeps mechanical continuity outside the model context. It never
summarizes project code or invents decisions; it snapshots durable run state and
emits a compact resume instruction.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

TERMINAL = {"completed", "human-blocked", "paused-by-user", "abandoned"}


class NoActiveRun(RuntimeError):
    pass


class AmbiguousRun(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_root(start: Path) -> Path:
    try:
        value = subprocess.check_output(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if value:
            return Path(value).resolve()
    except Exception:
        pass
    return start.resolve()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def resolve_path(value: Any, base: Path) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def active_state_paths(project_root: Path) -> list[Path]:
    root = project_root / "DeepSeekAndDestroy" / "plans"
    if not root.is_dir():
        return []
    candidates: list[Path] = []
    for path in root.glob("*/runs/*/state.json"):
        try:
            state = read_json(path)
        except Exception:
            continue
        if str(state.get("execution_status", "")).lower() not in TERMINAL:
            candidates.append(path.resolve())
    return sorted(candidates)


def choose_run(project_root: Path, explicit: str | None, session_id: str | None, *, prefer_checkpoint: bool = False) -> tuple[Path, dict[str, Any]]:
    requested = explicit or os.environ.get("DSD_RUN_ROOT")
    if requested:
        run_root = Path(requested)
        if not run_root.is_absolute():
            run_root = (project_root / run_root).resolve()
        state_path = run_root / "state.json"
        if not state_path.is_file():
            raise RuntimeError(f"No state.json at explicit run root: {run_root}")
        return run_root, read_json(state_path)

    paths = active_state_paths(project_root)
    if session_id:
        matching: list[Path] = []
        for path in paths:
            try:
                state = read_json(path)
            except Exception:
                continue
            known = {
                str(state.get("orchestrator_session_id", "")),
                str((state.get("orchestrator") or {}).get("session_id", "")),
            }
            if session_id in known:
                matching.append(path)
        if len(matching) == 1:
            return matching[0].parent, read_json(matching[0])
    if prefer_checkpoint and len(paths) > 1:
        checkpoint_candidates: list[Path] = []
        for path in paths:
            try:
                state = read_json(path)
            except Exception:
                continue
            checkpoint_status = str((state.get("context_checkpoint") or {}).get("status", "")).lower()
            if checkpoint_status in {"prepared", "compacting", "rehydration-required"}:
                checkpoint_candidates.append(path)
        if len(checkpoint_candidates) == 1:
            return checkpoint_candidates[0].parent, read_json(checkpoint_candidates[0])
    if len(paths) == 1:
        return paths[0].parent, read_json(paths[0])
    if not paths:
        raise NoActiveRun("No active DeepSeek and Destroy run found")
    raise AmbiguousRun(
        "Multiple active runs found; set DSD_RUN_ROOT or pass --run-root. "
        + ", ".join(str(path.parent) for path in paths)
    )


def latest_sequence(run_root: Path) -> int:
    compactions = run_root / "compactions"
    if not compactions.is_dir():
        return 0
    values = []
    for child in compactions.iterdir():
        if child.is_dir() and child.name.isdigit():
            values.append(int(child.name))
    return max(values, default=0)


def current_task_summary(state: dict[str, Any]) -> dict[str, Any]:
    active: list[dict[str, Any]] = []
    for phase_id, phase in (state.get("phases") or {}).items():
        for task_id, task in (phase.get("tasks") or {}).items():
            if not isinstance(task, dict):
                continue
            status = str(task.get("status", ""))
            if status not in {"passed", "completed", "accepted"}:
                active.append(
                    {
                        "phase": phase_id,
                        "task": task_id,
                        "status": status,
                        "task_type": task.get("task_type"),
                        "report_path": task.get("report_path"),
                        "current_attempt": task.get("current_attempt"),
                    }
                )
    return {"active_units": active[:10], "active_unit_count": len(active)}


def copy_if_exists(source: Path | None, destination: Path) -> None:
    if source and source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def checkpoint_paths(run_root: Path, sequence: int) -> tuple[Path, Path, Path]:
    checkpoint_dir = run_root / "compactions" / f"{sequence:04d}"
    return checkpoint_dir, checkpoint_dir / "CHECKPOINT.md", checkpoint_dir / "resume-manifest.json"


def prepare(
    project_root: Path,
    run_root_arg: str | None,
    harness: str,
    reason: str,
    session_id: str | None,
    context_percent: float | None,
) -> dict[str, Any]:
    run_root, state = choose_run(project_root, run_root_arg, session_id)
    existing_checkpoint = state.get("context_checkpoint") or {}
    existing_status = str(existing_checkpoint.get("status", "")).lower()
    existing_path = resolve_path(existing_checkpoint.get("checkpoint_path"), project_root)
    existing_manifest = resolve_path(existing_checkpoint.get("manifest_path"), project_root)
    if existing_status in {"prepared", "compacting"} and existing_path and existing_path.is_file() and existing_manifest and existing_manifest.is_file():
        return {
            "run_root": str(run_root),
            "checkpoint": str(existing_path),
            "manifest": str(existing_manifest),
            "sequence": int(existing_checkpoint.get("sequence") or latest_sequence(run_root)),
            "reused": True,
        }
    sequence = latest_sequence(run_root) + 1
    checkpoint_dir, checkpoint_md, manifest_path = checkpoint_paths(run_root, sequence)
    checkpoint_dir.mkdir(parents=True, exist_ok=False)

    state_path = run_root / "state.json"
    handover = resolve_path(state.get("handover"), project_root) or (run_root / "HANDOVER.md")
    plan_reference = resolve_path(state.get("plan_reference"), project_root) or (run_root / "plan/plan-reference.md")
    authority_index = resolve_path(state.get("authority_index"), project_root) or (run_root / "authority-index.json")
    effective_config = resolve_path(state.get("effective_config"), project_root) or (run_root / "effective-configuration.md")

    copy_if_exists(state_path, checkpoint_dir / "state.snapshot.json")
    copy_if_exists(handover, checkpoint_dir / "HANDOVER.snapshot.md")
    copy_if_exists(plan_reference, checkpoint_dir / "plan-reference.snapshot.md")
    copy_if_exists(authority_index, checkpoint_dir / "authority-index.snapshot.json")

    summary = current_task_summary(state)
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "sequence": sequence,
        "created_at": utc_now(),
        "reason": reason,
        "context_percent": context_percent,
        "harness": harness,
        "orchestrator_session_id": session_id,
        "project_root": str(project_root),
        "run_root": str(run_root),
        "run_id": state.get("run_id"),
        "plan_id": state.get("plan_id"),
        "plan_source_sha256": state.get("plan_source_sha256"),
        "next_action": state.get("next_action"),
        "execution_status": state.get("execution_status"),
        "state_sha256_before_checkpoint": sha256(state_path),
        "handover_sha256": sha256(handover),
        "plan_reference_sha256": sha256(plan_reference),
        "authority_index_sha256": sha256(authority_index),
        "effective_config_sha256": sha256(effective_config),
        "authority_paths": {
            "plan_reference": str(plan_reference),
            "authority_index": str(authority_index),
            "effective_config": str(effective_config),
        },
        "active_summary": summary,
    }
    write_json(manifest_path, manifest)

    checkpoint_text = f"""# DeepSeek and Destroy Context Checkpoint {sequence:04d}

## Identity

- Run id: `{state.get('run_id')}`
- Plan id: `{state.get('plan_id')}`
- Run root: `{run_root}`
- Harness: `{harness}`
- Reason: `{reason}`
- Context percentage when known: `{context_percent if context_percent is not None else 'unknown'}`
- Created: `{manifest['created_at']}`

## Continuity authority

Read live `{run_root / 'state.json'}` first. It is authoritative for current execution. `{manifest_path}` verifies checkpoint identity; HANDOVER/plan/evidence are cold and should be opened only when the live `next_action` actually needs their context.

Immutable snapshots captured with this checkpoint:

- `{checkpoint_dir / 'state.snapshot.json'}`
- `{checkpoint_dir / 'HANDOVER.snapshot.md'}`
- `{checkpoint_dir / 'plan-reference.snapshot.md'}`
- `{checkpoint_dir / 'authority-index.snapshot.json'}`

## Current state

- Execution status: `{state.get('execution_status')}`
- Exact next action: `{state.get('next_action')}`
- Active unit count: `{summary['active_unit_count']}`

## Resume contract

The compacted conversation is not authoritative. Reload the skill, read live
`state.json` first, then run the mechanical continuity verifier before revalidating
any live worker:

```bash
python3 "{project_root / 'DeepSeekAndDestroy/tools/context_checkpoint.py'}" verify-resume \\
  --run-root "{run_root}" --sequence {sequence} --harness {harness}
```

After continuity verification, execute the live `state.json` `next_action`
immediately. Do not stop after announcing that rehydration succeeded.
"""
    checkpoint_md.write_text(checkpoint_text, encoding="utf-8")
    (run_root / "compactions" / "LATEST").write_text(f"{sequence:04d}\n", encoding="utf-8")

    checkpoint_state = {
        "sequence": sequence,
        "status": "prepared",
        "reason": reason,
        "context_percent": context_percent,
        "checkpoint_path": str(checkpoint_md),
        "manifest_path": str(manifest_path),
        "created_at": manifest["created_at"],
        "harness": harness,
        "orchestrator_session_id": session_id,
        "preserved_next_action": state.get("next_action"),
    }
    state["context_checkpoint"] = checkpoint_state
    write_json(state_path, state)
    return {"run_root": str(run_root), "checkpoint": str(checkpoint_md), "manifest": str(manifest_path), "sequence": sequence}


def latest_checkpoint(run_root: Path) -> tuple[int, Path, Path]:
    latest_file = run_root / "compactions" / "LATEST"
    if latest_file.is_file():
        sequence = int(latest_file.read_text(encoding="utf-8").strip())
    else:
        sequence = latest_sequence(run_root)
    if sequence <= 0:
        raise RuntimeError(f"No checkpoint exists under {run_root}")
    checkpoint_dir, checkpoint_md, manifest_path = checkpoint_paths(run_root, sequence)
    return sequence, checkpoint_md, manifest_path


def set_checkpoint_status(run_root: Path, status: str, **extra: Any) -> None:
    state_path = run_root / "state.json"
    state = read_json(state_path)
    checkpoint = state.setdefault("context_checkpoint", {})
    checkpoint["status"] = status
    checkpoint.update(extra)
    write_json(state_path, state)


def rehydrate_text(project_root: Path, run_root_arg: str | None, session_id: str | None, *, mark_required: bool = True) -> str:
    run_root, state = choose_run(project_root, run_root_arg, session_id, prefer_checkpoint=True)
    sequence, checkpoint_md, manifest_path = latest_checkpoint(run_root)
    checkpoint = state.get("context_checkpoint") or {}
    if mark_required:
        set_checkpoint_status(run_root, "rehydration-required", rehydration_requested_at=utc_now())
    return f"""DeepSeek and Destroy continuity is active.

Before any project reasoning:
1. Reload the DeepSeek and Destroy skill.
2. Read live `{run_root / 'state.json'}` first.
3. Run `python3 "{project_root / 'DeepSeekAndDestroy/tools/context_checkpoint.py'}" --run-root "{run_root}" verify-resume --sequence {sequence}`.
4. Revalidate any worker recorded as live when needed.
5. Execute a mechanical live `next_action` immediately. If it requires parent judgment, open only the exact decision/evidence/authority it names; read HANDOVER only for genuinely missing non-state continuity.

Do not reconstruct the run from git history, session notes, old reports/contracts, or broad project architecture. The native compacted summary is advisory; live state plus immutable evidence are authority.
"""


def verify_resume(project_root: Path, run_root_arg: str | None, sequence_arg: int | None, harness: str) -> dict[str, Any]:
    run_root, state = choose_run(project_root, run_root_arg, None)
    sequence, checkpoint_md, manifest_path = latest_checkpoint(run_root)
    if sequence_arg is not None and sequence_arg != sequence:
        raise RuntimeError(f"Requested checkpoint {sequence_arg}, latest is {sequence}")
    manifest = read_json(manifest_path)
    if state.get("run_id") != manifest.get("run_id"):
        raise RuntimeError("Run identity differs from checkpoint manifest")
    if state.get("plan_id") != manifest.get("plan_id"):
        raise RuntimeError("Plan identity differs from checkpoint manifest")

    drift: list[str] = []
    recorded_plan_source = manifest.get("plan_source_sha256")
    if recorded_plan_source and state.get("plan_source_sha256") != recorded_plan_source:
        drift.append("plan source identity/hash recorded in state changed")

    authority_paths = manifest.get("authority_paths") if isinstance(manifest.get("authority_paths"), dict) else {}
    defaults = {
        "plan_reference": run_root / "plan/plan-reference.md",
        "authority_index": run_root / "authority-index.json",
        "effective_config": run_root / "effective-configuration.md",
    }
    state_keys = {
        "plan_reference": "plan_reference",
        "authority_index": "authority_index",
        "effective_config": "effective_config",
    }
    hash_keys = {
        "plan_reference": "plan_reference_sha256",
        "authority_index": "authority_index_sha256",
        "effective_config": "effective_config_sha256",
    }
    checked: dict[str, dict[str, Any]] = {}
    for name in ("plan_reference", "authority_index", "effective_config"):
        live = resolve_path(state.get(state_keys[name]), project_root) or defaults[name]
        recorded_path = authority_paths.get(name)
        if recorded_path and Path(recorded_path).resolve() != live.resolve():
            drift.append(f"{name} path changed: checkpoint={recorded_path} live={live}")
        expected = manifest.get(hash_keys[name])
        actual = sha256(live)
        checked[name] = {"path": str(live), "expected_sha256": expected, "actual_sha256": actual}
        if expected != actual:
            drift.append(f"{name} content changed or is missing")

    if drift:
        checkpoint = state.setdefault("context_checkpoint", {})
        checkpoint.update({
            "sequence": sequence,
            "status": "rehydration-required",
            "continuity_verified": False,
            "continuity_error_at": utc_now(),
            "continuity_drift": drift,
            "checkpoint_path": str(checkpoint_md),
            "manifest_path": str(manifest_path),
        })
        write_json(run_root / "state.json", state)
        raise RuntimeError("Governing authority drift after checkpoint: " + "; ".join(drift))

    checkpoint = state.setdefault("context_checkpoint", {})
    checkpoint.update({
        "sequence": sequence,
        "status": "resumed",
        "resumed_at": utc_now(),
        "continuity_verified": True,
        "resumed_harness": harness,
        "checkpoint_path": str(checkpoint_md),
        "manifest_path": str(manifest_path),
        "authority_verified": checked,
    })
    write_json(run_root / "state.json", state)
    return {
        "run_root": str(run_root),
        "sequence": sequence,
        "status": "resumed",
        "continuity_verified": True,
        "authority_verified": checked,
        "next_action": state.get("next_action"),
        "note": "Revalidate any active worker lifecycle separately before acting on it.",
    }


def hook_response(harness: str, event: str, text: str | None = None, block: str | None = None) -> None:
    if block:
        if harness == "claude-code":
            print(json.dumps({"decision": "block", "reason": block}))
        else:
            print(json.dumps({"continue": False, "stopReason": block, "systemMessage": block}))
        return
    if event == "sessionstart" and text:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": text,
                    }
                }
            )
        )
    else:
        print(json.dumps({"continue": True, "systemMessage": text or "DSD checkpoint hook completed"}))


def hook(args: argparse.Namespace) -> int:
    raw = sys.stdin.read()
    payload: dict[str, Any] = {}
    if raw.strip():
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
    project_root = git_root(Path(payload.get("cwd") or args.project_root or os.getcwd()))
    session_id = payload.get("session_id") or payload.get("sessionId")
    try:
        if args.event == "precompact":
            result = prepare(project_root, args.run_root, args.harness, f"{args.harness}-precompact", session_id, None)
            set_checkpoint_status(Path(result["run_root"]), "compacting", compacting_at=utc_now())
            hook_response(args.harness, args.event, f"DSD checkpoint prepared: {result['checkpoint']}")
        elif args.event == "postcompact":
            run_root, _ = choose_run(project_root, args.run_root, session_id)
            sequence, _, manifest_path = latest_checkpoint(run_root)
            summary = payload.get("compact_summary")
            if isinstance(summary, str):
                (manifest_path.parent / "native-compact-summary.md").write_text(summary, encoding="utf-8")
            set_checkpoint_status(run_root, "rehydration-required", postcompact_at=utc_now(), sequence=sequence)
            hook_response(args.harness, args.event, "DSD compaction finished; rehydration is required before project work")
        elif args.event == "sessionstart":
            source = str(payload.get("source", ""))
            if source and source not in {"compact", "resume"}:
                hook_response(args.harness, args.event, "")
            else:
                text = rehydrate_text(project_root, args.run_root, session_id)
                hook_response(args.harness, args.event, text)
        else:
            raise RuntimeError(f"Unsupported hook event: {args.event}")
    except NoActiveRun:
        # Project-local hooks may exist when no DSD run is active. They must be a no-op.
        hook_response(args.harness, args.event, "")
    except AmbiguousRun as exc:
        message = f"DeepSeek and Destroy run selection is ambiguous: {exc}"
        if args.event == "precompact":
            hook_response(args.harness, args.event, block=message)
        else:
            hook_response(args.harness, args.event, message)
    except Exception as exc:
        message = f"DeepSeek and Destroy checkpoint hook failed: {exc}"
        if args.event == "precompact":
            hook_response(args.harness, args.event, block=message)
            return 0
        hook_response(args.harness, args.event, message)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", help="Project root; defaults to git root/cwd")
    parser.add_argument("--run-root", help="Exact DSD run root; otherwise DSD_RUN_ROOT or unique active run")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--harness", default="generic")
    p_prepare.add_argument("--reason", default="context-threshold")
    p_prepare.add_argument("--session-id")
    p_prepare.add_argument("--context-percent", type=float)

    p_rehydrate = sub.add_parser("rehydrate")
    p_rehydrate.add_argument("--session-id")

    p_instruction = sub.add_parser("instruction")
    p_instruction.add_argument("--session-id")

    p_verify = sub.add_parser("verify-resume")
    p_verify.add_argument("--sequence", type=int)
    p_verify.add_argument("--harness", default="generic")

    p_hook = sub.add_parser("hook")
    p_hook.add_argument("--harness", required=True, choices=["codex", "claude-code"])
    p_hook.add_argument("--event", required=True, choices=["precompact", "postcompact", "sessionstart"])
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    project_root = git_root(Path(args.project_root or os.getcwd()))
    try:
        if args.command == "prepare":
            result = prepare(project_root, args.run_root, args.harness, args.reason, args.session_id, args.context_percent)
            print(json.dumps(result, indent=2))
        elif args.command == "rehydrate":
            print(rehydrate_text(project_root, args.run_root, args.session_id, mark_required=True))
        elif args.command == "instruction":
            print(rehydrate_text(project_root, args.run_root, args.session_id, mark_required=False))
        elif args.command == "verify-resume":
            print(json.dumps(verify_resume(project_root, args.run_root, args.sequence, args.harness), indent=2))
        elif args.command == "hook":
            return hook(args)
    except NoActiveRun as exc:
        print(f"NO_ACTIVE_RUN: {exc}", file=sys.stderr)
        return 4
    except AmbiguousRun as exc:
        print(f"AMBIGUOUS_RUN: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
