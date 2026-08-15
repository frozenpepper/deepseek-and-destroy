import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
STATE = ROOT / "scripts" / "dsd_state.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class V154LifecycleRegressions(unittest.TestCase):
    def make_run(self, root: Path):
        run = root / "project" / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"
        contract = run / "phases" / "p1" / "t1" / "contracts" / "task-r0001.md"
        contract.parent.mkdir(parents=True, exist_ok=True)
        contract.write_text("# Task\n\nContract revision: r0001\n\n## Allowed source changes\nNONE\n", encoding="utf-8")
        rel_contract = contract.relative_to(run)
        state = {
            "phases": {"p1": {"status": "in-progress", "tasks": {
                "t1": {"status": "prepared", "current_contract": {"revision": 1, "path": str(rel_contract), "sha256": sha(contract)}}
            }}},
            "next_action": "test",
        }
        write_json(run / "state.json", state)
        return run, contract

    def make_attempt(self, run: Path, contract: Path, role: str, number: int, *, terminal: bool = False):
        event = contract.parent.parent / "attempts" / f"{role}-{number}"
        event.mkdir(parents=True, exist_ok=True)
        reservation = event / "launch-reservation.json"
        write_json(reservation, {
            "format": "dsd-worker-launch-reservation-v2",
            "task_id": "t1", "role": role, "attempt": number,
            "writes_project": role in {"implementer", "fixer"},
            "task_contract": str(contract.resolve()),
            "task_contract_sha256": sha(contract),
            "reserved_at": "2026-08-12T00:00:00Z",
        })
        if terminal:
            write_json(event / "terminal.json", {
                "format": "dsd-worker-terminal-v3", "status": "completed", "exit_code": 0,
                "task_id": "t1", "role": role, "attempt": number,
                "launch_reservation": str(reservation.resolve()),
                "launch_reservation_sha256": sha(reservation),
            })
        return event, reservation

    def run_state(self, run: Path, *args: str, cwd: Path | None = None):
        return subprocess.run(
            [PYTHON, str(STATE), *args, "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "t1"],
            cwd=cwd, text=True, capture_output=True,
        )

    def test_bind_attempt_resolves_run_relative_contract_against_run_root_not_cwd(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); run, contract = self.make_run(root)
            event, _ = self.make_attempt(run, contract, "reviewer", 1, terminal=True)
            # Deliberately invoke from project root, reproducing the field failure.
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(event.relative_to(run)), cwd=root / "project")
            self.assertEqual(cp.returncode, 0, cp.stderr)
            state = json.loads((run / "state.json").read_text())
            self.assertEqual(state["phases"]["p1"]["tasks"]["t1"]["current_attempt"]["role"], "reviewer")

    def test_reportless_terminal_attempt_can_enter_report_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); run, contract = self.make_run(root)
            event, reservation = self.make_attempt(run, contract, "reviewer", 1, terminal=True)
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(event))
            self.assertEqual(cp.returncode, 0, cp.stderr)
            gate = event / "evidence-gate.json"
            write_json(gate, {
                "integrity_ok": True, "ready_for_interpretation": False,
                "needs_report_recovery": True,
                "launch_reservation": str(reservation.resolve()),
            })
            cp = self.run_state(run, "bind-gate", "--gate", str(gate))
            self.assertEqual(cp.returncode, 0, cp.stderr)
            task = json.loads((run / "state.json").read_text())["phases"]["p1"]["tasks"]["t1"]
            self.assertEqual(task["status"], "report-recovery")

    def test_completed_attempt_is_archived_automatically_when_next_role_binds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); run, contract = self.make_run(root)
            old, old_res = self.make_attempt(run, contract, "implementer", 1, terminal=True)
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(old)); self.assertEqual(cp.returncode, 0, cp.stderr)
            gate = old / "evidence-gate.json"; write_json(gate, {"integrity_ok": True, "ready_for_interpretation": True, "needs_report_recovery": False, "launch_reservation": str(old_res.resolve())})
            cp = self.run_state(run, "bind-gate", "--gate", str(gate)); self.assertEqual(cp.returncode, 0, cp.stderr)

            new, _ = self.make_attempt(run, contract, "reviewer", 1, terminal=False)
            cp = self.run_state(run, "preflight-attempt", "--contract", str(contract)); self.assertEqual(cp.returncode, 0, cp.stderr)
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(new)); self.assertEqual(cp.returncode, 0, cp.stderr)
            task = json.loads((run / "state.json").read_text())["phases"]["p1"]["tasks"]["t1"]
            self.assertEqual(task["current_attempt"]["role"], "reviewer")
            self.assertEqual(task["last_attempt"]["role"], "implementer")
            self.assertEqual(task["last_attempt"]["status"], "gated")
            self.assertIn("integrity_gate", task["last_attempt"])

    def test_terminal_less_prior_attempt_requires_explicit_supersede_and_is_recorded_honestly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); run, contract = self.make_run(root)
            old, _ = self.make_attempt(run, contract, "implementer", 1, terminal=False)
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(old)); self.assertEqual(cp.returncode, 0, cp.stderr)
            # No terminal, and no known live PID: ordinary launch preflight must fail closed.
            cp = self.run_state(run, "preflight-attempt", "--contract", str(contract))
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("lifecycle is incomplete", cp.stderr)
            cp = self.run_state(run, "preflight-attempt", "--contract", str(contract), "--supersede-incomplete")
            self.assertEqual(cp.returncode, 0, cp.stderr)
            new, _ = self.make_attempt(run, contract, "recovery", 1, terminal=False)
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(new), "--supersede-incomplete")
            self.assertEqual(cp.returncode, 0, cp.stderr)
            task = json.loads((run / "state.json").read_text())["phases"]["p1"]["tasks"]["t1"]
            self.assertEqual(task["last_attempt"]["status"], "lifecycle-incomplete")
            self.assertEqual(task["last_attempt"]["disposition"], "superseded")
            self.assertEqual(task["current_attempt"]["role"], "recovery")

    def test_live_terminal_less_attempt_cannot_be_superseded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); run, contract = self.make_run(root)
            old, _ = self.make_attempt(run, contract, "implementer", 1, terminal=False)
            write_json(old / "attempt.json", {"worker_pid": os.getpid(), "started_at": "now"})
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(old)); self.assertEqual(cp.returncode, 0, cp.stderr)
            cp = self.run_state(run, "preflight-attempt", "--contract", str(contract), "--supersede-incomplete")
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("still live", cp.stderr)

    def test_gate_can_attach_to_archived_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); run, contract = self.make_run(root)
            old, old_res = self.make_attempt(run, contract, "implementer", 1, terminal=True)
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(old)); self.assertEqual(cp.returncode, 0, cp.stderr)
            new, _ = self.make_attempt(run, contract, "reviewer", 1, terminal=False)
            cp = self.run_state(run, "bind-attempt", "--event-dir", str(new)); self.assertEqual(cp.returncode, 0, cp.stderr)
            gate = old / "evidence-gate.json"; write_json(gate, {"integrity_ok": True, "ready_for_interpretation": True, "needs_report_recovery": False, "launch_reservation": str(old_res.resolve())})
            cp = self.run_state(run, "bind-gate", "--gate", str(gate)); self.assertEqual(cp.returncode, 0, cp.stderr)
            result = json.loads(cp.stdout)
            self.assertFalse(result["current"])
            task = json.loads((run / "state.json").read_text())["phases"]["p1"]["tasks"]["t1"]
            self.assertEqual(task["current_attempt"]["role"], "reviewer")
            self.assertIn("integrity_gate", task["last_attempt"])


    def test_high_level_detached_launch_binds_state_before_long_worker_finishes_and_wait_refreshes_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"
            contract = run / "phases" / "p1" / "t1" / "contracts" / "task-r0001.md"
            contract.parent.mkdir(parents=True)
            (root / "bin").mkdir()
            (root / "external").mkdir()
            subprocess.run(["git", "init"], cwd=project, text=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
            subprocess.run(["git", "config", "user.name", "DSD Test"], cwd=project)
            (project / "source.py").write_text("VALUE=1\n")
            (project / "PLAN.md").write_text("plan\n")
            subprocess.run(["git", "add", "source.py", "PLAN.md"], cwd=project)
            subprocess.run(["git", "commit", "-m", "base"], cwd=project, text=True, capture_output=True)
            contract.write_text(
                "# Task\nContract revision: r0001\n\n## Objective\nInspect.\n\n"
                "## Allowed source changes\nNONE\n\n## Acceptance criteria\n- AC-001 source exists.\n"
            )
            prep = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                 "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                 "--plan", str((project / "PLAN.md").resolve())],
                text=True, capture_output=True,
            )
            self.assertEqual(prep.returncode, 0, prep.stderr)
            state = {
                "project_worktree": str(project.resolve()), "execution_status": "active", "next_action": "launch",
                "worker_rules": json.loads(prep.stdout),
                "worker_runtime": {"harness": "opencode-cli", "model": "fake", "opencode": {"run_db": str((root / "external" / "workers.db").resolve())}},
                "phases": {"p1": {"status": "in-progress", "tasks": {
                    "t1": {"status": "prepared", "current_contract": {"revision": 1, "path": str(contract.relative_to(run)), "sha256": sha(contract)}}
                }}},
            }
            write_json(run / "state.json", state)
            fake = root / "bin" / "opencode"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import sys,time\n"
                "args=sys.argv[1:]\n"
                "if args[:2] == ['session','list']:\n    print('[]'); raise SystemExit(0)\n"
                "if args and args[0] == 'run':\n    time.sleep(1.5); raise SystemExit(0)\n"
                "raise SystemExit(2)\n"
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(root / "bin") + os.pathsep + env.get("PATH", "")
            launch = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch",
                 "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "t1",
                 "--role", "reviewer", "--detach", "--auto-flag="],
                env=env, cwd=project, text=True, capture_output=True,
            )
            self.assertEqual(launch.returncode, 0, launch.stderr)
            task = json.loads((run / "state.json").read_text())["phases"]["p1"]["tasks"]["t1"]
            self.assertIn(task["status"], {"launching", "in-progress"})
            self.assertEqual(task["current_attempt"]["role"], "reviewer")
            launch_data = json.loads(launch.stdout)
            event = Path(launch_data["event_dir"])
            self.assertEqual(Path(launch_data["terminal_event"]), event / "terminal.json")
            baseline_data = json.loads((event / "scope-baseline.json").read_text())
            self.assertEqual(baseline_data["inventory_mode"], "git-dirty")
            wait = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "wait",
                 "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "t1", "--timeout", "5"],
                env=env, cwd=project, text=True, capture_output=True,
            )
            self.assertEqual(wait.returncode, 0, wait.stdout + wait.stderr)
            self.assertTrue((event / "terminal.json").is_file())
            terminal_data = json.loads((event / "terminal.json").read_text())
            self.assertEqual(terminal_data["terminal_report"]["state"], "launcher-skeleton")
            self.assertEqual(terminal_data["terminal_report"]["sha256"], sha(event / "report.md"))
            self.assertIsInstance(terminal_data.get("terminal_scope"), dict)
            state = json.loads((run / "state.json").read_text())
            task = state["phases"]["p1"]["tasks"]["t1"]
            self.assertEqual(task["status"], "process-exited")
            self.assertFalse(state.get("orchestrator_wait", {}).get("active", False))
            gate = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "gate",
                 "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "t1"],
                env=env, cwd=project, text=True, capture_output=True,
            )
            self.assertEqual(gate.returncode, 4, gate.stdout + gate.stderr)
            gate_summary = json.loads(gate.stdout)
            self.assertEqual(gate_summary["attempt_output"], "reportless-no-change")
            state = json.loads((run / "state.json").read_text())
            task = state["phases"]["p1"]["tasks"]["t1"]
            self.assertEqual(task["status"], "report-recovery")
            self.assertIn("route reportless-no-change reviewer attempt", state["next_action"])


if __name__ == "__main__":
    unittest.main()
