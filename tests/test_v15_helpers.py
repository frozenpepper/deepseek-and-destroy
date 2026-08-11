from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

PROTOCOL_NAMES = ('COMMON.md', 'PROOF-PATTERNS.md', 'roles/dsd-implementer/SKILL.md', 'roles/dsd-fixer/SKILL.md', 'roles/dsd-reviewer/SKILL.md', 'roles/dsd-verification/SKILL.md', 'roles/dsd-discovery/SKILL.md', 'roles/dsd-phase-surveyor/SKILL.md', 'roles/dsd-recovery/SKILL.md', 'roles/dsd-phase-auditor/SKILL.md', 'roles/dsd-evidence-clerk/SKILL.md')


class V15HelpersTest(unittest.TestCase):
    def run_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)

    def make_worker_rules_state(self, root: Path):
        revision_root = root / "worker-rules" / "r0001"
        rules = revision_root / "WORKER_RULES.md"
        rules.parent.mkdir(parents=True, exist_ok=True)
        if not rules.exists():
            rules.write_text("rules")
        protocol = revision_root / "protocol"
        protocol.mkdir(exist_ok=True)
        h = hashlib.sha256()
        for name in PROTOCOL_NAMES:
            path = protocol / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(name)
            h.update(name.encode("utf-8")); h.update(b"\0"); h.update(path.read_bytes()); h.update(b"\0")
        protocol_hashes = {name: hashlib.sha256((protocol / name).read_bytes()).hexdigest() for name in PROTOCOL_NAMES}
        state = {
            "revision": 1,
            "path": str(rules.resolve()),
            "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
            "protocol_dir": str(protocol.resolve()),
            "protocol_fingerprint": h.hexdigest(),
            "protocol": protocol_hashes,
        }
        manifest = revision_root / "MANIFEST.json"
        manifest.write_text(json.dumps({"format": "dsd-worker-rules-manifest-v2", **state}, indent=2, sort_keys=True) + "\n")
        state["manifest"] = str(manifest.resolve())
        state["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        return rules, state


    def make_terminal_event(self, run_root: Path, task: Path, report: Path, baseline: Path, role: str, *, task_id: str = "U1", log: Path | None = None, rules: Path | None = None) -> Path:
        run_root = run_root.resolve(); task = task.resolve(); report = report.resolve(); baseline = baseline.resolve()
        if rules is None:
            rules, _ = self.make_worker_rules_state(run_root)
        rules = rules.resolve()
        event_dir = run_root / ".test-attempts" / f"{role}-{report.stem}"
        event_dir.mkdir(parents=True, exist_ok=True)
        terminal = event_dir / "terminal.json"
        prompt = event_dir / "launch-prompt.txt"
        prompt.write_text("test launch prompt\n")
        data = {
            "format": "dsd-worker-terminal-v2",
            "status": "completed",
            "exit_code": 0,
            "task_id": task_id,
            "role": role,
            "report": str(report),
            "prompt_file": str(prompt.resolve()),
            "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
            "task_contract": str(task),
            "task_contract_sha256": hashlib.sha256(task.read_bytes()).hexdigest(),
            "worker_rules": str(rules),
            "worker_rules_sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
            "worker_rules_manifest": str((rules.parent / "MANIFEST.json").resolve()),
            "worker_rules_manifest_sha256": hashlib.sha256((rules.parent / "MANIFEST.json").read_bytes()).hexdigest(),
            "scope_baseline": str(baseline),
            "scope_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        }
        if log is not None:
            data["log"] = str(log.resolve())
        terminal.write_text(json.dumps(data))
        return terminal


    def make_clean_clerk_gate(self, root: Path, clerk: Path) -> Path:
        path = root / (clerk.stem + "-gate.json")
        path.write_text(json.dumps({
            "format": "dsd-evidence-gate-v2",
            "role": "evidence-clerk",
            "report": str(clerk.resolve()),
            "report_sha256": hashlib.sha256(clerk.read_bytes()).hexdigest(),
            "ok": True,
            "clerk_required": False,
            "errors": [],
        }))
        return path

    def make_launch_authority(self, run: Path, task_id: str = "U1"):
        run = run.resolve()
        task = run / f"{task_id}-contract.md"
        if not task.exists():
            task.write_text(f"# Task {task_id}\n## Allowed source changes\nNONE\n\n## Evidence Clerk Checks\nNONE\n")
        rules, _ = self.make_worker_rules_state(run)
        return task, rules

    def make_scope_baseline(self, root: Path):
        project = root / "scope-project"
        project.mkdir(exist_ok=True)
        if not (project / ".git").exists():
            self.assertEqual(self.run_cmd(["git", "init"], cwd=project).returncode, 0)
            self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
            self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
            (project / "base.txt").write_text("base\n")
            self.assertEqual(self.run_cmd(["git", "add", "base.txt"], cwd=project).returncode, 0)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
        baseline = root / "scope-baseline.json"
        cp = self.run_cmd([
            PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture",
            "--root", str(project.resolve()), "--output", str(baseline.resolve()),
            "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy",
        ])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return project, baseline




    def test_prepare_rules_manifest_detects_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            run = project / "DeepSeekAndDestroy" / "run"
            run.mkdir(parents=True)
            plan = project / "PLAN.md"
            plan.write_text("plan\n")
            cmd = [
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project.resolve()),
                "--run-root", str(run.resolve()),
                "--skill-root", str(ROOT.resolve()),
                "--plan", str(plan.resolve()),
                "--revision", "1",
            ]
            first = self.run_cmd(cmd)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            data = json.loads(first.stdout)
            manifest = Path(data["manifest"])
            self.assertTrue(manifest.is_file())
            reuse = self.run_cmd(cmd + ["--reuse-existing"])
            self.assertEqual(reuse.returncode, 0, reuse.stdout + reuse.stderr)
            core = run / "worker-rules" / "r0001" / "protocol" / "COMMON.md"
            core.write_text(core.read_text() + "\nTAMPER\n")
            tampered = self.run_cmd(cmd + ["--reuse-existing"])
            self.assertEqual(tampered.returncode, 2)
            self.assertIn("immutable worker-rules revision changed", tampered.stderr)

    def test_clerk_overlay_requires_matching_clean_clerk_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            report = root / "worker.md"
            clerk = root / "clerk.md"
            task.write_text("# Task U1\n## Allowed source changes\nNONE\n\n## Evidence Clerk Checks\n- P-001 provenance recheck\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: PASS
                Verification: PASS; total=1; passed=1; failed=0; skipped=0
                Task-relevant defects: NONE
                Clerk checks: REQUIRED P-001
            """))
            clerk.write_text("DSD_REPORT_STATUS: FINAL\nVerdict: CLEAN\nP-001 rederived.\n")
            self.make_terminal_event(root, task, report, baseline, "implementer")
            base = [
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task), "--report", str(report), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
            ]
            missing = self.run_cmd(base + ["--clerk-report", str(clerk), "--json"])
            self.assertEqual(missing.returncode, 2)
            self.assertIn("must be supplied together", missing.stderr)
            bad_gate = root / "bad-clerk-gate.json"
            bad_gate.write_text(json.dumps({
                "format": "dsd-evidence-gate-v2",
                "role": "evidence-clerk",
                "report": str((root / "other.md").resolve()),
                "report_sha256": hashlib.sha256(clerk.read_bytes()).hexdigest(),
                "ok": True,
                "clerk_required": False,
                "errors": [],
            }))
            mismatch = self.run_cmd(base + ["--clerk-report", str(clerk), "--clerk-gate", str(bad_gate), "--json"])
            self.assertEqual(mismatch.returncode, 1, mismatch.stdout + mismatch.stderr)
            payload = json.loads(mismatch.stdout)
            self.assertTrue(any("binding does not match" in e for e in payload["errors"]))

    def test_clean_clerk_gate_binds_exact_report_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            report = root / "worker.md"
            clerk = root / "clerk.md"
            task.write_text("# Task U1\n## Allowed source changes\nNONE\n\n## Evidence Clerk Checks\n- P-001 provenance recheck\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: PASS
                Verification: PASS; total=1; passed=1; failed=0; skipped=0
                Task-relevant defects: NONE
                Clerk checks: REQUIRED P-001
            """))
            clerk.write_text("DSD_REPORT_STATUS: FINAL\nVerdict: CLEAN\nP-001 rederived.\n")
            clerk_gate = self.make_clean_clerk_gate(root, clerk)
            clerk.write_text(clerk.read_text() + "mutated after gate\n")
            self.make_terminal_event(root, task, report, baseline, "implementer")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task), "--report", str(report), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                "--clerk-report", str(clerk), "--clerk-gate", str(clerk_gate), "--json",
            ])
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            payload = json.loads(cp.stdout)
            self.assertTrue(any("changed after its clean evidence gate" in e for e in payload["errors"]))

    def test_render_task_contract_uses_compact_slots_and_freezes_revision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            run = project / "DeepSeekAndDestroy" / "run"
            contracts = run / "phases" / "p1" / "U1" / "contracts"
            run.mkdir(parents=True)
            plan = project / "PLAN.md"; plan.write_text("plan")
            report = run / "phases" / "p1" / "U1" / "implementer-1.md"
            output = contracts / "r0001.md"
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_task_contract.py"),
                "--run-root", str(run.resolve()), "--task-id", "U1", "--revision", "1",
                "--output", str(output.resolve()), "--unit", "Change one behavior",
                "--objective", "Behavior is correct", "--task-output", "source.py behavior updated",
                "--risk", "Claim: stale path | Failure mode: old branch | Attack: execute new path | Discriminating evidence: new path wins",
                "--acceptance", "AC-001 behavior is correct",
                "--authority", str(plan.resolve()),
                "--expected-scope", "source.py", "--write-path", "source.py", "--verification", "python3 -m test",
            ])
            self.assertEqual(cp.returncode, 0, cp.stderr)
            data = json.loads(cp.stdout)
            self.assertEqual(data["revision"], 1)
            self.assertEqual(len(data["sha256"]), 64)
            text = output.read_text()
            self.assertIn("# Task U1 — Change one behavior", text)
            self.assertNotIn("## Unit", text)
            self.assertIn("AC-001 behavior is correct", text)
            self.assertIn("source.py behavior updated", text)
            self.assertNotIn("## Evidence Clerk Checks", text)
            self.assertNotIn("## Inputs", text)
            again = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_task_contract.py"),
                "--run-root", str(run.resolve()), "--task-id", "U1", "--revision", "1",
                "--output", str(output.resolve()), "--unit", "Different", "--objective", "Different",
            ])
            self.assertEqual(again.returncode, 2)
            self.assertIn("already exists", again.stderr)

    def test_prepare_rules_and_render_prompt_are_path_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            run = project / "DeepSeekAndDestroy" / "run"
            project.mkdir(parents=True)
            plan = project / "PLAN.md"
            agents = project / "AGENTS.md"
            task = run / "phases" / "p1" / "U1" / "task.md"
            report = task.parent / "review-1.md"
            plan.write_text("plan")
            agents.write_text("rules")
            task.parent.mkdir(parents=True)
            task.write_text("# Task U1\n## Objective\nX\n")

            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project), "--run-root", str(run),
                "--plan", str(plan), "--project-instruction", str(agents),
                "--rule", "Do not use heredocs in this environment.",
            ])
            self.assertEqual(cp.returncode, 0, cp.stderr)
            rule_info = json.loads(cp.stdout)
            rules = Path(rule_info["path"])
            self.assertTrue(rules.exists())
            rules_text = rules.read_text()
            self.assertIn("launcher fixes the worker working directory", rules_text)
            self.assertIn("Do not use heredocs in this environment.", rules_text)
            self.assertTrue((rules.parent / "protocol" / "roles" / "dsd-reviewer" / "SKILL.md").exists())
            rerun = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project), "--run-root", str(run),
                "--plan", str(plan), "--project-instruction", str(agents),
                "--revision", "1", "--reuse-existing",
            ])
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            mutate = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project), "--run-root", str(run),
                "--plan", str(plan), "--project-instruction", str(agents),
                "--rule", "new rule",
            ])
            self.assertEqual(mutate.returncode, 2)
            self.assertIn("immutable", mutate.stderr)

            prompt = run / "launch.txt"
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"),
                "--role", "reviewer", "--task-id", "U1", "--run-root", str(run),
                "--worker-rules", str(rules), "--task", str(task), "--report", str(report), "--output", str(prompt),
            ])
            self.assertEqual(cp.returncode, 0, cp.stderr)
            text = prompt.read_text()
            self.assertLess(len(text.split()), 120)
            self.assertIn(str(rules), text)
            self.assertNotIn("NO SHORTCUTS", text)

    def test_evidence_gate_flags_skeleton_as_clerk_not_substantive_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            report = root / "review.md"
            task.write_text("# Task U1\n## Acceptance criteria\n- AC-001 — works\n\n## Evidence Clerk Checks\nNONE\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: SKELETON
                Verdict: FAIL
                Verification: FAIL; total=1; passed=0; failed=1; skipped=0
                Task-relevant defects: UNKNOWN
                Clerk checks: REQUIRED RC-004 REPORT-SKELETON
            """))
            self.make_terminal_event(root, task, report, baseline, "reviewer")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task), "--report", str(report), "--role", "reviewer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 4, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertTrue(data["clerk_required"])
            self.assertFalse(data["ok"])
            self.assertTrue(any("SKELETON" in r for r in data["clerk_reasons"]))

    def test_evidence_gate_rejects_bad_verification_arithmetic_via_clerk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            report = root / "worker.md"
            task.write_text("# Task U1\n## Evidence Clerk Checks\nNONE\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: PASS
                Verification: PASS; total=17; passed=14; failed=2; skipped=0
                Task-relevant defects: NONE
                Clerk checks: NONE
            """))
            self.make_terminal_event(root, task, report, baseline, "implementer")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task), "--report", str(report), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 4)
            data = json.loads(cp.stdout)
            self.assertTrue(any("ARITHMETIC" in r for r in data["clerk_reasons"]))

    def test_run_worker_foreground_and_wait_terminal_event(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            bin_dir = root / "bin"
            project.mkdir()
            bin_dir.mkdir()
            fake = bin_dir / "opencode"
            fake.write_text(textwrap.dedent(r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time
args=sys.argv[1:]
db=pathlib.Path(os.environ["OPENCODE_DB"])
db.parent.mkdir(parents=True, exist_ok=True)
if args[:2] == ["session", "list"]:
    title_file=db.with_suffix(".title")
    title=title_file.read_text() if title_file.exists() else ""
    print(json.dumps([{"id":"ses_fake","title":title}]))
    raise SystemExit(0)
if args and args[0] == "run":
    title=args[args.index("--title")+1]
    db.with_suffix(".title").write_text(title)
    print("fake worker output")
    time.sleep(0.1)
    raise SystemExit(0)
raise SystemExit(2)
'''))
            fake.chmod(0o755)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            prompt = run / "prompt.txt"
            report = run / "report.md"
            event_dir = run / "event"
            log = event_dir / "worker.log"
            db = root / "external" / "workers.db"
            prompt.write_text("Do task")
            scope = run / "scope-baseline.json"; scope.write_text("{}\n")
            task, rules = self.make_launch_authority(run, "U1")
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "run_worker.py"),
                "--project-root", str(project), "--run-root", str(run), "--task-id", "U1", "--role", "implementer",
                "--prompt-file", str(prompt), "--task-contract", str(task), "--worker-rules", str(rules),
                "--scope-baseline", str(scope), "--report", str(report),
                "--event-dir", str(event_dir), "--log", str(log), "--db", str(db),
                "--auto-flag", "",
            ], env=env)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            terminal = json.loads((event_dir / "terminal.json").read_text())
            reservation_path = event_dir / "launch-reservation.json"
            reservation = json.loads(reservation_path.read_text())
            self.assertEqual(reservation["format"], "dsd-worker-launch-reservation-v2")
            self.assertEqual(terminal["format"], "dsd-worker-terminal-v3")
            self.assertEqual(terminal["launch_reservation"], str(reservation_path.resolve()))
            self.assertEqual(terminal["launch_reservation_sha256"], hashlib.sha256(reservation_path.read_bytes()).hexdigest())
            self.assertNotIn("task_contract_sha256", terminal)
            self.assertEqual(terminal["status"], "completed")
            self.assertEqual(terminal["session_id"], "ses_fake")
            self.assertIn("fake worker output", log.read_text())
            self.assertIn("DSD_REPORT_STATUS: SKELETON", report.read_text())

            wait = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "wait_worker.py"),
                "--event-dir", str(event_dir), "--timeout", "0.5",
            ])
            self.assertEqual(wait.returncode, 0)
            self.assertEqual(json.loads(wait.stdout)["status"], "completed")

    def test_check_state_blocks_third_zero_change_mutating_launch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rules, worker_rules = self.make_worker_rules_state(root)
            taskfile = root / "task.md"
            taskfile.write_text("task")
            state = {
                "execution_status": "active",
                "next_action": "launch U1 implementer",
                "worker_rules": worker_rules,
                "worker_runtime": {"harness": "opencode-cli"},
                "context_checkpoint": {"status": "none"},
                "phases": {"p1": {"status": "in-progress", "gate_barrier": {"status": "OPEN"}, "tasks": {
                    "U1": {
                        "status": "prepared", "task_path": str(taskfile), "transport_attempts": 2,
                        "zero_intended_change_streak": 2, "decomposition_required": True,
                        "current_attempt": {"role": "implementer"},
                    }
                }}},
            }
            path = root / "state.json"
            path.write_text(json.dumps(state))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(path)])
            self.assertEqual(cp.returncode, 1)
            self.assertIn("forbids another mutating launch", cp.stdout)

    def test_run_worker_detached_waits_without_model_polling(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            bin_dir = root / "bin"
            project.mkdir(); bin_dir.mkdir()
            fake = bin_dir / "opencode"
            fake.write_text(textwrap.dedent(r"""#!/usr/bin/env python3
import json, os, pathlib, sys, time
args=sys.argv[1:]
db=pathlib.Path(os.environ["OPENCODE_DB"]); db.parent.mkdir(parents=True, exist_ok=True)
if args[:2] == ["session", "list"]:
    title_file=db.with_suffix(".title"); title=title_file.read_text() if title_file.exists() else ""
    print(json.dumps([{"id":"ses_detached","title":title}])); raise SystemExit(0)
if args and args[0] == "run":
    title=args[args.index("--title")+1]; db.with_suffix(".title").write_text(title)
    time.sleep(0.25); print("done"); raise SystemExit(0)
raise SystemExit(2)
"""))
            fake.chmod(0o755)
            run=project/"DeepSeekAndDestroy"/"run"; run.mkdir(parents=True)
            prompt=run/"prompt.txt"; prompt.write_text("Do it")
            scope=run/"scope-baseline.json"; scope.write_text("{}\n")
            report=run/"report.md"; event=run/"event"; log=event/"worker.log"; db=root/"external"/"workers.db"
            task, rules = self.make_launch_authority(run, "U2")
            env=os.environ.copy(); env["PATH"]=str(bin_dir)+os.pathsep+env.get("PATH","")
            launch=self.run_cmd([
                PYTHON, str(ROOT/"scripts"/"run_worker.py"), "--project-root",str(project),
                "--run-root",str(run),"--task-id","U2","--role","reviewer","--prompt-file",str(prompt),
                "--task-contract",str(task),"--worker-rules",str(rules),"--scope-baseline",str(scope),"--report",str(report),"--event-dir",str(event),"--log",str(log),"--db",str(db),
                "--auto-flag","","--detach"], env=env)
            self.assertEqual(launch.returncode,0,launch.stderr)
            self.assertFalse((event/"terminal.json").exists())
            wait=self.run_cmd([PYTHON,str(ROOT/"scripts"/"wait_worker.py"),"--event-dir",str(event),"--timeout","5"],env=env)
            self.assertEqual(wait.returncode,0,wait.stdout+wait.stderr)
            data=json.loads((event/"terminal.json").read_text())
            self.assertEqual(data["session_id"],"ses_detached")



    def test_check_state_detects_mutated_frozen_contract(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = root / "contracts" / "r0001.md"
            contract.parent.mkdir()
            contract.write_text("# Contract r1\nAC-001\n")
            frozen = hashlib.sha256(contract.read_bytes()).hexdigest()
            state = root / "state.json"
            payload = {
                "execution_status": "active",
                "next_action": "launch reviewer",
                "phases": {"p1": {"status": "in-progress", "tasks": {"U1": {
                    "status": "accepted",
                    "current_contract": {"revision": 1, "path": str(contract.resolve()), "sha256": frozen},
                }}}},
            }
            state.write_text(json.dumps(payload))
            clean = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state)])
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            contract.write_text("# Contract r1 MUTATED\nAC-001\n")
            bad = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state)])
            self.assertEqual(bad.returncode, 1)
            self.assertIn("current_contract hash changed after freeze", bad.stdout)

    def test_check_state_allows_active_host_wait_and_rejects_stale_terminal_wait(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            terminal = root / "attempt" / "terminal.json"
            state = root / "state.json"
            payload = {
                "execution_status": "active",
                "next_action": "wait for worker terminal event",
                "orchestrator_wait": {
                    "active": True,
                    "kind": "claude-async-rewake",
                    "terminal_event": str(terminal.resolve()),
                    "monitor_pid": os.getpid(),
                },
                "phases": {},
            }
            state.write_text(json.dumps(payload))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state), "--for-turn-exit"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

            terminal.parent.mkdir(parents=True)
            terminal.write_text(json.dumps({"status": "completed"}))
            stale = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state), "--for-turn-exit"])
            self.assertEqual(stale.returncode, 1)
            self.assertIn("terminal_event already exists", stale.stdout)

    def test_git_worktree_snapshot_detects_unexpected_file_but_excludes_dsd_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            project.mkdir()
            self.assertEqual(self.run_cmd(["git","init"], cwd=project).returncode, 0)
            self.run_cmd(["git","config","user.email","dsd@test.invalid"], cwd=project)
            self.run_cmd(["git","config","user.name","DSD Test"], cwd=project)
            (project / "source.py").write_text("x=1\n")
            self.assertEqual(self.run_cmd(["git","add","source.py"], cwd=project).returncode, 0)
            self.assertEqual(self.run_cmd(["git","commit","-m","base"], cwd=project).returncode, 0)
            run = project / "DeepSeekAndDestroy" / "run"
            run.mkdir(parents=True)
            baseline = run / "readonly-baseline.json"
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture",
                "--root", str(project), "--output", str(baseline), "--git-worktree",
                "--exclude-prefix", "DeepSeekAndDestroy",
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            (project / "unexpected.py").write_text("oops=True\n")
            (run / "review.md").write_text("allowed DSD evidence\n")
            diff = run / "readonly-diff.json"
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare",
                "--root", str(project), "--baseline", str(baseline), "--output", str(diff),
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(diff.read_text())
            changed = [entry["path"] for entry in data["changed"]]
            self.assertEqual(changed, ["unexpected.py"])

    def test_claude_rewake_ignores_normal_bash_and_wakes_on_dsd_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            terminal = project / "DeepSeekAndDestroy" / "run" / "event" / "terminal.json"
            terminal.parent.mkdir(parents=True)
            terminal.write_text(json.dumps({"status": "completed"}))
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = str(project)
            env["DSD_CLAUDE_REWAKE_TIMEOUT_SECONDS"] = "2"

            normal = self.run_cmd(
                [PYTHON, str(ROOT / "scripts" / "claude_worker_rewake.py")],
                input=json.dumps({"tool_name":"Bash","cwd":str(project),"tool_response":{"stdout":"hello"}}),
                env=env,
            )
            self.assertEqual(normal.returncode, 0)

            launched = json.dumps({"status":"launched","terminal_event":str(terminal)})
            wake = self.run_cmd(
                [PYTHON, str(ROOT / "scripts" / "claude_worker_rewake.py")],
                input=json.dumps({"tool_name":"Bash","cwd":str(project),"tool_response":{"stdout":launched}}),
                env=env,
            )
            self.assertEqual(wake.returncode, 2)
            self.assertIn(str(terminal), wake.stderr)
            self.assertIn("completed", wake.stderr)

    def test_claude_adapter_installs_async_rewake_hook(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            project.mkdir()
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "install_harness_adapter.py"),
                "--harness", "claude-code", "--project-root", str(project),
                "--skill-root", str(ROOT),
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            settings = json.loads((project / ".claude" / "settings.json").read_text())
            handlers = [
                h for group in settings["hooks"].get("PostToolUse", [])
                for h in group.get("hooks", [])
                if "claude_worker_rewake.py" in h.get("command", "")
            ]
            self.assertEqual(len(handlers), 1)
            self.assertTrue(handlers[0].get("asyncRewake"))
            self.assertTrue((project / "DeepSeekAndDestroy" / "tools" / "claude_worker_rewake.py").exists())
            self.assertTrue((project / "DeepSeekAndDestroy" / "tools" / "_rules_snapshot.py").exists())
            copied_check = project / "DeepSeekAndDestroy" / "tools" / "check_state.py"
            imported = self.run_cmd([PYTHON, str(copied_check), "--help"])
            self.assertEqual(imported.returncode, 0, imported.stdout + imported.stderr)
            # Idempotence: installing again must not duplicate the hook.
            again = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "install_harness_adapter.py"),
                "--harness", "claude-code", "--project-root", str(project),
                "--skill-root", str(ROOT),
            ])
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            settings2 = json.loads((project / ".claude" / "settings.json").read_text())
            handlers2 = [
                h for group in settings2["hooks"].get("PostToolUse", [])
                for h in group.get("hooks", [])
                if "claude_worker_rewake.py" in h.get("command", "")
            ]
            self.assertEqual(len(handlers2), 1)

    def test_run_worker_rejects_relative_db_before_detach(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            project.mkdir()
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            prompt = run / "prompt.txt"
            prompt.write_text("Do task")
            scope = run / "scope-baseline.json"; scope.write_text("{}\n")
            task, rules = self.make_launch_authority(run, "U1")
            event = run / "event"
            report = run / "report.md"
            log = event / "worker.log"
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "run_worker.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--task-id", "U1", "--role", "implementer",
                "--prompt-file", str(prompt.resolve()), "--task-contract", str(task.resolve()), "--worker-rules", str(rules.resolve()),
                "--scope-baseline", str(scope.resolve()), "--report", str(report.resolve()),
                "--event-dir", str(event.resolve()), "--log", str(log.resolve()),
                "--db", "relative-workers.db", "--detach",
            ])
            self.assertEqual(cp.returncode, 2)
            self.assertIn("db path must be absolute", cp.stderr)
            self.assertFalse(event.exists())

    def test_run_worker_resume_preserves_known_session_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            bin_dir = root / "bin"
            project.mkdir(); bin_dir.mkdir()
            fake = bin_dir / "opencode"
            fake.write_text(textwrap.dedent(r"""#!/usr/bin/env python3
import sys
args=sys.argv[1:]
if args and args[0] == "run":
    assert "--session" in args and args[args.index("--session")+1] == "ses_resume"
    print("resumed"); raise SystemExit(0)
raise SystemExit(2)
"""))
            fake.chmod(0o755)
            run=project/"DeepSeekAndDestroy"/"run"; run.mkdir(parents=True)
            prompt=run/"prompt.txt"; prompt.write_text("Continue")
            scope=run/"scope-baseline.json"; scope.write_text("{}\n")
            report=run/"report.md"; event=run/"event"; log=event/"worker.log"; db=root/"external"/"workers.db"
            task, rules = self.make_launch_authority(run, "U3")
            env=os.environ.copy(); env["PATH"]=str(bin_dir)+os.pathsep+env.get("PATH","")
            cp=self.run_cmd([
                PYTHON,str(ROOT/"scripts"/"run_worker.py"),"--project-root",str(project.resolve()),
                "--run-root",str(run.resolve()),"--task-id","U3","--role","fixer",
                "--prompt-file",str(prompt.resolve()),"--task-contract",str(task.resolve()),"--worker-rules",str(rules.resolve()),
                "--scope-baseline",str(scope.resolve()),"--report",str(report.resolve()),
                "--event-dir",str(event.resolve()),"--log",str(log.resolve()),"--db",str(db.resolve()),
                "--resume-session","ses_resume","--auto-flag",""
            ],env=env)
            self.assertEqual(cp.returncode,0,cp.stderr)
            terminal=json.loads((event/"terminal.json").read_text())
            self.assertEqual(terminal["session_id"],"ses_resume")

    def test_clean_clerk_satisfies_only_declared_checks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            report = root / "worker.md"
            clerk = root / "clerk.md"
            task.write_text("# Task U1\n## Evidence Clerk Checks\n- P-001 provenance: compare source to task-start baseline\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: PASS
                Verification: PASS; total=1; passed=1; failed=0; skipped=0
                Task-relevant defects: NONE
                Clerk checks: REQUIRED P-001
            """))
            clerk.write_text("DSD_REPORT_STATUS: FINAL\nVerdict: CLEAN\nP-001 rederived from task-start baseline.\n")
            clerk_gate = self.make_clean_clerk_gate(root, clerk)
            self.make_terminal_event(root, task, report, baseline, "implementer")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task), "--report", str(report), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                "--clerk-report", str(clerk), "--clerk-gate", str(clerk_gate), "--json",
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["clerk_reconciliation"]["verdict"], "CLEAN")

    def test_clean_clerk_can_reconcile_verification_arithmetic_without_rewriting_final(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            report = root / "worker.md"
            clerk = root / "clerk.md"
            task.write_text("# Task U1\n## Evidence Clerk Checks\nNONE\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: PASS
                Verification: PASS; total=17; passed=14; failed=2; skipped=0
                Task-relevant defects: NONE
                Clerk checks: NONE
            """))
            clerk.write_text("DSD_REPORT_STATUS: FINAL\nVerdict: CLEAN\nVERIFICATION-ARITHMETIC: actual terminal counts total=16, passed=14, failed=2.\n")
            clerk_gate = self.make_clean_clerk_gate(root, clerk)
            self.make_terminal_event(root, task, report, baseline, "implementer")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task), "--report", str(report), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                "--clerk-report", str(clerk), "--clerk-gate", str(clerk_gate), "--json",
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertTrue(data["ok"])
            self.assertIn("VERIFICATION-ARITHMETIC", "\n".join(data["declared_clerk_reasons"]))

    def test_clean_clerk_normalizes_substantive_nonfinal_report_but_not_missing_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            report = root / "worker.md"
            clerk = root / "clerk.md"
            task.write_text("# Task U1\n## Evidence Clerk Checks\nNONE\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: DRAFT
                Verdict: PASS
                Verification: PASS; total=1; passed=1; failed=0; skipped=0
                Task-relevant defects: NONE
                Clerk checks: NONE
                Evidence: implementation and verification evidence are present.
            """))
            clerk.write_text("DSD_REPORT_STATUS: FINAL\nVerdict: CLEAN\nRC-002 confirmed: substantive same-attempt report; finality marker alone was noncanonical.\n")
            clerk_gate = self.make_clean_clerk_gate(root, clerk)
            self.make_terminal_event(root, task, report, baseline, "implementer")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task), "--report", str(report), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                "--clerk-report", str(clerk), "--clerk-gate", str(clerk_gate), "--json",
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["clerk_reconciliation"]["normalizes_clerical_representation"])

    def test_decomposition_guard_requires_explicit_next_role(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rules, worker_rules = self.make_worker_rules_state(root)
            taskfile = root / "task.md"
            taskfile.write_text("task")
            state = {
                "execution_status": "active",
                "next_action": "re-decompose U1",
                "worker_rules": worker_rules,
                "worker_runtime": {"harness": "opencode-cli"},
                "context_checkpoint": {"status": "none"},
                "phases": {"p1": {"status": "in-progress", "gate_barrier": {"status": "OPEN"}, "tasks": {
                    "U1": {
                        "status": "prepared", "task_path": str(taskfile), "transport_attempts": 2,
                        "zero_intended_change_streak": 2, "decomposition_required": True,
                    }
                }}},
            }
            path = root / "state.json"
            path.write_text(json.dumps(state))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(path)])
            self.assertEqual(cp.returncode, 1)
            self.assertIn("requires explicit next_role", cp.stdout)

    def test_clean_reviewer_evidence_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); project, baseline = self.make_scope_baseline(root); task=root/"task.md"; review=root/"review.md"
            task.write_text("# Task U1\n## Acceptance criteria\n- AC-001 — works\n\n## Evidence Clerk Checks\nNONE\n")
            review.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: PASS
                Goal/result: works
                Changed/read-only: read-only
                Verification: PASS; total=1; passed=1; failed=0; skipped=0
                Proof: 1/1
                Scope/preservation: CLEAN
                Task-relevant defects: NONE
                Major log: NONE
                Clerk checks: NONE
                Evidence: e

                ## Proof Matrix
                | AC | Mechanism reached | Positive | Negative | Dimensions exercised | Counterexample defeated | Result |
                |---|---|---|---|---|---|---|
                | AC-001 | YES: production path | PASS | N/A | normal | YES: wrong branch fails | PASS |
                VERDICT: PASS
            """))
            self.make_terminal_event(root, task, review, baseline, "reviewer")
            cp=self.run_cmd([PYTHON,str(ROOT/"scripts"/"evidence_gate.py"),"--run-root",str(root.resolve()),"--task",str(task),"--report",str(review),"--role","reviewer","--project-root",str(project.resolve()),"--scope-baseline",str(baseline.resolve()),"--require-review-pass","--json"])
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
            self.assertTrue(json.loads(cp.stdout)["ok"])

    def test_end_to_end_fake_opencode_implement_review_acceptance_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            bin_dir = root / "bin"
            project.mkdir(); bin_dir.mkdir()
            self.run_cmd(["git", "init"], cwd=project)
            self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
            self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
            source = project / "source.py"
            source.write_text("VALUE = 1\n")
            plan = project / "PLAN.md"; plan.write_text("Make VALUE equal 2.\n")
            agents = project / "AGENTS.md"; agents.write_text("Preserve simple architecture.\n")
            self.run_cmd(["git", "add", "source.py", "PLAN.md", "AGENTS.md"], cwd=project)
            self.run_cmd(["git", "commit", "-m", "base"], cwd=project)

            run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"
            contract = run / "phases" / "p1" / "U1" / "contracts" / "r0001.md"
            contract.parent.mkdir(parents=True)
            contract.write_text(textwrap.dedent(f"""\
                # Task U1 — Contract r1
                Contract revision: 1
                ## Unit
                Change VALUE from 1 to 2.
                ## Objective
                VALUE is 2.
                ## Authority
                Plan: {plan}
                Project instructions: {agents}
                ## Inputs
                Prior report/review/gate/findings: NONE
                ## Scope
                Expected: source.py
                Excluded: everything else
                Mechanical facts: NONE
                ## Allowed source changes
                - `source.py`
                ## Risk hypotheses
                1. Claim: wrong value survives | Failure mode: source remains 1 | Attack: import source | Discriminating evidence: VALUE == 2
                ## Acceptance criteria
                - AC-001 — source.VALUE equals 2
                ## Proof Obligations
                | AC | Mechanism | Paths | Required dimensions | Counterexample to defeat | Patterns |
                |---|---|---|---|---|---|
                | AC-001 | direct module constant | positive | exact value | VALUE remains 1 | NONE |
                ## Verification
                - python3 -c "import source; assert source.VALUE == 2"
                ## Evidence Clerk Checks
                NONE
                ## Deliverables
                Task outputs:
                - source.py updated
                Role report: ASSIGNED BY IMMUTABLE LAUNCH HANDOFF
            """))

            prep = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--plan", str(plan.resolve()), "--project-instruction", str(agents.resolve()),
            ])
            self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr)
            rules_path = Path(json.loads(prep.stdout)["path"])

            fake = bin_dir / "opencode"
            fake.write_text(textwrap.dedent(r'''#!/usr/bin/env python3
import json, pathlib, re, sys
args=sys.argv[1:]
if args[:2] == ["session", "list"]:
    print("[]"); raise SystemExit(0)
if not args or args[0] != "run": raise SystemExit(2)
prompt=args[-1]
report=pathlib.Path(re.search(r"^Report: (.+)$", prompt, re.M).group(1).strip())
project=pathlib.Path(args[args.index("--dir")+1])
role=re.search(r"^DSD (.+?) for ", prompt).group(1).strip()
if role == "IMPLEMENTER":
    (project/"source.py").write_text("VALUE = 2\n")
    report.write_text("""## Decision Packet
DSD_REPORT_STATUS: FINAL
Verdict: PASS
Goal/result: VALUE set to 2
Changed/read-only: source.py
Verification: PASS; total=1; passed=1; failed=0; skipped=0; check=import
Proof: AC-001 implemented
Scope/preservation: CLEAN
Task-relevant defects: NONE
Major log: NONE
Clerk checks: NONE
Evidence: source.py
""")
elif role == "REVIEWER":
    report.write_text("""## Decision Packet
DSD_REPORT_STATUS: FINAL
Verdict: PASS
Goal/result: AC-001 independently proven
Changed/read-only: read-only source
Verification: PASS; total=1; passed=1; failed=0; skipped=0; check=import
Proof: AC-001 covered
Scope/preservation: CLEAN
Task-relevant defects: NONE
Major log: NONE
Clerk checks: NONE
Evidence: source.py

## Proof Matrix
| AC | Mechanism reached | Positive | Negative | Dimensions exercised | Counterexample defeated | Result |
|---|---|---|---|---|---|---|
| AC-001 | YES: imported source.VALUE | PASS | N/A | exact value=2 | YES: VALUE=1 would fail assertion | PASS |
""")
else:
    raise SystemExit(3)
raise SystemExit(0)
'''))
            fake.chmod(0o755)
            env = os.environ.copy(); env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
            db = root / "external" / "workers.db"

            # Implementer
            impl_report = contract.parent.parent / "implementer-report-1.md"
            impl_attempt = contract.parent.parent / "attempts" / "implementer-1"
            impl_baseline = contract.parent.parent / "implementer-1-scope-baseline.json"
            cap_impl = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project.resolve()),
                "--output", str(impl_baseline.resolve()), "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy",
            ])
            self.assertEqual(cap_impl.returncode, 0, cap_impl.stdout + cap_impl.stderr)
            impl_prompt = impl_attempt / "launch-prompt.txt"
            render = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"), "--role", "implementer",
                "--task-id", "U1", "--run-root", str(run.resolve()), "--worker-rules", str(rules_path),
                "--task", str(contract.resolve()), "--report", str(impl_report.resolve()), "--output", str(impl_prompt.resolve()),
            ])
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            run_impl = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "run_worker.py"), "--project-root", str(project.resolve()),
                "--run-root", str(run.resolve()), "--task-id", "U1", "--role", "implementer",
                "--prompt-file", str(impl_prompt.resolve()), "--task-contract", str(contract.resolve()), "--worker-rules", str(rules_path.resolve()),
                "--scope-baseline", str(impl_baseline.resolve()), "--report", str(impl_report.resolve()),
                "--event-dir", str(impl_attempt.resolve()), "--log", str((impl_attempt/"worker.log").resolve()),
                "--db", str(db.resolve()), "--auto-flag", "",
            ], env=env)
            self.assertEqual(run_impl.returncode, 0, run_impl.stdout + run_impl.stderr)
            self.assertEqual(json.loads((impl_attempt/"terminal.json").read_text())["status"], "completed")
            gate_impl = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()),
                "--task", str(contract.resolve()), "--report", str(impl_report.resolve()), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(impl_baseline.resolve()), "--json",
            ])
            self.assertEqual(gate_impl.returncode, 0, gate_impl.stdout + gate_impl.stderr)
            self.assertEqual(source.read_text(), "VALUE = 2\n")

            # Reviewer: freeze full source tree excluding DSD and prove it remains read-only.
            review_report = contract.parent.parent / "review-1.md"
            review_attempt = contract.parent.parent / "attempts" / "reviewer-1"
            review_baseline = contract.parent.parent / "reviewer-1-scope-baseline.json"
            cap = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project.resolve()),
                "--output", str(review_baseline.resolve()), "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy",
            ])
            self.assertEqual(cap.returncode, 0, cap.stdout + cap.stderr)
            review_prompt = review_attempt / "launch-prompt.txt"
            render2 = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"), "--role", "reviewer",
                "--task-id", "U1", "--run-root", str(run.resolve()), "--worker-rules", str(rules_path),
                "--task", str(contract.resolve()), "--report", str(review_report.resolve()), "--output", str(review_prompt.resolve()),
            ])
            self.assertEqual(render2.returncode, 0, render2.stdout + render2.stderr)
            run_review = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "run_worker.py"), "--project-root", str(project.resolve()),
                "--run-root", str(run.resolve()), "--task-id", "U1", "--role", "reviewer",
                "--prompt-file", str(review_prompt.resolve()), "--task-contract", str(contract.resolve()), "--worker-rules", str(rules_path.resolve()),
                "--scope-baseline", str(review_baseline.resolve()), "--report", str(review_report.resolve()),
                "--event-dir", str(review_attempt.resolve()), "--log", str((review_attempt/"worker.log").resolve()),
                "--db", str(db.resolve()), "--auto-flag", "",
            ], env=env)
            self.assertEqual(run_review.returncode, 0, run_review.stdout + run_review.stderr)
            review_diff = review_attempt / "readonly-diff.json"
            gate_review = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()),
                "--task", str(contract.resolve()), "--report", str(review_report.resolve()), "--role", "reviewer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(review_baseline.resolve()),
                "--scope-output", str(review_diff.resolve()), "--require-review-pass", "--json",
            ])
            self.assertEqual(gate_review.returncode, 0, gate_review.stdout + gate_review.stderr)
            self.assertTrue(json.loads(gate_review.stdout)["ok"])
            self.assertEqual(json.loads(review_diff.read_text())["changed"], [])

    def test_evidence_gate_uses_role_terminal_vocabulary_and_derives_fast_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "contract.md"
            report = root / "report.md"
            task.write_text("# Contract\n## Evidence Clerk Checks\nNONE\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: FIXED
                Verification: PASS; total=1; passed=1; failed=0; skipped=0
                Task-relevant defects: NONE
                Clerk checks: NONE
                FAST-PATH ELIGIBLE: YES — ignored legacy worker prose
            """))
            self.make_terminal_event(root, task, report, baseline, "implementer")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task.resolve()),
                "--report", str(report.resolve()), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertTrue(any("invalid implementer terminal verdict" in e for e in data["errors"]))
            self.assertFalse(data["fast_path_eligible"])
            self.assertFalse(any("FAST-PATH" in e for e in data["errors"]))

    def test_evidence_clerk_uses_single_role_verdict_vocabulary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "contract.md"
            report = root / "clerk.md"
            task.write_text("# Clerk Contract\n## Evidence Clerk Checks\nNONE\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: PASS
                Verification: PASS
                Task-relevant defects: NONE
                Clerk checks: NONE
            """))
            self.make_terminal_event(root, task, report, baseline, "evidence-clerk", task_id="C1")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task.resolve()),
                "--report", str(report.resolve()), "--role", "evidence-clerk",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            self.assertTrue(any("invalid evidence-clerk terminal verdict" in e for e in json.loads(cp.stdout)["errors"]))


    def test_decision_packet_extracts_bounded_surface_from_noncanonical_report(self):
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "report.md"
            report.write_text(textwrap.dedent("""
                # Worker notes
                Investigated the production path in depth.
                Verdict: PASS
                Verification: PASS; 8 checks passed
                Task-relevant defects: NONE
                Evidence: logs/evidence.md
                More detailed explanation that should not force a full premium reread.
            """))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "decision_packet.py"), str(report.resolve()), "--max-lines", "8"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertIn("Decision Surface (noncanonical report)", cp.stdout)
            self.assertIn("Verdict: PASS", cp.stdout)
            self.assertIn("Evidence: logs/evidence.md", cp.stdout)


    def test_review_contract_allows_noncanonical_ac_evidence_but_not_unaccounted_ac(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task = root / "task.md"
            review = root / "review.md"
            task.write_text("# Task\n## Acceptance criteria\n- AC-001 first behavior\n- AC-002 second behavior\n")
            review.write_text(textwrap.dedent("""
                # Review
                Verdict: PASS
                Task-relevant defects: NONE
                AC-001 — production path reached; positive and negative evidence recorded.
                AC-002 — restart path reached; counterexample defeated.
            """))
            normal = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_review_contract.py"), "--task", str(task), "--review", str(review), "--require-pass", "--json"])
            self.assertEqual(normal.returncode, 4, normal.stdout + normal.stderr)
            payload = json.loads(normal.stdout)
            self.assertTrue(payload["semantic_ok"])
            self.assertTrue(payload["normalization_required"])

            review.write_text(textwrap.dedent("""
                # Review
                Verdict: PASS
                Task-relevant defects: NONE
                AC-001 — production path reached; positive and negative evidence recorded.
            """))
            missing = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_review_contract.py"), "--task", str(task), "--review", str(review), "--require-pass", "--json"])
            self.assertEqual(missing.returncode, 1, missing.stdout + missing.stderr)
            self.assertTrue(any("AC-002" in e for e in json.loads(missing.stdout)["errors"]))

    def test_clean_clerk_cannot_waive_untouched_v15_launcher_skeleton(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"
            task.write_text("# Task U1\n## Allowed source changes\nNONE\n## Evidence Clerk Checks\nNONE\n")
            rules, _ = self.make_worker_rules_state(root)
            event = root / "attempt"; event.mkdir()
            prompt = event / "launch-prompt.txt"; prompt.write_text("prompt\n")
            report = root / "worker.md"
            log = event / "worker.log"; log.write_text("worker exited without a report\n")
            skeleton = "\n".join([
                "## Decision Packet", "DSD_REPORT_STATUS: SKELETON", "Verdict: BLOCKED",
                "Goal/result: worker has not finalized this report", "Verification: UNKNOWN",
                "Task-relevant defects: UNKNOWN", "Clerk checks: REQUIRED RC-004 REPORT-SKELETON",
                f"Evidence: {event}", "",
            ])
            report.write_text(skeleton)
            manifest = rules.parent / "MANIFEST.json"
            reservation = event / "launch-reservation.json"
            reservation.write_text(json.dumps({
                "format": "dsd-worker-launch-reservation-v2", "task_id": "U1", "role": "implementer", "attempt": 1,
                "report": str(report.resolve()), "log": str(log.resolve()),
                "report_skeleton_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "prompt_file": str(prompt.resolve()), "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                "task_contract": str(task.resolve()), "task_contract_sha256": hashlib.sha256(task.read_bytes()).hexdigest(),
                "worker_rules": str(rules.resolve()), "worker_rules_sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
                "worker_rules_manifest": str(manifest.resolve()), "worker_rules_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "scope_baseline": str(baseline.resolve()), "scope_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
            }, indent=2))
            terminal = event / "terminal.json"
            terminal.write_text(json.dumps({
                "format": "dsd-worker-terminal-v3", "status": "completed", "exit_code": 0,
                "task_id": "U1", "role": "implementer", "attempt": 1,
                "launch_reservation": str(reservation.resolve()),
                "launch_reservation_sha256": hashlib.sha256(reservation.read_bytes()).hexdigest(),
            }))
            clerk = root / "clerk.md"
            clerk.write_text("DSD_REPORT_STATUS: FINAL\nVerdict: CLEAN\nRC-004 inspected; no alternate report was recovered.\n")
            clerk_gate = self.make_clean_clerk_gate(root, clerk)
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(root.resolve()),
                "--task", str(task.resolve()), "--report", str(report.resolve()), "--terminal-event", str(terminal.resolve()),
                "--log", str(log.resolve()), "--role", "implementer", "--project-root", str(project.resolve()),
                "--scope-baseline", str(baseline.resolve()), "--clerk-report", str(clerk.resolve()), "--clerk-gate", str(clerk_gate.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 4, cp.stdout + cp.stderr)
            payload = json.loads(cp.stdout)
            self.assertTrue(payload["clerk_required"])
            self.assertTrue(any("RC-004 REPORT-UNCHANGED-SKELETON" in r for r in payload["report_recovery_reasons"]))
            self.assertFalse(payload["ok"])


    def test_clean_evidence_clerk_terminal_gate_is_nonrecursive_and_valid(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "clerk-task.md"
            report = root / "clerk.md"
            task.write_text("# Clerk task\n## Allowed source changes\nNONE\n## Evidence Clerk Checks\nNONE\n")
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Verdict: CLEAN
                Verification: PASS
                Task-relevant defects: NONE
                Clerk checks: NONE
                Evidence: exact assigned reconciliation completed.
            """))
            self.make_terminal_event(root, task, report, baseline, "evidence-clerk", task_id="C1")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(root.resolve()), "--task", str(task.resolve()),
                "--report", str(report.resolve()), "--role", "evidence-clerk",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            payload = json.loads(cp.stdout)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["clerk_required"])

    def test_worker_authored_role_and_task_are_readability_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, baseline = self.make_scope_baseline(root)
            task = root / "task.md"; task.write_text("# Task U1\n## Allowed source changes\nNONE\n## Evidence Clerk Checks\nNONE\n")
            report = root / "worker.md"
            report.write_text(textwrap.dedent("""
                ## Decision Packet
                DSD_REPORT_STATUS: FINAL
                Role: reviewer
                Task: WRONG
                Verdict: PASS
                Verification: PASS; total=1; passed=1; failed=0; skipped=0
                Task-relevant defects: NONE
                Clerk checks: NONE
            """))
            self.make_terminal_event(root, task, report, baseline, "implementer", task_id="U1")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(root.resolve()),
                "--task", str(task.resolve()), "--report", str(report.resolve()), "--role", "implementer",
                "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            payload = json.loads(cp.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue(any("Role mismatch" in w for w in payload["warnings"]))
            self.assertTrue(any("Task mismatch" in w for w in payload["warnings"]))




if __name__ == "__main__":
    unittest.main()
