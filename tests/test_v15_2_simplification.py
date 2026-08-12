import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class V152SimplificationTest(unittest.TestCase):
    def run_cmd(self, args, cwd=None, input_text=None):
        return subprocess.run(args, cwd=cwd, input=input_text, text=True, capture_output=True, check=False)

    def test_contract_json_spec_and_clerk_recursion_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"
            contract = run / "phases" / "p1" / "U1" / "contracts" / "r0001.md"
            run.mkdir(parents=True)
            spec = run / "contract.json"
            spec.write_text(json.dumps({
                "run_root": str(run.resolve()),
                "task_id": "U1",
                "revision": 1,
                "output": str(contract.resolve()),
                "unit": "JSON contract",
                "objective": "Do bounded work",
                "acceptance": ["AC-001 works"],
                "write_path": ["src/generated"],
                "extra_inventory": ["runtime/locks"],
            }))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "render_task_contract.py"), "--spec", str(spec)])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            payload = json.loads(cp.stdout)
            self.assertEqual(payload["format"], "dsd-task-contract-v4")
            text = contract.read_text()
            self.assertIn("## Extra scope inventory", text)
            self.assertIn("`runtime/locks`", text)

            legacy = run / "legacy-clerk-field.json"
            legacy.write_text(json.dumps({
                "run_root": str(run.resolve()), "task_id": "C1", "revision": 1,
                "output": str((run / "c1.md").resolve()), "unit": "Clerk", "objective": "Reconcile",
                "clerk_check": ["legacy semantic hook"],
            }))
            bad = self.run_cmd([PYTHON, str(ROOT / "scripts" / "render_task_contract.py"), "--spec", str(legacy)])
            self.assertEqual(bad.returncode, 2)
            self.assertIn("removed in v15.3", bad.stderr)

    def test_reviewer_semantics_are_not_machine_parsed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            review = root / "review.md"
            review.write_text(textwrap.dedent("""
                All local requirements were exercised and no task-relevant defect was found.
                AC-001 was reached through the real production path.
                This deliberately has no canonical Verdict line or Proof Matrix.
            """))
            self.assertFalse((ROOT / "scripts" / "check_review_contract.py").exists())
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "report_surface.py"), str(review), "--max-lines", "8"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertIn("All local requirements", cp.stdout)

    def test_extra_inventory_detects_new_ignored_files(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            project.mkdir()
            self.run_cmd(["git", "init"], cwd=project)
            self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
            self.run_cmd(["git", "config", "user.name", "DSD"], cwd=project)
            (project / ".gitignore").write_text("runtime/\n")
            (project / "tracked.txt").write_text("base\n")
            self.run_cmd(["git", "add", ".gitignore", "tracked.txt"], cwd=project)
            self.run_cmd(["git", "commit", "-m", "base"], cwd=project)
            (project / "runtime").mkdir()
            (project / "runtime" / "existing.lock").write_text("a")
            contract = Path(td) / "task.md"
            contract.write_text(textwrap.dedent("""
                # Task U1
                ## Extra scope inventory
                - `runtime`
            """))
            baseline = Path(td) / "baseline.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project), "--output", str(baseline), "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy", "--task-contract", str(contract)])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(baseline.read_text())
            self.assertEqual(data["extra_inventory_roots"], ["runtime"])
            (project / "runtime" / "new.lock").write_text("b")
            diff = Path(td) / "diff.json"
            cmp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare", "--root", str(project), "--baseline", str(baseline), "--output", str(diff)])
            self.assertEqual(cmp.returncode, 0, cmp.stdout + cmp.stderr)
            changed = {row["path"] for row in json.loads(diff.read_text())["changed"]}
            self.assertIn("runtime/new.lock", changed)

    def test_state_helper_updates_atomically_and_verification_is_conditionally_writable(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            state.write_text(json.dumps({"execution_status": "completed", "next_action": "old", "phases": {}}))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "--state", str(state.resolve()), "set-next", "--next-action", "new exact action"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(json.loads(state.read_text())["next_action"], "new exact action")

            probe = self.run_cmd([PYTHON, "-c", f"import sys; sys.path.insert(0,{str(ROOT / 'scripts')!r}); from _roles import role_is_project_writer; print(role_is_project_writer('verification', [])); print(role_is_project_writer('verification', ['dist'])); print(role_is_project_writer('evidence-clerk', ['docs']))"])
            self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertEqual(probe.stdout.splitlines(), ["False", "True", "False"])


if __name__ == "__main__":
    unittest.main()
