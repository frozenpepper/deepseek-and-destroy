#!/usr/bin/env python3
"""Launch one external OpenCode DSD worker and emit durable attempt/terminal events.

Normal DSD workers are external `opencode run` processes. This wrapper centralizes
transport boilerplate and reserves each attempt atomically so duplicate launches
cannot race on one report/event path. It may run in the foreground or detach one
monitor process and return immediately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _rules_snapshot import sha256_file, verify_snapshot

ROLES = {
    "implementer", "fixer", "reviewer", "verification", "discovery",
    "phase-surveyor", "recovery", "phase-auditor", "evidence-clerk",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parse_sessions(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        for key in ("sessions", "items", "data"):
            if isinstance(value.get(key), list):
                return [x for x in value[key] if isinstance(x, dict)]
    return []


def lookup_session_id(env: dict[str, str], title: str) -> tuple[str | None, str | None]:
    try:
        cp = subprocess.run(
            ["opencode", "session", "list", "--format", "json", "--max-count", "50"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            timeout=30, check=False,
        )
    except Exception as exc:
        return None, f"session lookup failed: {exc}"
    if cp.returncode != 0:
        return None, f"session list exit {cp.returncode}: {cp.stderr.strip()[:500]}"
    try:
        data = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        return None, f"session list JSON parse failed: {exc}"
    exact = [s for s in parse_sessions(data) if str(s.get("title", "")) == title]
    if len(exact) == 1:
        ident = exact[0].get("id") or exact[0].get("sessionID") or exact[0].get("session_id")
        return (str(ident), None) if ident else (None, "matched session has no id")
    if len(exact) > 1:
        return None, f"multiple sessions match title {title!r}"
    return None, f"no session matched title {title!r}"


def skeleton(report: Path, role: str, task_id: str, evidence_dir: Path) -> None:
    if report.exists():
        raise FileExistsError(f"attempt report already exists: {report}")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join([
            "## Decision Packet",
            "DSD_REPORT_STATUS: SKELETON",
            f"Role: {role}",
            f"Task: {task_id}",
            "Verdict: BLOCKED",
            "Goal/result: worker has not finalized this report",
            "Changed/read-only: UNKNOWN",
            "Verification: UNKNOWN",
            "Proof: UNKNOWN",
            "Scope/preservation: UNKNOWN",
            "Task-relevant defects: UNKNOWN",
            "Major log: NONE",
            "Clerk checks: REQUIRED REPORT-SKELETON",
            f"Evidence: {evidence_dir}",
            "FAST-PATH ELIGIBLE: NO — report is still a launcher skeleton",
            "",
        ]), encoding="utf-8",
    )


def resolve_preflight(args: argparse.Namespace) -> tuple[dict[str, Path] | None, str | None]:
    raw_paths = {
        "project_root": args.project_root,
        "run_root": args.run_root,
        "prompt": args.prompt_file,
        "task_contract": args.task_contract,
        "worker_rules": args.worker_rules,
        "scope_baseline": args.scope_baseline,
        "report": args.report,
        "event_dir": args.event_dir,
        "log": args.log,
        "db": args.db,
    }
    for label, path in raw_paths.items():
        if not path.is_absolute():
            return None, f"{label} path must be absolute: {path}"
    paths = {label: path.resolve() for label, path in raw_paths.items()}
    project_root = paths["project_root"]
    run_root = paths["run_root"]
    if not project_root.is_dir():
        return None, f"project root missing/not directory: {project_root}"
    if not run_root.is_dir():
        return None, f"run root missing/not directory: {run_root}"
    try:
        run_root.relative_to(project_root / "DeepSeekAndDestroy")
    except ValueError:
        return None, f"run root must live under {project_root / 'DeepSeekAndDestroy'}: {run_root}"
    if not paths["prompt"].is_file():
        return None, f"prompt file missing: {paths['prompt']}"
    if not paths["task_contract"].is_file():
        return None, f"task contract missing: {paths['task_contract']}"
    if not paths["worker_rules"].is_file():
        return None, f"worker rules missing: {paths['worker_rules']}"
    if paths["worker_rules"].name != "WORKER_RULES.md":
        return None, f"worker rules path must name WORKER_RULES.md: {paths['worker_rules']}"
    try:
        paths["worker_rules"].relative_to(run_root / "worker-rules")
    except ValueError:
        return None, f"worker rules must live under {run_root / 'worker-rules'}: {paths['worker_rules']}"
    try:
        snapshot = verify_snapshot(paths["worker_rules"])
    except ValueError as exc:
        return None, f"invalid immutable worker-rules snapshot: {exc}"
    paths["worker_rules_manifest"] = Path(snapshot["manifest"]).resolve()
    if not paths["scope_baseline"].is_file():
        return None, f"scope baseline missing: {paths['scope_baseline']}"
    for label in ("prompt", "task_contract", "worker_rules", "scope_baseline", "report", "event_dir", "log"):
        try:
            paths[label].relative_to(run_root)
        except ValueError:
            return None, f"{label} path is outside run root: {paths[label]}"
    db = paths["db"]
    for forbidden_label, forbidden_root in (("project", project_root), ("run", run_root)):
        try:
            db.relative_to(forbidden_root)
        except ValueError:
            continue
        return None, f"OPENCODE DB must be outside the {forbidden_label} tree: {db}"
    if args.attempt < 1:
        return None, "attempt must be >= 1"
    return paths, None


def reserve_attempt(args: argparse.Namespace, paths: dict[str, Path]) -> tuple[str | None, str | None]:
    event_dir = paths["event_dir"]
    report = paths["report"]
    log = paths["log"]
    if report.exists():
        return None, f"immutable attempt report path already exists: {report}; use a new numbered attempt/report"
    if log.exists():
        return None, f"immutable attempt log path already exists: {log}; use a new numbered attempt/log"
    event_dir.mkdir(parents=True, exist_ok=True)
    for terminal_artifact in (event_dir / "attempt.json", event_dir / "terminal.json"):
        if terminal_artifact.exists():
            return None, f"attempt event path already contains {terminal_artifact.name}; duplicate/reused attempt is forbidden"
    reserved_at = now()
    reservation = event_dir / "launch-reservation.json"
    try:
        fd = os.open(reservation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        payload = json.dumps({
            "format": "dsd-worker-launch-reservation-v1",
            "task_id": args.task_id,
            "role": args.role,
            "attempt": args.attempt,
            "report": str(report),
            "log": str(log),
            "prompt_file": str(paths["prompt"]),
            "prompt_sha256": sha256_file(paths["prompt"]),
            "task_contract": str(paths["task_contract"]),
            "task_contract_sha256": sha256_file(paths["task_contract"]),
            "worker_rules": str(paths["worker_rules"]),
            "worker_rules_sha256": sha256_file(paths["worker_rules"]),
            "worker_rules_manifest": str(paths["worker_rules_manifest"]),
            "worker_rules_manifest_sha256": sha256_file(paths["worker_rules_manifest"]),
            "scope_baseline": str(paths["scope_baseline"]),
            "scope_baseline_sha256": sha256_file(paths["scope_baseline"]),
            "reserved_at": reserved_at,
            "reserved_by_pid": os.getpid(),
        }, indent=2, sort_keys=True) + "\n"
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
    except FileExistsError:
        return None, f"attempt launch reservation already exists: {reservation}; duplicate/reused attempt is forbidden"
    except Exception as exc:
        try:
            reservation.unlink(missing_ok=True)
        except Exception:
            pass
        return None, f"cannot persist attempt reservation: {exc}"
    return reserved_at, None


def terminal_error(args: argparse.Namespace, paths: dict[str, Path], message: str, code: int = 2, *, started_at: str | None = None) -> int:
    atomic_json(paths["event_dir"] / "terminal.json", {
        "format": "dsd-worker-terminal-v2", "status": "transport-error",
        "task_id": args.task_id, "role": args.role, "attempt": args.attempt,
        "error": message, "exit_code": code, "ended_at": now(),
        "started_at": started_at,
        "report": str(paths["report"]), "log": str(paths["log"]),
        "prompt_file": str(paths["prompt"]),
        "prompt_sha256": sha256_file(paths["prompt"]) if paths["prompt"].is_file() else None,
        "task_contract": str(paths["task_contract"]),
        "task_contract_sha256": sha256_file(paths["task_contract"]) if paths["task_contract"].is_file() else None,
        "worker_rules": str(paths["worker_rules"]),
        "worker_rules_sha256": sha256_file(paths["worker_rules"]) if paths["worker_rules"].is_file() else None,
        "worker_rules_manifest": str(paths.get("worker_rules_manifest")) if paths.get("worker_rules_manifest") else None,
        "worker_rules_manifest_sha256": sha256_file(paths["worker_rules_manifest"]) if paths.get("worker_rules_manifest") and paths["worker_rules_manifest"].is_file() else None,
        "scope_baseline": str(paths["scope_baseline"]),
        "scope_baseline_sha256": sha256_file(paths["scope_baseline"]) if paths["scope_baseline"].is_file() else None,
    })
    return code


def child_run(args: argparse.Namespace, paths: dict[str, Path], reserved_at: str) -> int:
    project_root = paths["project_root"]
    prompt_file = paths["prompt"]
    report = paths["report"]
    event_dir = paths["event_dir"]
    log = paths["log"]
    db = paths["db"]

    if not (event_dir / "launch-reservation.json").is_file():
        return terminal_error(args, paths, "missing launch reservation", started_at=reserved_at)
    if not shutil.which("opencode"):
        return terminal_error(args, paths, "opencode executable not found", 127, started_at=reserved_at)

    log.parent.mkdir(parents=True, exist_ok=True)
    db.parent.mkdir(parents=True, exist_ok=True)
    try:
        skeleton(report, args.role, args.task_id, event_dir)
    except Exception as exc:
        return terminal_error(args, paths, f"cannot create report skeleton: {exc}", started_at=reserved_at)

    env = os.environ.copy()
    env["OPENCODE_DB"] = str(db)
    title = args.title or f"dsd:{args.task_id}:{args.role}:{args.attempt}"
    prompt = prompt_file.read_text(encoding="utf-8")
    cmd = ["opencode", "run", "--model", args.model]
    if args.auto_flag:
        cmd.append(args.auto_flag)
    cmd += ["--title", title, "--dir", str(project_root)]
    if args.resume_session:
        cmd += ["--session", args.resume_session]
    cmd.append(prompt)

    started = now()
    out = None
    try:
        out = log.open("xb", buffering=0)
        proc = subprocess.Popen(cmd, cwd=project_root, env=env, stdout=out, stderr=subprocess.STDOUT)
    except Exception as exc:
        if out:
            out.close()
        return terminal_error(args, paths, f"failed to launch opencode: {exc}", started_at=started)

    with out:
        attempt_data = {
            "format": "dsd-worker-attempt-v2",
            "task_id": args.task_id, "role": args.role, "attempt": args.attempt,
            "title": title, "model": args.model, "project_root": str(project_root),
            "db": str(db), "prompt_file": str(prompt_file),
            "prompt_sha256": sha256_file(prompt_file),
            "task_contract": str(paths["task_contract"]),
            "task_contract_sha256": sha256_file(paths["task_contract"]),
            "worker_rules": str(paths["worker_rules"]),
            "worker_rules_sha256": sha256_file(paths["worker_rules"]),
            "worker_rules_manifest": str(paths["worker_rules_manifest"]),
            "worker_rules_manifest_sha256": sha256_file(paths["worker_rules_manifest"]),
            "scope_baseline": str(paths["scope_baseline"]),
            "scope_baseline_sha256": sha256_file(paths["scope_baseline"]),
            "report": str(report),
            "log": str(log), "worker_pid": proc.pid, "launcher_pid": os.getpid(),
            "reserved_at": reserved_at, "started_at": started,
            "resume_session": args.resume_session,
        }
        atomic_json(event_dir / "attempt.json", attempt_data)
        rc = proc.wait()

    if args.resume_session:
        session_id, session_error = args.resume_session, None
    else:
        session_id, session_error = lookup_session_id(env, title)
    terminal = {
        "format": "dsd-worker-terminal-v2",
        "status": "completed" if rc == 0 else "process-error",
        "task_id": args.task_id, "role": args.role, "attempt": args.attempt,
        "title": title, "model": args.model, "exit_code": rc,
        "worker_pid": attempt_data["worker_pid"], "launcher_pid": os.getpid(),
        "session_id": session_id, "session_lookup_error": session_error,
        "report": str(report), "prompt_file": attempt_data["prompt_file"],
        "prompt_sha256": attempt_data["prompt_sha256"],
        "task_contract": attempt_data["task_contract"],
        "task_contract_sha256": attempt_data["task_contract_sha256"],
        "worker_rules": attempt_data["worker_rules"],
        "worker_rules_sha256": attempt_data["worker_rules_sha256"],
        "worker_rules_manifest": attempt_data["worker_rules_manifest"],
        "worker_rules_manifest_sha256": attempt_data["worker_rules_manifest_sha256"],
        "scope_baseline": attempt_data["scope_baseline"],
        "scope_baseline_sha256": attempt_data["scope_baseline_sha256"],
        "log": str(log), "reserved_at": reserved_at, "started_at": started, "ended_at": now(),
    }
    atomic_json(event_dir / "terminal.json", terminal)
    return rc


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--role", choices=sorted(ROLES), required=True)
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--prompt-file", type=Path, required=True)
    ap.add_argument("--task-contract", type=Path, required=True, help="exact immutable task-contract revision referenced by the prompt")
    ap.add_argument("--worker-rules", type=Path, required=True, help="exact immutable WORKER_RULES.md revision referenced by the prompt")
    ap.add_argument("--scope-baseline", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--event-dir", type=Path, required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--model", default="opencode-go/deepseek-v4-flash")
    ap.add_argument("--title")
    ap.add_argument("--resume-session")
    ap.add_argument("--auto-flag", default="--auto", help="OpenCode permission flag; pass empty string to omit")
    ap.add_argument("--detach", action="store_true", help="spawn the monitor in a detached process and return")
    ap.add_argument("--_child", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--_reserved-at", help=argparse.SUPPRESS)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    paths, preflight_error = resolve_preflight(args)
    if preflight_error or paths is None:
        print(f"ERROR: {preflight_error}", file=sys.stderr)
        return 2

    if args._child:
        if not args._reserved_at:
            print("ERROR: internal child launch lacks reservation", file=sys.stderr)
            return 2
        return child_run(args, paths, args._reserved_at)

    reserved_at, reservation_error = reserve_attempt(args, paths)
    if reservation_error or reserved_at is None:
        print(f"ERROR: {reservation_error}", file=sys.stderr)
        return 2

    if not args.detach:
        return child_run(args, paths, reserved_at)

    child_argv = [sys.executable, str(Path(__file__).resolve())]
    for key, value in vars(args).items():
        if key in {"detach", "_child", "_reserved_at"}:
            continue
        opt = "--" + key.replace("_", "-")
        if value is None:
            continue
        if isinstance(value, bool):
            if value:
                child_argv.append(opt)
        elif key == "auto_flag":
            child_argv.append(f"{opt}={value}")
        else:
            child_argv += [opt, str(value)]
    child_argv += ["--_child", "--_reserved-at", reserved_at]

    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(child_argv, **kwargs)
    except Exception as exc:
        return terminal_error(args, paths, f"failed to spawn detached worker monitor: {exc}", started_at=reserved_at)
    print(json.dumps({
        "status": "launched", "monitor_pid": proc.pid,
        "event_dir": str(paths["event_dir"]),
        "terminal_event": str(paths["event_dir"] / "terminal.json"),
        "prompt_file": str(paths["prompt"]),
        "prompt_sha256": sha256_file(paths["prompt"]),
        "task_contract": str(paths["task_contract"]),
        "task_contract_sha256": sha256_file(paths["task_contract"]),
        "worker_rules": str(paths["worker_rules"]),
        "worker_rules_sha256": sha256_file(paths["worker_rules"]),
        "worker_rules_manifest": str(paths["worker_rules_manifest"]),
        "worker_rules_manifest_sha256": sha256_file(paths["worker_rules_manifest"]),
        "scope_baseline": str(paths["scope_baseline"]),
        "scope_baseline_sha256": sha256_file(paths["scope_baseline"]),
        "reserved_at": reserved_at,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
