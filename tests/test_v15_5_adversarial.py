from __future__ import annotations

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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class V155Adversarial(unittest.TestCase):
    def run_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)

    def init_git(self, root: Path, count: int = 40) -> Path:
        project = root / "project"; project.mkdir()
        self.assertEqual(self.run_cmd(["git", "init"], cwd=project).returncode, 0)
        self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
        self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
        for i in range(count):
            (project / f"f{i}.txt").write_text(f"{i}\n")
        self.run_cmd(["git", "add", "."], cwd=project)
        self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
        return project

    def test_compact_scope_hashes_only_dirty_then_discovers_new_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git(root, 120); out = root / "out"; out.mkdir()
            (project / "f1.txt").write_text("dirty before\n")
            baseline = out / "baseline.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture",
                               "--root", str(project), "--output", str(baseline), "--git-dirty"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            base = json.loads(baseline.read_text())
            self.assertEqual(base["inventory_mode"], "git-dirty")
            self.assertEqual(set(base["entries"]), {"f1.txt"})
            self.assertLess(baseline.stat().st_size, 2000)

            (project / "f50.txt").write_text("changed during attempt\n")
            diff = out / "diff.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare",
                               "--root", str(project), "--baseline", str(baseline), "--output", str(diff)])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(diff.read_text())
            self.assertEqual([x["path"] for x in data["changed"]], ["f50.txt"])

    def test_compact_scope_detects_committed_change_via_head_delta(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git(root, 3); out = root / "out"; out.mkdir()
            baseline = out / "baseline.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture",
                               "--root", str(project), "--output", str(baseline), "--git-dirty"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(len(json.loads(baseline.read_text())["entries"]), 0)
            (project / "f2.txt").write_text("committed change\n")
            self.run_cmd(["git", "add", "f2.txt"], cwd=project)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "change"], cwd=project).returncode, 0)
            diff = out / "diff.json"
            self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare",
                          "--root", str(project), "--baseline", str(baseline), "--output", str(diff)])
            data = json.loads(diff.read_text())
            self.assertTrue(data["git_head_changed"])
            self.assertEqual([x["path"] for x in data["changed"]], ["f2.txt"])

    def _attempt(self, task_root: Path, contract: Path, role: str, number: int, reserved: str, ended: str,
                 *, writes: bool, changed: bool) -> Path:
        event = task_root / "attempts" / f"{role}-{number}"; event.mkdir(parents=True, exist_ok=True)
        report = event / "report.md"; report.write_text(f"{role} report\n")
        reservation = event / "launch-reservation.json"
        write_json(reservation, {
            "format": "dsd-worker-launch-reservation-v2", "task_id": task_root.name,
            "role": role, "attempt": number, "writes_project": writes,
            "task_contract": str(contract.resolve()), "task_contract_sha256": sha(contract),
            "report": str(report.resolve()), "reserved_at": reserved,
        })
        diff = event / "scope-diff.json"
        write_json(diff, {
            "format": "deepseek-and-destroy-scope-comparison-v5", "changed": ([{"path": "x.py"}] if changed else []),
            "git_head_changed": False,
        })
        terminal = event / "terminal.json"
        write_json(terminal, {
            "format": "dsd-worker-terminal-v3", "status": "completed", "exit_code": 0,
            "task_id": task_root.name, "role": role, "attempt": number,
            "process_ended_at": ended, "ended_at": ended,
            "launch_reservation": str(reservation.resolve()), "launch_reservation_sha256": sha(reservation),
            "terminal_scope": {"path": str(diff.resolve()), "sha256": sha(diff)},
        })
        return event

    def test_stale_reviewer_cannot_be_reused_after_later_fixer_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "DeepSeekAndDestroy" / "run"
            task_root = run / "phases" / "p1" / "tasks" / "U1"
            contract = task_root / "contracts" / "r0001.md"; contract.parent.mkdir(parents=True)
            contract.write_text("# Task\nContract revision: r0001\n")
            reviewer = self._attempt(task_root, contract, "reviewer", 1, "2026-08-13T10:00:00+00:00", "2026-08-13T10:01:00+00:00", writes=False, changed=False)
            self._attempt(task_root, contract, "fixer", 1, "2026-08-13T10:02:00+00:00", "2026-08-13T10:03:00+00:00", writes=True, changed=True)
            review_report = reviewer / "report.md"
            review_gate = reviewer / "evidence-gate.json"
            write_json(review_gate, {
                "format": "dsd-integrity-gate-v2", "integrity_ok": True, "ready_for_interpretation": True,
                "errors": [], "role": "reviewer", "task": str(contract.resolve()),
                "report": str(review_report.resolve()), "report_sha256": sha(review_report),
                "terminal_event": str((reviewer / "terminal.json").resolve()), "scope": {"changed_count": 0},
            })
            state = {"execution_status": "active", "next_action": "decide", "phases": {"p1": {"status": "in-progress", "tasks": {"U1": {
                "status": "gated", "current_contract": {"revision": 1, "path": str(contract.resolve()), "sha256": sha(contract)}
            }}}}}
            write_json(run / "state.json", state)
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                               "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1",
                               "--evidence-gate", str(review_gate.resolve())])
            self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)
            self.assertIn("predates later project mutation", cp.stderr)

    def test_tampered_terminal_scope_cannot_hide_later_writer_from_freshness_check(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "DeepSeekAndDestroy" / "run"
            task_root = run / "phases" / "p1" / "tasks" / "U1"
            contract = task_root / "contracts" / "r0001.md"; contract.parent.mkdir(parents=True)
            contract.write_text("# Task\nContract revision: r0001\n")
            reviewer = self._attempt(task_root, contract, "reviewer", 1, "2026-08-13T10:00:00+00:00", "2026-08-13T10:01:00+00:00", writes=False, changed=False)
            fixer = self._attempt(task_root, contract, "fixer", 1, "2026-08-13T10:02:00+00:00", "2026-08-13T10:03:00+00:00", writes=True, changed=True)
            # Tamper only the cold scope artifact after terminal so it falsely claims no change.
            write_json(fixer / "scope-diff.json", {
                "format": "deepseek-and-destroy-scope-comparison-v5", "changed": [], "git_head_changed": False,
            })
            report = reviewer / "report.md"; gate = reviewer / "evidence-gate.json"
            write_json(gate, {
                "format": "dsd-integrity-gate-v2", "integrity_ok": True, "ready_for_interpretation": True,
                "errors": [], "role": "reviewer", "task": str(contract.resolve()),
                "report": str(report.resolve()), "report_sha256": sha(report),
                "terminal_event": str((reviewer / "terminal.json").resolve()), "scope": {"changed_count": 0},
            })
            write_json(run / "state.json", {"execution_status": "active", "next_action": "decide", "phases": {"p1": {"status": "in-progress", "tasks": {"U1": {
                "status": "gated", "current_contract": {"revision": 1, "path": str(contract.resolve()), "sha256": sha(contract)}
            }}}}})
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                               "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1",
                               "--evidence-gate", str(gate.resolve())])
            self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)
            self.assertIn("predates later project mutation", cp.stderr)

    def test_old_contract_mutation_does_not_force_review_on_new_no_write_revision(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "DeepSeekAndDestroy" / "run"
            task_root = run / "phases" / "p1" / "tasks" / "U1"
            old_contract = task_root / "contracts" / "r0001.md"; old_contract.parent.mkdir(parents=True)
            old_contract.write_text("# Old Task\nContract revision: r0001\n")
            self._attempt(task_root, old_contract, "implementer", 1, "2026-08-13T09:00:00+00:00", "2026-08-13T09:01:00+00:00", writes=True, changed=True)
            contract = task_root / "contracts" / "r0002.md"
            contract.write_text("# New Task\nContract revision: r0002\n## Allowed source changes\nNONE\n")
            verifier = self._attempt(task_root, contract, "verification", 1, "2026-08-13T10:00:00+00:00", "2026-08-13T10:01:00+00:00", writes=False, changed=False)
            report = verifier / "report.md"; gate = verifier / "evidence-gate.json"
            write_json(gate, {
                "format": "dsd-integrity-gate-v2", "integrity_ok": True, "ready_for_interpretation": True,
                "errors": [], "role": "verification", "task": str(contract.resolve()),
                "report": str(report.resolve()), "report_sha256": sha(report),
                "terminal_event": str((verifier / "terminal.json").resolve()), "scope": {"changed_count": 0},
            })
            write_json(run / "state.json", {"execution_status": "active", "next_action": "decide", "phases": {"p1": {"status": "in-progress", "tasks": {"U1": {
                "status": "gated", "current_contract": {"revision": 2, "path": str(contract.resolve()), "sha256": sha(contract)}
            }}}}})
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                               "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1",
                               "--evidence-gate", str(gate.resolve())])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_acceptance_prunes_transient_attempt_state(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "DeepSeekAndDestroy" / "run"
            task_root = run / "phases" / "p1" / "tasks" / "U1"
            contract = task_root / "contracts" / "r0001.md"; contract.parent.mkdir(parents=True)
            contract.write_text("# Task\nContract revision: r0001\n")
            reviewer = self._attempt(task_root, contract, "reviewer", 1, "2026-08-13T10:02:00+00:00", "2026-08-13T10:03:00+00:00", writes=False, changed=False)
            report = reviewer / "report.md"; gate = reviewer / "evidence-gate.json"
            write_json(gate, {"format": "dsd-integrity-gate-v2", "integrity_ok": True, "ready_for_interpretation": True,
                              "errors": [], "role": "reviewer", "task": str(contract.resolve()), "report": str(report.resolve()),
                              "report_sha256": sha(report), "terminal_event": str((reviewer / "terminal.json").resolve()), "scope": {"changed_count": 0}})
            state = {"execution_status": "active", "next_action": "decide", "phases": {"p1": {"status": "in-progress", "tasks": {"U1": {
                "status": "gated", "current_contract": {"revision": 1, "path": str(contract.resolve()), "sha256": sha(contract)},
                "current_attempt": {"role": "reviewer", "attempt": 1, "event_dir": str(reviewer.resolve())},
                "last_attempt": {"role": "implementer", "attempt": 1, "event_dir": str((task_root / 'attempts' / 'implementer-1').resolve())},
            }}}}}
            write_json(run / "state.json", state)
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                               "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1",
                               "--evidence-gate", str(gate.resolve())])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            task = json.loads((run / "state.json").read_text())["phases"]["p1"]["tasks"]["U1"]
            self.assertNotIn("current_attempt", task)
            self.assertNotIn("last_attempt", task)
            self.assertEqual(task["status"], "accepted")

    def test_terminal_bound_report_cannot_be_rewritten_before_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git(root, 2)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            plan = project / "PLAN.md"; plan.write_text("plan\n")
            prep = self.run_cmd([PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                                 "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                                 "--plan", str(plan.resolve())])
            self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr)
            rules = Path(json.loads(prep.stdout)["path"]); manifest = rules.parent / "MANIFEST.json"
            task = run / "task.md"; task.write_text("# Task\nContract revision: r0001\n## Allowed source changes\nNONE\n")
            event = run / "attempt"; event.mkdir(); report = event / "report.md"; report.write_text("review complete\n")
            prompt = event / "prompt.txt"; prompt.write_text("prompt\n"); log = event / "worker.log"; log.write_text("")
            baseline = event / "scope-baseline.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture",
                               "--root", str(project.resolve()), "--output", str(baseline.resolve()),
                               "--git-dirty", "--exclude-prefix", "DeepSeekAndDestroy"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            reservation = event / "launch-reservation.json"
            write_json(reservation, {
                "format": "dsd-worker-launch-reservation-v2", "task_id": "U1", "role": "reviewer", "attempt": 1,
                "writes_project": False, "report": str(report.resolve()), "log": str(log.resolve()),
                "prompt_file": str(prompt.resolve()), "prompt_sha256": sha(prompt),
                "task_contract": str(task.resolve()), "task_contract_sha256": sha(task),
                "worker_rules": str(rules.resolve()), "worker_rules_sha256": sha(rules),
                "worker_rules_manifest": str(manifest.resolve()), "worker_rules_manifest_sha256": sha(manifest),
                "scope_baseline": str(baseline.resolve()), "scope_baseline_sha256": sha(baseline),
                "report_skeleton_sha256": "0" * 64, "reserved_at": "2026-08-13T10:00:00+00:00",
            })
            diff = event / "scope-diff.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare",
                               "--root", str(project.resolve()), "--baseline", str(baseline.resolve()), "--output", str(diff.resolve())])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            terminal = event / "terminal.json"
            write_json(terminal, {
                "format": "dsd-worker-terminal-v3", "status": "completed", "exit_code": 0, "task_id": "U1", "role": "reviewer", "attempt": 1,
                "launch_reservation": str(reservation.resolve()), "launch_reservation_sha256": sha(reservation),
                "terminal_report": {"path": str(report.resolve()), "sha256": sha(report), "state": "present"},
                "terminal_scope": {"path": str(diff.resolve()), "sha256": sha(diff)},
            })
            report.write_text("rewritten after worker exit\n")
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()),
                               "--task", str(task.resolve()), "--report", str(report.resolve()), "--role", "reviewer",
                               "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                               "--terminal-event", str(terminal.resolve()), "--log", str(log.resolve()), "--json"])
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            self.assertTrue(any("terminal-bound report changed" in e for e in json.loads(cp.stdout)["errors"]))

    def test_claude_rewake_recognizes_high_level_started_output(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            from claude_worker_rewake import launched_event_path
        finally:
            sys.path.pop(0)
        terminal = "/tmp/project/DeepSeekAndDestroy/run/attempt/terminal.json"
        payload = {"tool_name": "Bash", "tool_response": {"stdout": json.dumps({
            "status": "started", "attempt": "reviewer-1", "event_dir": str(Path(terminal).parent), "terminal_event": terminal,
        })}}
        self.assertEqual(launched_event_path(payload), Path(terminal))


    def test_compaction_run_selection_prefers_unique_orchestrator_harness(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"; project.mkdir()
            plans = project / "DeepSeekAndDestroy" / "plans"
            for name, harness in (("old-codex", "codex"), ("old-opencode", "opencode"), ("current-claude", "claude-code")):
                run = plans / name / "runs" / "run-1"
                write_json(run / "state.json", {
                    "execution_status": "active", "next_action": name,
                    "orchestrator": {"harness": harness},
                })
            sys.path.insert(0, str(ROOT / "scripts"))
            try:
                from context_checkpoint import choose_run
                run_root, state = choose_run(project, None, None, harness="claude-code")
            finally:
                sys.path.pop(0)
            self.assertEqual(run_root.parent.parent.name, "current-claude")
            self.assertEqual(state["next_action"], "current-claude")

    def test_precompact_ambiguity_warns_but_never_blocks_native_compaction(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"; project.mkdir()
            self.run_cmd(["git", "init"], cwd=project)
            plans = project / "DeepSeekAndDestroy" / "plans"
            for name in ("claude-a", "claude-b"):
                run = plans / name / "runs" / "run-1"
                write_json(run / "state.json", {
                    "execution_status": "active", "next_action": name,
                    "orchestrator": {"harness": "claude-code"},
                })
            payload = json.dumps({"cwd": str(project), "session_id": "unbound-session"})
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "context_checkpoint.py"),
                               "--project-root", str(project), "hook", "--harness", "claude-code", "--event", "precompact"],
                              input=payload)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            out = json.loads(cp.stdout)
            self.assertTrue(out.get("continue"))
            self.assertNotEqual(out.get("decision"), "block")
            self.assertIn("checkpoint skipped", out.get("systemMessage", "").lower())

    def test_new_phase_state_does_not_create_barrier_machine(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            write_json(run / "state.json", {"execution_status": "active", "next_action": "bind", "phases": {}})
            contract = run / "phases" / "p1" / "tasks" / "U1" / "contracts" / "r0001.md"
            contract.parent.mkdir(parents=True); contract.write_text("# Task\nContract revision: r0001\n")
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "bind-contract",
                               "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1", "--contract", str(contract.resolve())])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            phase = json.loads((run / "state.json").read_text())["phases"]["p1"]
            self.assertNotIn("gate_barrier", phase)


if __name__ == "__main__":
    unittest.main()
