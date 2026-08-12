#!/usr/bin/env python3
"""Thin transaction wrapper for the normal DSD external-worker attempt lifecycle.

It derives mechanical paths/configuration from state.json, but never chooses a role,
changes task semantics, retries a worker, or decides acceptance.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from report_surface import extract as extract_surface
from _roles import ROLE_NAMES


def run(cmd: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=capture, check=False)


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 2


def load_state(path: Path) -> tuple[dict[str, Any], Path, Path]:
    if not path.is_absolute():
        raise ValueError("--state must be absolute")
    state_path = path.resolve()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("state.json must contain one object")
    project = Path(str(data.get("project_worktree", "")))
    if not project.is_absolute():
        raise ValueError("state project_worktree must be absolute")
    project = project.resolve()
    run_value = Path(str(data.get("run_root", "")))
    run_root = run_value.resolve() if run_value.is_absolute() else (project / run_value).resolve()
    if state_path.parent.resolve() != run_root:
        raise ValueError(f"--state must be the active run state.json ({run_root / 'state.json'})")
    return data, project, run_root


def resolve_state_path(value: Any, project: Path, run_root: Path) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path.resolve()
    # DSD state convention stores run paths project-relative.
    project_candidate = (project / path).resolve()
    if project_candidate.exists() or str(path).startswith("DeepSeekAndDestroy/"):
        return project_candidate
    return (run_root / path).resolve()


def task_ref(state: dict[str, Any], phase: str, task: str) -> dict[str, Any]:
    try:
        value = state["phases"][phase]["tasks"][task]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"state has no task {phase}/{task}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"state task {phase}/{task} is not an object")
    return value


def next_attempt(task_root: Path, role: str) -> int:
    attempts = task_root / "attempts"
    highest = 0
    if attempts.is_dir():
        pattern = re.compile(rf"^{re.escape(role)}-(\d+)$")
        for child in attempts.iterdir():
            match = pattern.match(child.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def free_numbered(path: Path) -> Path:
    if not path.exists():
        return path
    for n in range(2, 10000):
        candidate = path.with_name(f"{path.stem}-{n:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise ValueError(f"cannot allocate immutable sibling for {path}")


def launch(args: argparse.Namespace) -> int:
    state, project, run_root = load_state(args.state)
    task = task_ref(state, args.phase, args.task)
    contract_meta = task.get("current_contract") or {}
    contract_value = contract_meta.get("path")
    if not contract_value:
        raise ValueError(f"{args.phase}/{args.task} has no current_contract")
    contract = resolve_state_path(contract_value, project, run_root)
    if not contract.is_file():
        raise ValueError(f"current contract missing: {contract}")

    rules_meta = state.get("worker_rules") or {}
    worker_rules = resolve_state_path(rules_meta.get("path"), project, run_root)
    if not worker_rules.is_file():
        raise ValueError(f"worker rules missing: {worker_rules}")

    task_root = contract.parent.parent if contract.parent.name == "contracts" else contract.parent
    attempt_no = next_attempt(task_root, args.role)
    attempt_dir = task_root / "attempts" / f"{args.role}-{attempt_no}"
    prompt = attempt_dir / "prompt.txt"
    baseline = attempt_dir / "scope-baseline.json"
    report = attempt_dir / "report.md"
    log = attempt_dir / "worker.log"

    runtime = state.get("worker_runtime") or {}
    model = args.model or runtime.get("model") or "opencode-go/deepseek-v4-flash"
    opencode = runtime.get("opencode") or {}
    db_value = args.db or opencode.get("run_db")
    if not db_value:
        raise ValueError("worker DB not configured in state worker_runtime.opencode.run_db; pass --db")
    db = Path(str(db_value)).expanduser().resolve()
    try:
        db.relative_to(project)
    except ValueError:
        pass
    else:
        raise ValueError("worker DB must live outside the project tree")

    attempt_dir.mkdir(parents=True, exist_ok=False)
    scripts = Path(__file__).resolve().parent
    try:
        capture = run([
            sys.executable, str(scripts / "scope_snapshot.py"), "capture",
            "--root", str(project), "--output", str(baseline), "--git-worktree",
            "--exclude-prefix", "DeepSeekAndDestroy", "--task-contract", str(contract),
        ])
        if capture.returncode != 0:
            raise ValueError((capture.stderr or capture.stdout).strip() or "scope baseline capture failed")

        render_cmd = [
            sys.executable, str(scripts / "render_worker_prompt.py"),
            "--role", args.role, "--task-id", args.task, "--run-root", str(run_root),
            "--worker-rules", str(worker_rules), "--task", str(contract),
            "--report", str(report),
        ]
        for evidence in args.evidence:
            render_cmd += ["--evidence", str(evidence.resolve())]
        render_cmd += ["--output", str(prompt)]
        render = run(render_cmd)
        if render.returncode != 0:
            raise ValueError((render.stderr or render.stdout).strip() or "worker prompt render failed")
    except Exception:
        # No immutable reservation exists yet, so pre-launch helper failures should
        # not burn an attempt number or leave a misleading partial attempt tree.
        if not (attempt_dir / "launch-reservation.json").exists():
            shutil.rmtree(attempt_dir, ignore_errors=True)
        raise

    cmd = [
        sys.executable, str(scripts / "run_worker.py"),
        "--project-root", str(project), "--run-root", str(run_root),
        "--task-id", args.task, "--role", args.role, "--attempt", str(attempt_no),
        "--prompt-file", str(prompt), "--task-contract", str(contract),
        "--worker-rules", str(worker_rules), "--scope-baseline", str(baseline),
        "--report", str(report), "--event-dir", str(attempt_dir), "--log", str(log),
        "--db", str(db), "--model", str(model), "--detach",
    ]
    if args.resume_session:
        cmd += ["--resume-session", args.resume_session]
    launched = run(cmd)
    if launched.returncode != 0:
        raise ValueError((launched.stderr or launched.stdout).strip() or "worker launch failed")
    try:
        launched_data = json.loads(launched.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"run_worker returned unreadable launch result: {launched.stdout[:1000]}") from exc

    reservation = Path(launched_data["launch_reservation"]).resolve()
    bind = run([
        sys.executable, str(scripts / "dsd_state.py"), "--state", str(args.state.resolve()),
        "bind-attempt", "--phase", args.phase, "--task", args.task,
        "--reservation", str(reservation), "--role", args.role, "--attempt", str(attempt_no),
        "--monitor-pid", str(launched_data["monitor_pid"]), "--liveness", "confirmed",
        "--next-action", f"wait for {args.phase}/{args.task} {args.role}-{attempt_no} terminal event",
    ])
    if bind.returncode != 0:
        raise ValueError("worker launched but state bind failed; reconcile before further launches: " + (bind.stderr or bind.stdout).strip())

    print(json.dumps({
        "status": "launched", "phase": args.phase, "task": args.task, "role": args.role,
        "attempt": attempt_no, "attempt_dir": str(attempt_dir), "report": str(report),
        "terminal_event": launched_data["terminal_event"], "monitor_pid": launched_data["monitor_pid"],
    }, indent=2, sort_keys=True))
    return 0


def gate(args: argparse.Namespace) -> int:
    state, project, run_root = load_state(args.state)
    task = task_ref(state, args.phase, args.task)
    attempt = task.get("current_attempt") or {}
    if not attempt:
        raise ValueError(f"{args.phase}/{args.task} has no current_attempt")
    reservation_path = resolve_state_path(attempt.get("launch_reservation"), project, run_root)
    reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
    event_dir = reservation_path.parent
    terminal = event_dir / "terminal.json"
    if not terminal.is_file():
        raise ValueError(f"worker has no terminal event yet: {terminal}")

    report = Path(reservation["report"]).resolve()
    contract = Path(reservation["task_contract"]).resolve()
    baseline = Path(reservation["scope_baseline"]).resolve()
    log = Path(reservation["log"]).resolve()
    scope_out = free_numbered(event_dir / "scope-diff.json")
    gate_out = free_numbered(event_dir / "evidence-gate.json")
    scripts = Path(__file__).resolve().parent
    cp = run([
        sys.executable, str(scripts / "evidence_gate.py"),
        "--run-root", str(run_root), "--project-root", str(project),
        "--task", str(contract), "--report", str(report), "--terminal-event", str(terminal),
        "--log", str(log), "--role", str(reservation["role"]),
        "--scope-baseline", str(baseline), "--scope-output", str(scope_out),
        "--output", str(gate_out), "--json",
    ])
    if not gate_out.is_file():
        raise ValueError((cp.stderr or cp.stdout).strip() or "evidence gate produced no artifact")
    result = json.loads(gate_out.read_text(encoding="utf-8"))

    if result.get("report_recovery_required") and result.get("mechanical_ok"):
        next_action = f"recover/interpret exact-attempt evidence for {args.phase}/{args.task}"
    elif not result.get("mechanical_ok"):
        next_action = f"resolve mechanical failure/recovery for {args.phase}/{args.task}"
    else:
        next_action = f"interpret gated {reservation['role']} result for {args.phase}/{args.task}"
    marked = run([
        sys.executable, str(scripts / "dsd_state.py"), "--state", str(args.state.resolve()),
        "mark-attempt", "--phase", args.phase, "--task", args.task,
        "--status", "process-exited", "--evidence-gate", str(gate_out),
        "--next-action", next_action,
    ])
    if marked.returncode != 0:
        raise ValueError("evidence gate completed but state update failed: " + (marked.stderr or marked.stdout).strip())

    surface: list[str] = []
    if result.get("report_state") == "substantive" and report.is_file():
        try:
            surface = extract_surface(report, args.max_surface_lines)
        except (OSError, ValueError):
            surface = []

    print(json.dumps({
        "gate_exit": cp.returncode,
        "evidence_gate": str(gate_out),
        "mechanical_ok": result.get("mechanical_ok"),
        "report_recovery_required": result.get("report_recovery_required"),
        "report": str(report),
        "report_bytes": result.get("report_bytes"),
        "decision_surface": surface,
        "next": (
            "recover exact-attempt report; do not rerun technical work" if result.get("report_recovery_required") and result.get("mechanical_ok")
            else "resolve mechanical failure/recovery" if not result.get("mechanical_ok")
            else "parent interpret compact surface; use Evidence Clerk only if semantic mapping/compression is needed"
        ),
    }, indent=2, sort_keys=True))
    return cp.returncode


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    l = sub.add_parser("launch", help="capture baseline, render prompt, reserve/launch worker, bind state")
    l.add_argument("--state", type=Path, required=True)
    l.add_argument("--phase", required=True); l.add_argument("--task", required=True)
    l.add_argument("--role", choices=sorted(ROLE_NAMES), required=True)
    l.add_argument("--db", type=Path); l.add_argument("--model"); l.add_argument("--resume-session")
    l.add_argument("--evidence", type=Path, action="append", default=[], help="prior immutable run evidence needed by this worker")

    g = sub.add_parser("gate", help="gate the current attempt mechanically and show a bounded report surface")
    g.add_argument("--state", type=Path, required=True)
    g.add_argument("--phase", required=True); g.add_argument("--task", required=True)
    g.add_argument("--max-surface-lines", type=int, default=20)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        return launch(args) if args.command == "launch" else gate(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
