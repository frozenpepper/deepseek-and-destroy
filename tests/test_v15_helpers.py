from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class V15HelpersTest(unittest.TestCase):
    """Objective helper invariants only; semantic worker interpretation is tested in v15.3."""

    def run_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)

    def init_project(self, root: Path) -> Path:
        project = root / "project"; project.mkdir(parents=True)
        self.assertEqual(self.run_cmd(["git", "init"], cwd=project).returncode, 0)
        self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
        self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
        (project / "base.txt").write_text("base\n")
        self.run_cmd(["git", "add", "base.txt"], cwd=project)
        self.run_cmd(["git", "commit", "-m", "base"], cwd=project)
        return project

    def rules(self, project: Path, run: Path) -> dict:
        plan = project / "PLAN.md"; plan.write_text("# Plan\n")
        cp = self.run_cmd([
            PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
            "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
            "--skill-root", str(ROOT.resolve()), "--plan", str(plan.resolve()),
        ])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return json.loads(cp.stdout)

    def test_prepare_rules_manifest_detects_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_project(root)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            info = self.rules(project, run)
            rules = Path(info["path"])
            verify = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--skill-root", str(ROOT.resolve()), "--plan", str((project / "PLAN.md").resolve()),
                "--reuse-existing",
            ])
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            common = rules.parent / "protocol" / "COMMON.md"
            common.write_text(common.read_text() + "\nTAMPER\n")
            bad = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--skill-root", str(ROOT.resolve()), "--plan", str((project / "PLAN.md").resolve()),
                "--reuse-existing",
            ])
            self.assertEqual(bad.returncode, 2)
            self.assertIn("immutable worker-rules revision changed", bad.stderr)

    def test_run_worker_keeps_recognizable_skeleton_when_worker_writes_no_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_project(root)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            rules = self.rules(project, run)
            task = run / "task.md"; task.write_text("# Task U1\n## Allowed source changes\nNONE\n")
            baseline = run / "baseline.json"
            snap = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project.resolve()), "--output", str(baseline.resolve()), "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy"])
            self.assertEqual(snap.returncode, 0, snap.stdout + snap.stderr)
            event = run / "attempt"; event.mkdir(); prompt = event / "prompt.txt"; prompt.write_text("do work\n")
            report = event / "report.md"; log = event / "worker.log"; db = root / "external" / "worker.db"
            bindir = root / "bin"; bindir.mkdir(); fake = bindir / "opencode"
            fake.write_text("#!/usr/bin/env python3\nimport json,sys\nif sys.argv[1:3]==['session','list']: print(json.dumps([])); raise SystemExit(0)\nif sys.argv[1:2]==['run']: print('done'); raise SystemExit(0)\nraise SystemExit(2)\n"); fake.chmod(0o755)
            env = os.environ.copy(); env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "run_worker.py"), "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--task-id", "U1", "--role", "reviewer", "--attempt", "1", "--prompt-file", str(prompt.resolve()),
                "--task-contract", str(task.resolve()), "--worker-rules", rules["path"], "--scope-baseline", str(baseline.resolve()),
                "--report", str(report.resolve()), "--event-dir", str(event.resolve()), "--log", str(log.resolve()), "--db", str(db.resolve()), "--auto-flag", "",
            ], env=env)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            text = report.read_text()
            self.assertIn("PENDING", text); self.assertNotIn("Verdict:", text)
            gate = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()), "--task", str(task.resolve()),
                "--report", str(report.resolve()), "--terminal-event", str((event / "terminal.json").resolve()), "--log", str(log.resolve()),
                "--role", "reviewer", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(gate.returncode, 4, gate.stdout + gate.stderr)
            payload = json.loads(gate.stdout)
            self.assertTrue(payload["mechanical_ok"]); self.assertTrue(payload["report_recovery_required"])
            self.assertEqual(payload["report_state"], "unchanged-skeleton")

    def test_scope_snapshot_detects_project_change_but_excludes_dsd_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_project(root)
            baseline = root / "baseline.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project.resolve()), "--output", str(baseline.resolve()), "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            (project / "DeepSeekAndDestroy").mkdir(); (project / "DeepSeekAndDestroy" / "state.json").write_text("{}")
            (project / "new.txt").write_text("new\n")
            diff = root / "diff.json"
            cmp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare", "--root", str(project.resolve()), "--baseline", str(baseline.resolve()), "--output", str(diff.resolve())])
            self.assertEqual(cmp.returncode, 0, cmp.stdout + cmp.stderr)
            paths = {x["path"] for x in json.loads(diff.read_text())["changed"]}
            self.assertIn("new.txt", paths); self.assertNotIn("DeepSeekAndDestroy/state.json", paths)

    def test_run_worker_rejects_db_inside_project_before_launch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_project(root)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            rules = self.rules(project, run)
            task = run / "task.md"; task.write_text("# Task\n")
            prompt = run / "prompt.txt"; prompt.write_text("x\n")
            scope = run / "scope.json"; scope.write_text("{}\n")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "run_worker.py"), "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--task-id", "U1", "--role", "reviewer", "--prompt-file", str(prompt.resolve()), "--task-contract", str(task.resolve()),
                "--worker-rules", rules["path"], "--scope-baseline", str(scope.resolve()), "--report", str((run / "r.md").resolve()),
                "--event-dir", str((run / "event").resolve()), "--log", str((run / "event" / "log").resolve()), "--db", str((project / "bad.db").resolve()),
            ])
            self.assertEqual(cp.returncode, 2)
            self.assertIn("outside", cp.stderr.lower())

    def test_state_detects_frozen_contract_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); run = root / "run"; run.mkdir(); contract = run / "task.md"; contract.write_text("# Task\n")
            state = run / "state.json"
            state.write_text(json.dumps({
                "execution_status": "active", "next_action": "review", "context_checkpoint": {"status": "none"},
                "phases": {"p1": {"tasks": {"U1": {"status": "prepared", "current_contract": {"revision": 1, "path": str(contract.resolve()), "sha256": hashlib.sha256(contract.read_bytes()).hexdigest()}}}}},
            }))
            self.assertEqual(self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state.resolve())]).returncode, 0)
            contract.write_text("# changed\n")
            bad = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state.resolve())])
            self.assertEqual(bad.returncode, 1); self.assertIn("hash changed", bad.stdout)


if __name__ == "__main__":
    unittest.main()
