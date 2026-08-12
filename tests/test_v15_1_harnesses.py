from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class V151HarnessAuditTest(unittest.TestCase):
    def run_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)

    def test_kilo_is_first_class_detectable_harness(self):
        cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "detect_harness.py"), "--harness", "kilo", "--json"])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["selected"], "kilo")
        self.assertEqual(data["capabilities"]["adapter"], "KILO.md")
        self.assertTrue(data["capabilities"]["precompact_hook"])

    def test_kilo_adapter_installs_canonical_plugin_and_complete_helper_set(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"; project.mkdir()
            cmd = [
                PYTHON, str(ROOT / "scripts" / "install_harness_adapter.py"),
                "--harness", "kilo", "--project-root", str(project), "--skill-root", str(ROOT),
            ]
            first = self.run_cmd(cmd); self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = self.run_cmd(cmd); self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            one, two = json.loads(first.stdout), json.loads(second.stdout)
            plugin = project / ".kilo" / "plugin" / "dsd-compaction.ts"
            self.assertEqual(plugin.read_text(), (ROOT / "adapters" / "kilo" / "dsd-compaction.ts").read_text())
            self.assertIn("export default", plugin.read_text())
            self.assertTrue(one["changed"]); self.assertFalse(two["changed"])
            self.assertNotIn(".kilo/plugins/", str(plugin))
            tools = project / "DeepSeekAndDestroy" / "tools"
            for name in ("context_checkpoint.py", "check_state.py", "_roles.py", "_rules_snapshot.py", "_task_contract.py"):
                self.assertTrue((tools / name).is_file(), name)
            check = self.run_cmd([PYTHON, str(tools / "check_state.py"), "--help"])
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_opencode_installer_consumes_canonical_plugin_asset(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"; project.mkdir()
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "install_harness_adapter.py"),
                "--harness", "opencode", "--project-root", str(project), "--skill-root", str(ROOT),
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            installed = project / ".opencode" / "plugins" / "dsd-compaction.ts"
            self.assertEqual(installed.read_text(), (ROOT / "adapters" / "opencode" / "dsd-compaction.ts").read_text())

    def test_kilo_worker_installer_uses_project_agents_and_validates_model(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir(); bindir = root / "bin"; bindir.mkdir()
            kilo = bindir / "kilo"
            kilo.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import sys
                if sys.argv[1:] == ['models']:
                    print('deepseek/deepseek-v4-flash')
                    raise SystemExit(0)
                raise SystemExit(2)
            """))
            kilo.chmod(0o755)
            env = os.environ.copy(); env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "install_kilo_workers.py"),
                "--project-root", str(project),
            ], env=env)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout); self.assertTrue(data["model_verified"])
            for name in ("dsd-mutating-worker.md", "dsd-readonly-worker.md"):
                target = project / ".kilo" / "agents" / name
                self.assertTrue(target.is_file())
                self.assertNotIn("{{MODEL}}", target.read_text())
                self.assertIn("deepseek/deepseek-v4-flash", target.read_text())

    def test_kilo_native_attempt_enters_normal_evidence_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir()
            self.run_cmd(["git", "init"], cwd=project)
            self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
            self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
            (project / "source.txt").write_text("base\n")
            self.run_cmd(["git", "add", "source.txt"], cwd=project)
            self.run_cmd(["git", "commit", "-m", "base"], cwd=project)
            run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"; run.mkdir(parents=True)
            plan = project / "plan.md"; plan.write_text("# Plan\n")
            prep = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--skill-root", str(ROOT.resolve()), "--plan", str(plan.resolve()), "--worker-harness", "kilo-native",
            ])
            self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr)
            rules = run / "worker-rules" / "r0001" / "WORKER_RULES.md"
            task = run / "task.md"
            task.write_text("# Task U1\n\n## Allowed source changes\nNONE\n\n## Acceptance criteria\n- AC-001 — source remains readable\n\n## Evidence Clerk Checks\nNONE\n")
            baseline = run / "scope.json"
            snap = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture",
                "--root", str(project.resolve()), "--output", str(baseline.resolve()),
                "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy",
            ])
            self.assertEqual(snap.returncode, 0, snap.stdout + snap.stderr)
            report = run / "review.md"; prompt = run / "prompt.txt"
            render = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"), "--role", "reviewer", "--task-id", "U1",
                "--run-root", str(run.resolve()), "--worker-rules", str(rules.resolve()), "--task", str(task.resolve()),
                "--report", str(report.resolve()), "--output", str(prompt.resolve()),
            ])
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            event = run / "attempts" / "reviewer-1"; log = event / "worker.log"
            reserve = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "native_worker_attempt.py"), "reserve", "--harness", "kilo",
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()), "--task-id", "U1",
                "--role", "reviewer", "--attempt", "1", "--prompt-file", str(prompt.resolve()),
                "--task-contract", str(task.resolve()), "--worker-rules", str(rules.resolve()),
                "--scope-baseline", str(baseline.resolve()), "--report", str(report.resolve()),
                "--event-dir", str(event.resolve()), "--log", str(log.resolve()),
            ])
            self.assertEqual(reserve.returncode, 0, reserve.stdout + reserve.stderr)
            report.write_text(
                "Reviewed the tracked production input directly. source.txt remained readable and unchanged; "
                "no task-relevant defect was found.\n"
            )
            final = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "native_worker_attempt.py"), "finalize",
                "--event-dir", str(event.resolve()), "--status", "completed",
            ])
            self.assertEqual(final.returncode, 0, final.stdout + final.stderr)
            terminal = json.loads((event / "terminal.json").read_text())
            self.assertEqual(terminal["transport"], "kilo-native")
            gate = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()),
                "--task", str(task.resolve()), "--report", str(report.resolve()), "--terminal-event", str((event / "terminal.json").resolve()),
                "--role", "reviewer", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                "--json",
            ])
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
            gated = json.loads(gate.stdout)
            self.assertTrue(gated["ok"]); self.assertTrue(gated["mechanical_ok"])
            self.assertNotIn("verdict", gated); self.assertNotIn("fast_path_eligible", gated)

    def test_all_core_harness_installers_use_canonical_assets_and_complete_helpers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for harness in ("codex", "claude-code", "opencode", "kilo"):
                project = root / harness; project.mkdir()
                cp = self.run_cmd([
                    PYTHON, str(ROOT / "scripts" / "install_harness_adapter.py"),
                    "--harness", harness, "--project-root", str(project), "--skill-root", str(ROOT),
                ])
                self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
                tools = project / "DeepSeekAndDestroy" / "tools"
                for name in ("context_checkpoint.py", "check_state.py", "_roles.py", "_rules_snapshot.py", "_task_contract.py"):
                    self.assertTrue((tools / name).is_file(), f"{harness}: {name}")
            codex = json.loads((root / "codex" / ".codex" / "hooks.json").read_text())
            canonical_codex = json.loads((ROOT / "adapters" / "codex" / "hooks.json").read_text())
            for event in canonical_codex["hooks"]:
                self.assertIn(event, codex["hooks"])
            claude = json.loads((root / "claude-code" / ".claude" / "settings.json").read_text())
            canonical_claude = json.loads((ROOT / "adapters" / "claude" / "settings.fragment.json").read_text())
            for event in canonical_claude["hooks"]:
                self.assertIn(event, claude["hooks"])
            self.assertEqual(
                (root / "opencode" / ".opencode" / "plugins" / "dsd-compaction.ts").read_text(),
                (ROOT / "adapters" / "opencode" / "dsd-compaction.ts").read_text(),
            )
            self.assertEqual(
                (root / "kilo" / ".kilo" / "plugin" / "dsd-compaction.ts").read_text(),
                (ROOT / "adapters" / "kilo" / "dsd-compaction.ts").read_text(),
            )

    def test_legacy_kilo_entrypoints_forward_to_canonical_installers(self):
        agents = self.run_cmd([PYTHON, str(ROOT / "contrib" / "kilo" / "install_agents.py"), "--help"])
        self.assertEqual(agents.returncode, 0, agents.stdout + agents.stderr)
        self.assertIn("install", agents.stdout.lower())
        compaction = self.run_cmd([PYTHON, str(ROOT / "contrib" / "kilo" / "install_compaction.py"), "--help"])
        self.assertEqual(compaction.returncode, 0, compaction.stdout + compaction.stderr)
        self.assertIn("--harness", compaction.stdout)

    def test_compaction_plugins_fail_closed_when_resume_instruction_generation_fails(self):
        kilo = (ROOT / "adapters" / "kilo" / "dsd-compaction.ts").read_text()
        opencode = (ROOT / "adapters" / "opencode" / "dsd-compaction.ts").read_text()
        self.assertIn("instruction.exitCode !== 0", kilo)
        self.assertIn("rehydrate.exitCode !== 0", opencode)
        self.assertIn("Do not assume continuity is safe", kilo)
        self.assertIn("Do not assume continuity is safe", opencode)

    def test_no_orphaned_kilo_implementation_or_stale_v15_config(self):
        config = (ROOT / "CONFIG.example.md").read_text()
        self.assertIn("kilo", config.lower())
        self.assertNotIn("reviewer resume when trustworthy/moderate", config)
        self.assertIn("Role changes start fresh sessions", config)
        self.assertFalse((ROOT / "contrib" / "kilo" / "dsd-compaction.ts").exists())
        self.assertFalse((ROOT / "contrib" / "kilo" / "agents").exists())
        self.assertTrue((ROOT / "KILO.md").is_file())
        self.assertTrue((ROOT / "adapters" / "kilo" / "dsd-compaction.ts").is_file())
        self.assertIn("compatibility wrapper", (ROOT / "contrib" / "kilo" / "README.md").read_text().lower())


if __name__ == "__main__":
    unittest.main()
