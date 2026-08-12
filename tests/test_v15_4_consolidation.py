import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class V154ConsolidationTest(unittest.TestCase):
    def test_hot_instruction_surfaces_stay_small_and_role_local(self):
        self.assertLessEqual((ROOT / "SKILL.md").stat().st_size, 7500)
        self.assertLessEqual((ROOT / "worker" / "COMMON.md").stat().st_size, 2000)
        self.assertLessEqual((ROOT / "worker" / "roles" / "dsd-reviewer" / "SKILL.md").stat().st_size, 1400)
        self.assertLessEqual((ROOT / "worker" / "roles" / "dsd-evidence-clerk" / "SKILL.md").stat().st_size, 1700)
        self.assertLessEqual((ROOT / "WORKSPACE.md").stat().st_size, 7500)
        self.assertLessEqual((ROOT / "OPENCODE.md").stat().st_size, 5000)
        self.assertLessEqual((ROOT / "COMPACTION.md").stat().st_size, 4500)
        self.assertLessEqual((ROOT / "KILO.md").stat().st_size, 2200)

    def test_executable_semantic_parser_surface_is_absent(self):
        for retired in ("check_review_contract.py", "_report_contract.py", "_report.py", "decision_packet.py"):
            self.assertFalse((ROOT / "scripts" / retired).exists(), retired)
        banned = ("Proof Matrix", "Task-relevant defects", "FAST-PATH", "require-review-pass", "clerk-report", "clerk-gate")
        for path in (ROOT / "scripts").glob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for token in banned:
                self.assertNotIn(token, text, f"{token!r} leaked into executable semantic logic: {path.name}")

    def test_role_capabilities_match_architecture(self):
        code = (
            "from _contract import role_writes_project; "
            "w='# T\\n\\n## Allowed source changes\\n- `src/generated`\\n'; "
            "r='# T\\n\\n## Allowed source changes\\nNONE\\n'; "
            "print(role_writes_project('implementer', w), role_writes_project('fixer', w), "
            "role_writes_project('verification', w), role_writes_project('verification', r), "
            "role_writes_project('evidence-clerk', w), role_writes_project('reviewer', w))"
        )
        cp = subprocess.run([PYTHON, "-c", code], cwd=ROOT / "scripts", text=True, capture_output=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(cp.stdout.strip(), "True True True False False False")

    def test_contract_renderer_exposes_only_json_spec_authoring(self):
        cp = subprocess.run([PYTHON, str(ROOT / "scripts" / "render_task_contract.py"), "--help"], text=True, capture_output=True)
        self.assertEqual(cp.returncode, 0)
        self.assertIn("--spec", cp.stdout)
        for legacy in ("--objective", "--acceptance", "--write-path", "--clerk-check", "--unit"):
            self.assertNotIn(legacy, cp.stdout)

    def test_obsolete_semantic_gate_flags_fail_loudly(self):
        cp = subprocess.run([PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--help"], text=True, capture_output=True)
        self.assertEqual(cp.returncode, 0)
        for flag in ("--require-review-pass", "--clerk-report", "--clerk-gate"):
            self.assertNotIn(flag, cp.stdout)

    def test_launcher_placeholder_has_no_old_report_grammar_token(self):
        text = (ROOT / "scripts" / "run_worker.py").read_text(encoding="utf-8")
        self.assertIn("DSD_WORKER_REPORT_PLACEHOLDER_V1", text)
        self.assertNotIn("DSD_REPORT_STATUS", text)

    def test_docs_make_clerk_optional_and_project_read_only(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        clerk = (ROOT / "worker" / "roles" / "dsd-evidence-clerk" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("only if useful", skill)
        self.assertIn("Never read Implementer/Fixer output when another specialist is the next consumer", skill)
        self.assertIn("Trust the specialist chain", skill)
        self.assertIn("Routine execution is silent", skill)
        self.assertIn("always project-read-only", clerk)
        self.assertNotIn("Evidence Clerk Checks", (ROOT / "templates" / "task-contract-spec.example.json").read_text(encoding="utf-8"))

    def test_proof_library_is_lazy_and_never_loaded_for_clerk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"
            run.mkdir(parents=True); (project / "PLAN.md").write_text("plan\n")
            prep = subprocess.run([PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"), "--project-root", str(project.resolve()), "--run-root", str(run.resolve()), "--plan", str((project / "PLAN.md").resolve())], text=True, capture_output=True)
            self.assertEqual(prep.returncode, 0, prep.stderr)
            import json
            rules = Path(json.loads(prep.stdout)["path"]); task = run / "task.md"; report = run / "report.md"
            task.write_text("# T\n\n## Allowed source changes\nNONE\n\n## Proof patterns\n- DURABILITY\n")
            common = ["--task-id", "U1", "--run-root", str(run.resolve()), "--worker-rules", str(rules), "--task", str(task.resolve()), "--report", str(report.resolve())]
            reviewer = subprocess.run([PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"), "--role", "reviewer", *common], text=True, capture_output=True)
            clerk = subprocess.run([PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"), "--role", "evidence-clerk", *common], text=True, capture_output=True)
            self.assertEqual(reviewer.returncode, 0, reviewer.stderr); self.assertEqual(clerk.returncode, 0, clerk.stderr)
            self.assertIn("PROOF-PATTERNS.md", reviewer.stdout)
            self.assertNotIn("PROOF-PATTERNS.md", clerk.stdout)


if __name__ == "__main__":
    unittest.main()
