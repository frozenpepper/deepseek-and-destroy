#!/usr/bin/env python3
"""Prepare/launch/gate one DSD external OpenCode attempt from durable state.

The premium parent chooses task semantics and role. This helper derives the repetitive
attempt paths/configuration, captures the scope baseline, renders the tiny prompt,
launches the existing OpenCode wrapper, and binds state. It does not accept tasks or
make routing decisions.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from _roles import ROLE_NAMES




def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def project_root_from_run(run_root: Path, state: dict[str, Any]) -> Path:
    raw = state.get("project_worktree")
    if isinstance(raw, str) and raw.strip():
        path = Path(raw)
        if not path.is_absolute():
            path = (run_root / path).resolve()
        if path.is_dir():
            return path.resolve()
    for ancestor in [run_root, *run_root.parents]:
        if ancestor.name == "DeepSeekAndDestroy":
            return ancestor.parent.resolve()
    raise ValueError("cannot derive project root from run; state.project_worktree is missing/invalid")


def phase_task(state: dict[str, Any], phase_id: str, task_id: str) -> dict[str, Any]:
    phase = (state.get("phases") or {}).get(phase_id)
    if not isinstance(phase, dict):
        raise ValueError(f"phase not found: {phase_id}")
    task = (phase.get("tasks") or {}).get(task_id)
    if not isinstance(task, dict):
        raise ValueError(f"task not found: {phase_id}/{task_id}")
    return task


def resolve_run_path(run_root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = run_root / path
    path = path.resolve()
    try:
        path.relative_to(run_root)
    except ValueError as exc:
        raise ValueError(f"path is outside run root: {path}") from exc
    return path


def next_attempt_number(task_root: Path, role: str) -> int:
    attempts = task_root / "attempts"
    maximum = 0
    if attempts.is_dir():
        pattern = re.compile(rf"^{re.escape(role)}-(\d+)$")
        for child in attempts.iterdir():
            match = pattern.match(child.name)
            if match:
                maximum = max(maximum, int(match.group(1)))
    return maximum + 1


def run_checked(cmd: list[str], *, input_text: str | None = None, allowed: set[int] = {0}) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(cmd, text=True, input=input_text, capture_output=True, check=False)
    if cp.returncode not in allowed:
        detail = (cp.stderr or cp.stdout).strip()
        raise RuntimeError(f"command failed ({cp.returncode}): {' '.join(cmd)}\n{detail[:4000]}")
    return cp


def current_contract(run_root: Path, task: dict[str, Any]) -> Path:
    binding = task.get("current_contract") or {}
    raw = binding.get("path")
    if not isinstance(raw, str):
        raise ValueError("task.current_contract.path is missing; bind the contract first")
    path = resolve_run_path(run_root, raw)
    if not path.is_file():
        raise ValueError(f"current contract missing: {path}")
    return path


def current_worker_rules(run_root: Path, state: dict[str, Any], override: str | None) -> Path:
    raw = override or (state.get("worker_rules") or {}).get("path")
    if not isinstance(raw, str):
        raise ValueError("state.worker_rules.path is missing; prepare/bind worker rules first")
    path = resolve_run_path(run_root, raw)
    if not path.is_file():
        raise ValueError(f"worker rules missing: {path}")
    return path


def opencode_runtime(state: dict[str, Any], db_override: str | None, model_override: str | None) -> tuple[Path, str]:
    runtime = state.get("worker_runtime") or {}
    harness = str(runtime.get("harness") or "opencode-cli")
    if harness not in {"opencode-cli", "opencode"}:
        raise ValueError(f"dsd_attempt launch supports external OpenCode only; configured worker harness is {harness!r}")
    model = model_override or runtime.get("model") or "opencode-go/deepseek-v4-flash"
    db_raw = db_override or (runtime.get("opencode") or {}).get("run_db") or os.environ.get("DSD_OC_RUN_DB")
    if not isinstance(db_raw, str) or not db_raw.strip():
        raise ValueError("OpenCode run DB is not configured (state.worker_runtime.opencode.run_db, --db, or DSD_OC_RUN_DB)")
    db = Path(db_raw)
    if not db.is_absolute():
        raise ValueError(f"OpenCode DB must be absolute and outside the project: {db}")
    return db.resolve(), str(model)


def launch(args: argparse.Namespace) -> int:
    run_root = args.run_root.resolve()
    state_path = run_root / "state.json"
    state = read_json(state_path)
    task = phase_task(state, args.phase_id, args.task_id)
    role = args.role

    project_root = project_root_from_run(run_root, state)
    contract = current_contract(run_root, task)
    worker_rules = current_worker_rules(run_root, state, args.worker_rules)
    db, model = opencode_runtime(state, args.db, args.model)
    task_root = contract.parent.parent if contract.parent.name == "contracts" else contract.parent
    try:
        task_root.relative_to(run_root)
    except ValueError as exc:
        raise ValueError(f"task root is outside run root: {task_root}") from exc

    scripts = Path(__file__).resolve().parent
    # Fail before launching a worker if state/contract binding or prior-attempt lifecycle
    # cannot support a clean transition. This prevents "worker launched, state bind failed".
    preflight_cmd = [
        sys.executable, str(scripts / "dsd_state.py"), "preflight-attempt",
        "--run-root", str(run_root), "--phase-id", args.phase_id,
        "--task-id", args.task_id, "--contract", str(contract),
    ]
    if getattr(args, "supersede_incomplete", False):
        preflight_cmd.append("--supersede-incomplete")
    run_checked(preflight_cmd)

    attempt = args.attempt or next_attempt_number(task_root, role)
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    event_dir = task_root / "attempts" / f"{role}-{attempt}"
    prompt = event_dir / "launch-prompt.txt"
    baseline = event_dir / "scope-baseline.json"
    log = event_dir / "worker.log"
    report = event_dir / "report.md"

    event_dir.mkdir(parents=True, exist_ok=False)
    try:
        run_checked([
            sys.executable, str(scripts / "scope_snapshot.py"), "capture",
            "--root", str(project_root), "--output", str(baseline),
            "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy",
            "--task-contract", str(contract),
        ])
        run_checked([
            sys.executable, str(scripts / "render_worker_prompt.py"),
            "--role", role, "--task-id", args.task_id,
            "--run-root", str(run_root), "--worker-rules", str(worker_rules),
            "--task", str(contract), "--report", str(report),
            *sum((["--input", str(resolve_run_path(run_root, value))] for value in (getattr(args, "input", None) or [])), []),
            "--output", str(prompt),
        ])

        cmd = [
            sys.executable, str(scripts / "run_worker.py"),
            "--project-root", str(project_root), "--run-root", str(run_root),
            "--task-id", args.task_id, "--role", role, "--attempt", str(attempt),
            "--prompt-file", str(prompt), "--task-contract", str(contract),
            "--worker-rules", str(worker_rules), "--scope-baseline", str(baseline),
            "--report", str(report), "--event-dir", str(event_dir), "--log", str(log),
            "--db", str(db), "--model", model,
        ]
        if getattr(args, "force_read_only", False):
            cmd.append("--force-read-only")
        if args.resume_session:
            cmd += ["--resume-session", args.resume_session]
        if args.auto_flag is not None:
            cmd += [f"--auto-flag={args.auto_flag}"]
        # Always use the detached low-level monitor so the immutable reservation can
        # be bound into state immediately. Foreground behavior is implemented by a
        # cheap wait *after* state binding, not by hiding a long worker inside launch.
        cmd.append("--detach")
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False)

        # Reservation is created before worker execution/detach. Bind lifecycle state
        # even if foreground transport later fails, so recovery sees exact reality.
        reservation = event_dir / "launch-reservation.json"
        if reservation.is_file():
            next_action = (
                f"wait for {args.phase_id}/{args.task_id} {role} terminal event"
                if args.detach and not (event_dir / "terminal.json").is_file()
                else f"classify {args.phase_id}/{args.task_id} {role} terminal event"
            )
            state_cmd = [
                sys.executable, str(scripts / "dsd_state.py"), "bind-attempt",
                "--run-root", str(run_root), "--phase-id", args.phase_id,
                "--task-id", args.task_id, "--event-dir", str(event_dir),
                "--next-action", next_action,
            ]
            state_cmd += ["--wait-kind", args.wait_kind or "external-worker-terminal"]
            if getattr(args, "supersede_incomplete", False):
                state_cmd.append("--supersede-incomplete")
            launch_json = cp.stdout.strip() if cp.stdout.strip().startswith("{") else None
            if launch_json:
                state_cmd += ["--launch-json", "-"]
            state_cp = run_checked(state_cmd, input_text=launch_json)
            state_result = json.loads(state_cp.stdout)
        else:
            state_result = None
            if cp.returncode != 0:
                # No immutable reservation means the worker never entered the attempt
                # lifecycle. Remove setup-only artifacts rather than leaving an orphan
                # directory that looks like recoverable execution evidence.
                import shutil
                shutil.rmtree(event_dir, ignore_errors=True)
                if cp.stderr.strip():
                    sys.stderr.write(cp.stderr)
                return cp.returncode

        # Premium-facing stdout is status only. Full detail is durable in the attempt directory/state.
        result = {
            "status": "started" if args.detach else "waiting",
            "attempt": f"{role}-{attempt}",
            "event_dir": str(event_dir),
        }
        rc = cp.returncode
        if cp.returncode == 0 and not args.detach:
            wait_cp = subprocess.run([
                sys.executable, str(scripts / "wait_worker.py"),
                "--event-dir", str(event_dir),
            ], text=True, capture_output=True, check=False)
            try:
                wait_data = json.loads(wait_cp.stdout) if wait_cp.stdout.strip() else {}
            except json.JSONDecodeError:
                wait_data = {}
            result["status"] = wait_data.get("status") or "terminal"
            if wait_data.get("exit_code") is not None:
                result["exit_code"] = wait_data.get("exit_code")
            if wait_cp.returncode in {0, 1}:
                refresh = subprocess.run([
                    sys.executable, str(scripts / "dsd_state.py"), "bind-attempt",
                    "--run-root", str(run_root), "--phase-id", args.phase_id,
                    "--task-id", args.task_id, "--event-dir", str(event_dir),
                    "--next-action", f"gate {args.phase_id}/{args.task_id} {role} attempt {event_dir}",
                ], text=True, capture_output=True, check=False)
                if refresh.returncode != 0:
                    if refresh.stderr.strip():
                        sys.stderr.write(refresh.stderr)
                    return refresh.returncode
            elif wait_cp.stderr.strip():
                sys.stderr.write(wait_cp.stderr)
            rc = wait_cp.returncode
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return rc
    except Exception:
        # Pre-reservation setup is safe to clean up. Once reservation exists, preserve
        # the exact attempt directory for Recovery/audit.
        if not (event_dir / "launch-reservation.json").exists():
            import shutil
            shutil.rmtree(event_dir, ignore_errors=True)
        raise


def next_gate_path(event_dir: Path) -> Path:
    base = event_dir / "evidence-gate.json"
    if not base.exists():
        return base
    for i in range(2, 10000):
        candidate = event_dir / f"evidence-gate-{i:02d}.json"
        if not candidate.exists():
            return candidate
    raise ValueError(f"cannot allocate evidence-gate path under {event_dir}")


def gate(args: argparse.Namespace) -> int:
    run_root = args.run_root.resolve()
    state = read_json(run_root / "state.json")
    task = phase_task(state, args.phase_id, args.task_id)
    project_root = project_root_from_run(run_root, state)
    if args.event_dir:
        event_dir = resolve_run_path(run_root, args.event_dir)
    else:
        attempt = task.get("current_attempt") or {}
        event_raw = attempt.get("event_dir")
        if not isinstance(event_raw, str):
            raise ValueError("task.current_attempt.event_dir is missing; pass --event-dir for an earlier immutable attempt")
        event_dir = resolve_run_path(run_root, event_raw)
    reservation_path = event_dir / "launch-reservation.json"
    if not reservation_path.is_file():
        raise ValueError(f"launch reservation missing: {reservation_path}")
    reservation = read_json(reservation_path)
    role = str(reservation.get("role") or "")
    for key in ("task_contract", "report", "scope_baseline", "log"):
        if not isinstance(reservation.get(key), str):
            raise ValueError(f"reservation lacks {key}")
    task_path = resolve_run_path(run_root, reservation["task_contract"])
    report = resolve_run_path(run_root, reservation["report"])
    baseline = resolve_run_path(run_root, reservation["scope_baseline"])
    log = resolve_run_path(run_root, reservation["log"])
    terminal = event_dir / "terminal.json"
    if not terminal.is_file():
        raise ValueError(f"attempt is not terminal yet: {terminal}")
    output = next_gate_path(event_dir)
    scripts = Path(__file__).resolve().parent
    cmd = [
        sys.executable, str(scripts / "evidence_gate.py"),
        "--run-root", str(run_root), "--task", str(task_path), "--report", str(report),
        "--role", role, "--project-root", str(project_root), "--scope-baseline", str(baseline),
        "--terminal-event", str(terminal), "--log", str(log), "--output", str(output), "--json",
    ]
    cp = subprocess.run(cmd, text=True, capture_output=True, check=False)
    # Bind the objective gate result into state; no semantic routing is inferred.
    if output.is_file():
        next_action = f"route gated {role} attempt {event_dir}"
        state_cp = subprocess.run([
            sys.executable, str(scripts / "dsd_state.py"), "bind-gate",
            "--run-root", str(run_root), "--phase-id", args.phase_id,
            "--task-id", args.task_id, "--gate", str(output),
            "--next-action", next_action,
        ], text=True, capture_output=True, check=False)
        if state_cp.returncode != 0:
            if state_cp.stderr.strip(): sys.stderr.write(state_cp.stderr)
            return state_cp.returncode
    if cp.stderr.strip():
        sys.stderr.write(cp.stderr)
    if cp.stdout.strip():
        try:
            gate_data = json.loads(cp.stdout)
        except json.JSONDecodeError:
            sys.stdout.write(cp.stdout)
        else:
            surface_lines: list[str] = []
            if args.surface and gate_data.get("ready_for_interpretation") is True and report.is_file():
                surface_cp = subprocess.run([
                    sys.executable, str(scripts / "report_surface.py"),
                    "--report", str(report), "--json",
                ], text=True, capture_output=True, check=False)
                if surface_cp.returncode == 0:
                    try:
                        surface_lines = json.loads(surface_cp.stdout).get("surface", [])
                    except Exception:
                        surface_lines = []
            summary = {
                "integrity_ok": gate_data.get("integrity_ok") is True,
                "gate": str(output),
            }
            if gate_data.get("needs_report_recovery") is True:
                summary["report_recovery"] = True
            if gate_data.get("errors"):
                summary["errors"] = gate_data.get("errors")
            if args.surface:
                summary["report_surface"] = surface_lines
            print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return cp.returncode


def wait(args: argparse.Namespace) -> int:
    run_root = args.run_root.resolve()
    state = read_json(run_root / "state.json")
    task = phase_task(state, args.phase_id, args.task_id)
    if args.event_dir:
        event_dir = resolve_run_path(run_root, args.event_dir)
    else:
        raw = (task.get("current_attempt") or {}).get("event_dir")
        if not isinstance(raw, str):
            raise ValueError("task.current_attempt.event_dir is missing; pass --event-dir")
        event_dir = resolve_run_path(run_root, raw)
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "wait_worker.py"), "--event-dir", str(event_dir)]
    if args.timeout is not None:
        cmd += ["--timeout", str(args.timeout)]
    cp = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if cp.returncode in {0, 1} and (event_dir / "terminal.json").is_file():
        refresh = subprocess.run([
            sys.executable, str(Path(__file__).resolve().parent / "dsd_state.py"), "bind-attempt",
            "--run-root", str(run_root), "--phase-id", args.phase_id,
            "--task-id", args.task_id, "--event-dir", str(event_dir),
            "--next-action", f"gate {args.phase_id}/{args.task_id} attempt {event_dir}",
        ], text=True, capture_output=True, check=False)
        if refresh.returncode != 0:
            if refresh.stderr.strip():
                sys.stderr.write(refresh.stderr)
            return refresh.returncode
    if cp.stdout.strip():
        try:
            waited = json.loads(cp.stdout)
        except json.JSONDecodeError:
            sys.stdout.write(cp.stdout)
        else:
            compact = {"status": waited.get("status")}
            if waited.get("exit_code") is not None:
                compact["exit_code"] = waited.get("exit_code")
            print(json.dumps(compact, sort_keys=True, separators=(",", ":")))
    if cp.stderr.strip():
        sys.stderr.write(cp.stderr)
    return cp.returncode


def latest_integrity_gate(event_dir: Path) -> Path:
    candidates = list(event_dir.glob("evidence-gate*.json"))
    if not candidates:
        raise ValueError(f"no integrity gate found under source attempt: {event_dir}")
    def rank(path: Path) -> tuple[int, str]:
        m = re.search(r"-(\d+)\.json$", path.name)
        return (int(m.group(1)) if m else 1, path.name)
    return max(candidates, key=rank)


def interpret(args: argparse.Namespace) -> int:
    """Launch the standard Evidence Clerk over an exact source attempt.

    This composes paths only. It does not interpret the source report or decide what
    the Clerk should conclude.
    """
    run_root = args.run_root.resolve()
    state = read_json(run_root / "state.json")
    task = phase_task(state, args.phase_id, args.task_id)
    if args.source_event_dir:
        source_event = resolve_run_path(run_root, args.source_event_dir)
    else:
        raw = (task.get("current_attempt") or {}).get("event_dir")
        if not isinstance(raw, str):
            raise ValueError("task.current_attempt.event_dir is missing; pass --source-event-dir")
        source_event = resolve_run_path(run_root, raw)
    source_gate = resolve_run_path(run_root, args.source_gate) if args.source_gate else latest_integrity_gate(source_event)
    gate_data = read_json(source_gate)
    if str(gate_data.get("role") or "").lower() == "evidence-clerk":
        raise ValueError("Evidence Clerk output routes to the parent; Clerk-of-Clerk interpretation is not a DSD path")
    if gate_data.get("integrity_ok") is not True or gate_data.get("errors"):
        raise ValueError("source attempt integrity gate is not clean; Clerk cannot waive integrity failure")
    if gate_data.get("ready_for_interpretation") is not True:
        raise ValueError("source report is not available for interpretation; use report recovery/Recovery first")
    source_report_raw = gate_data.get("report")
    if not isinstance(source_report_raw, str):
        raise ValueError("source integrity gate lacks report binding")
    source_report = resolve_run_path(run_root, source_report_raw)
    if not source_report.is_file():
        raise ValueError(f"source report missing: {source_report}")

    launch_args = argparse.Namespace(
        run_root=run_root, phase_id=args.phase_id, task_id=args.task_id,
        role="evidence-clerk", attempt=None, worker_rules=args.worker_rules,
        db=args.db, model=args.model, detach=args.detach, wait_kind=args.wait_kind,
        resume_session=None, auto_flag=args.auto_flag,
        input=[str(source_report), str(source_gate)], force_read_only=True,
        supersede_incomplete=False,
    )
    return launch(launch_args)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--run-root", type=Path, required=True)
    common.add_argument("--phase-id", required=True)
    common.add_argument("--task-id", required=True)

    l = sub.add_parser("launch", parents=[common], help="derive attempt paths, capture baseline, render prompt, launch OpenCode, and bind state")
    l.add_argument("--role", choices=sorted(ROLE_NAMES), required=True)
    l.add_argument("--attempt", type=int, help="normally omitted; next per-role attempt number is derived")
    l.add_argument("--worker-rules", help="override state.worker_rules.path")
    l.add_argument("--db", help="override state.worker_runtime.opencode.run_db")
    l.add_argument("--model", help="override state.worker_runtime.model")
    l.add_argument("--detach", action="store_true")
    l.add_argument("--wait-kind")
    l.add_argument("--resume-session", help="same-role continuation only")
    l.add_argument("--auto-flag", default="--auto", help="OpenCode permission flag; pass empty string to omit")
    l.add_argument("--input", action="append", default=[], help="additional exact run artifact input supplied to this worker")
    l.add_argument("--force-read-only", action="store_true", help="reserve attempt as project-read-only regardless of task write scope")
    l.add_argument("--supersede-incomplete", action="store_true", help="exceptional recovery: archive a terminal-less prior attempt as lifecycle-incomplete before binding the new attempt; never use while the old worker may still write")

    i = sub.add_parser("interpret", parents=[common], help="launch an Evidence Clerk over one mechanically clean source attempt without authoring another Clerk contract")
    i.add_argument("--source-event-dir", help="source attempt directory; defaults to task.current_attempt.event_dir")
    i.add_argument("--source-gate", help="source integrity gate; defaults to latest evidence-gate*.json in source event dir")
    i.add_argument("--worker-rules", help="override state.worker_rules.path")
    i.add_argument("--db", help="override state.worker_runtime.opencode.run_db")
    i.add_argument("--model", help="override state.worker_runtime.model")
    i.add_argument("--detach", action="store_true")
    i.add_argument("--wait-kind")
    i.add_argument("--auto-flag", default="--auto")

    w = sub.add_parser("wait", parents=[common], help="quiescently wait for the current attempt terminal event")
    w.add_argument("--event-dir", help="optional run-relative/absolute immutable attempt directory")
    w.add_argument("--timeout", type=float, help="optional helper timeout; omission uses wait_worker default")

    g = sub.add_parser("gate", parents=[common], help="verify objective integrity for the task's current terminal attempt, or an explicitly named earlier attempt")
    g.add_argument("--event-dir", help="optional run-relative/absolute immutable attempt directory")
    g.add_argument("--surface", action="store_true", help="also return a bounded non-semantic report prefix for a parent decision boundary")
    return ap


def main() -> int:
    args = parser().parse_args()
    if not args.run_root.is_absolute():
        print("ERROR: --run-root must be absolute", file=sys.stderr)
        return 2
    try:
        if args.command == "launch":
            return launch(args)
        if args.command == "interpret":
            return interpret(args)
        if args.command == "wait":
            return wait(args)
        return gate(args)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
