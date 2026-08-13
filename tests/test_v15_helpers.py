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
            task.write_text(f"# Task {task_id}\n## Allowed source changes\nNONE\n\n")
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



    def test_render_task_contract_uses_json_spec_and_freezes_revision(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); project=root/"project"; run=project/"DeepSeekAndDestroy"/"run"; run.mkdir(parents=True)
            plan=project/"PLAN.md"; plan.write_text("plan")
            spec=run/"spec.json"; spec.write_text(json.dumps({
                "run_root":str(run.resolve()),"phase_id":"p1","task_id":"U1","title":"Change one behavior","objective":"Behavior is correct",
                "authority":[str(plan.resolve())],"write_paths":["source.py"],"acceptance":["behavior is correct"],"verification":["python3 -m test"]
            }))
            cp=self.run_cmd([PYTHON,str(ROOT/"scripts"/"render_task_contract.py"),"--spec",str(spec)])
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr); data=json.loads(cp.stdout); self.assertEqual(data["revision"],1)
            output=Path(data["path"]); text=output.read_text(); self.assertIn("# Task U1 — Change one behavior",text); self.assertIn("AC-001",text); self.assertIn("`source.py`",text); self.assertNotIn("Evidence Clerk Checks",text)
            cp=self.run_cmd([PYTHON,str(ROOT/"scripts"/"render_task_contract.py"),"--spec",str(spec)])
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr); self.assertEqual(json.loads(cp.stdout)["revision"],2)
            self.assertTrue((output.parent/"r0002.md").is_file())

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
            self.assertIn("Launcher working directory is PROJECT ROOT", rules_text)
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
            self.assertNotIn("PROOF-PATTERNS.md", text)
            self.assertNotIn("NO SHORTCUTS", text)



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
            self.assertIn("DSD_WORKER_REPORT_PLACEHOLDER_V1", report.read_text())

            wait = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "wait_worker.py"),
                "--event-dir", str(event_dir), "--timeout", "0.5",
            ])
            self.assertEqual(wait.returncode, 0)
            self.assertEqual(json.loads(wait.stdout)["status"], "completed")

    def test_check_state_does_not_encode_zero_change_or_routing_heuristics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, worker_rules = self.make_worker_rules_state(root)
            state = {
                "execution_status": "active", "next_action": "re-scope U1",
                "worker_rules": worker_rules, "worker_runtime": {"harness": "opencode-cli"},
                "context_checkpoint": {"status": "none"},
                "phases": {"p1": {"status": "in-progress", "gate_barrier": {"status": "OPEN"}, "tasks": {
                    "U1": {"status": "prepared", "zero_intended_change_streak": 99,
                           "decomposition_required": True, "next_role": "fixer"}
                }}},
            }
            path = root / "state.json"; path.write_text(json.dumps(state))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(path)])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

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
                    "status": "prepared",
                    "current_contract": {"revision": 1, "path": str(contract.resolve()), "sha256": frozen},
                }}}},
            }
            state.write_text(json.dumps(payload))
            clean = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state)])
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            contract.write_text("# Contract r1 MUTATED\nAC-001\n")
            bad = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state)])
            self.assertEqual(bad.returncode, 1)
            self.assertIn("current_contract changed after binding", bad.stdout)

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
            self.assertIn("orchestrator_wait still active after terminal event", stale.stdout)

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
            self.assertIsNone(terminal["terminal_scope_error"])
            scope_binding = terminal["terminal_scope"]
            self.assertTrue(Path(scope_binding["path"]).is_file())
            self.assertEqual(hashlib.sha256(Path(scope_binding["path"]).read_bytes()).hexdigest(), scope_binding["sha256"])




    def test_native_finalize_binds_frozen_scope_into_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir()
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            prompt = run / "prompt.txt"; prompt.write_text("Native task")
            scope = run / "scope-baseline.json"; scope.write_text(json.dumps({
                "format": "deepseek-and-destroy-scope-snapshot-v4", "project_root": str(project.resolve()),
                "captured_at": "2026-08-13T00:00:00+00:00", "inventory_mode": "paths",
                "exclude_prefixes": [], "extra_inventory_specs": [], "entries": {}
            }) + "\n")
            task, rules = self.make_launch_authority(run, "U4")
            event = run / "native-event"; report = event / "report.md"; log = event / "worker.log"
            reserve = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "native_worker_attempt.py"), "reserve",
                "--harness", "kilo", "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--task-id", "U4", "--role", "reviewer", "--attempt", "1",
                "--prompt-file", str(prompt.resolve()), "--task-contract", str(task.resolve()),
                "--worker-rules", str(rules.resolve()), "--scope-baseline", str(scope.resolve()),
                "--report", str(report.resolve()), "--event-dir", str(event.resolve()), "--log", str(log.resolve()),
            ])
            self.assertEqual(reserve.returncode, 0, reserve.stdout + reserve.stderr)
            finalize = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "native_worker_attempt.py"), "finalize",
                "--event-dir", str(event.resolve()), "--status", "completed",
            ])
            self.assertEqual(finalize.returncode, 0, finalize.stdout + finalize.stderr)
            terminal = json.loads((event / "terminal.json").read_text())
            self.assertIsNone(terminal["terminal_scope_error"])
            frozen = Path(terminal["terminal_scope"]["path"])
            self.assertTrue(frozen.is_file())
            self.assertEqual(hashlib.sha256(frozen.read_bytes()).hexdigest(), terminal["terminal_scope"]["sha256"])

    def test_check_state_requires_next_action_not_next_role(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, worker_rules = self.make_worker_rules_state(root)
            state = {"execution_status":"active","next_action":"launch fresh reviewer",
                     "worker_rules":worker_rules,"worker_runtime":{"harness":"opencode-cli"},
                     "context_checkpoint":{"status":"none"},
                     "phases":{"p1":{"status":"in-progress","gate_barrier":{"status":"OPEN"},"tasks":{"U1":{"status":"prepared"}}}}}
            path=root/"state.json"; path.write_text(json.dumps(state))
            cp=self.run_cmd([PYTHON,str(ROOT/"scripts"/"check_state.py"),str(path)])
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
            state.pop("next_action"); path.write_text(json.dumps(state))
            cp=self.run_cmd([PYTHON,str(ROOT/"scripts"/"check_state.py"),str(path)])
            self.assertEqual(cp.returncode,1); self.assertIn("active run requires next_action",cp.stdout)

    def test_dsd_attempt_minimum_hop_flow_implementer_to_reviewer_direct_accept(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); project=root/"project"; run=project/"DeepSeekAndDestroy"/"plans"/"p"/"runs"/"r1"
            contract=run/"phases"/"p1"/"U1"/"contracts"/"r0001.md"; contract.parent.mkdir(parents=True); (root/"bin").mkdir(); (root/"external").mkdir()
            self.run_cmd(["git","init"],cwd=project); self.run_cmd(["git","config","user.email","dsd@test.invalid"],cwd=project); self.run_cmd(["git","config","user.name","DSD Test"],cwd=project)
            (project/"source.py").write_text("VALUE = 1\n"); (project/"PLAN.md").write_text("plan\n"); self.run_cmd(["git","add","source.py","PLAN.md"],cwd=project); self.run_cmd(["git","commit","-m","base"],cwd=project)
            contract.write_text("# Task U1 — Set value\nContract revision: r0001\n\n## Objective\nSet value.\n\n## Allowed source changes\n- `source.py`\n\n## Acceptance criteria\n- AC-001 — VALUE equals 2.\n")
            prep=self.run_cmd([PYTHON,str(ROOT/"scripts"/"prepare_worker_rules.py"),"--project-root",str(project.resolve()),"--run-root",str(run.resolve()),"--plan",str((project/"PLAN.md").resolve())]); self.assertEqual(prep.returncode,0,prep.stdout+prep.stderr)
            state={"project_worktree":str(project.resolve()),"execution_status":"active","next_action":"launch implementer","worker_rules":json.loads(prep.stdout),"worker_runtime":{"harness":"opencode-cli","model":"opencode-go/deepseek-v4-flash","opencode":{"run_db":str((root/"external"/"workers.db").resolve())}},"phases":{"p1":{"status":"in-progress","gate_barrier":{"status":"OPEN","snapshot":None},"tasks":{"U1":{"status":"prepared","current_contract":{"revision":1,"path":str(contract.resolve()),"sha256":hashlib.sha256(contract.read_bytes()).hexdigest()}}}}}}
            (run/"state.json").write_text(json.dumps(state))
            fake=root/"bin"/"opencode"; fake.write_text(r"""#!/usr/bin/env python3
import pathlib,re,sys
args=sys.argv[1:]
if args[:2] == ['session','list']: print('[]'); raise SystemExit(0)
if not args or args[0] != 'run': raise SystemExit(2)
prompt=args[-1]; report=pathlib.Path(re.search(r'^Report: (.+)$',prompt,re.M).group(1).strip()); project=pathlib.Path(args[args.index('--dir')+1])
if 'DSD IMPLEMENTER' in prompt:
 (project/'source.py').write_text('VALUE = 2\n'); report.write_text('Implemented the requested behavior with direct evidence.\n')
elif 'DSD REVIEWER' in prompt:
 report.write_text('Independent natural-language review reached the production path and found no task-relevant defect.\n')
else: report.write_text('Completed.\n')
"""); fake.chmod(0o755)
            env=os.environ.copy(); env["PATH"]=str(root/"bin")+os.pathsep+env.get("PATH","")
            impl=self.run_cmd([PYTHON,str(ROOT/"scripts"/"dsd_attempt.py"),"launch","--run-root",str(run.resolve()),"--phase-id","p1","--task-id","U1","--role","implementer","--auto-flag="],env=env); self.assertEqual(impl.returncode,0,impl.stdout+impl.stderr)
            impl_event=Path(json.loads(impl.stdout)["event_dir"]); self.assertTrue((impl_event/"scope-baseline.json").is_file())
            g=self.run_cmd([PYTHON,str(ROOT/"scripts"/"dsd_attempt.py"),"gate","--run-root",str(run.resolve()),"--phase-id","p1","--task-id","U1"]); self.assertEqual(g.returncode,0,g.stdout+g.stderr); gdata=json.loads(g.stdout); self.assertTrue(gdata["integrity_ok"]); self.assertNotIn("report_surface",gdata)
            review=self.run_cmd([PYTHON,str(ROOT/"scripts"/"dsd_attempt.py"),"launch","--run-root",str(run.resolve()),"--phase-id","p1","--task-id","U1","--role","reviewer","--input",str(impl_event/"report.md"),"--auto-flag="],env=env); self.assertEqual(review.returncode,0,review.stdout+review.stderr)
            review_event=Path(json.loads(review.stdout)["event_dir"]); self.assertIn("SHA-256",(review_event/"launch-prompt.txt").read_text())
            rg=self.run_cmd([PYTHON,str(ROOT/"scripts"/"dsd_attempt.py"),"gate","--run-root",str(run.resolve()),"--phase-id","p1","--task-id","U1","--surface"]); self.assertEqual(rg.returncode,0,rg.stdout+rg.stderr); summary=json.loads(rg.stdout); self.assertTrue(summary["report_surface"]); self.assertNotIn("verdict",summary)
            # Parent can consume a clear bounded Reviewer surface directly: no Clerk call.
            acc=self.run_cmd([PYTHON,str(ROOT/"scripts"/"dsd_state.py"),"accept-task","--run-root",str(run.resolve()),"--phase-id","p1","--task-id","U1","--evidence-gate",str(review_event/"evidence-gate.json"),"--next-action","next task"]); self.assertEqual(acc.returncode,0,acc.stdout+acc.stderr)
            task=json.loads((run/"state.json").read_text())["phases"]["p1"]["tasks"]["U1"]; self.assertEqual(task["status"],"accepted"); self.assertEqual(task["accepted"]["semantic_report"]["path"],str(review_event/"report.md")); self.assertNotIn("last_verdict",task)

    def test_dsd_attempt_cleans_setup_artifacts_when_preflight_never_reserves(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
            task_root = run / "phases" / "p1" / "U1"; contract = task_root / "contracts" / "r0001.md"
            contract.parent.mkdir(parents=True)
            self.assertEqual(self.run_cmd(["git", "init"], cwd=project).returncode, 0)
            self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
            self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
            (project / "source.py").write_text("VALUE = 1\n"); (project / "PLAN.md").write_text("plan\n")
            self.run_cmd(["git", "add", "source.py", "PLAN.md"], cwd=project); self.run_cmd(["git", "commit", "-m", "base"], cwd=project)
            contract.write_text("# Task U1 — Inspect\nContract revision: r0001\n\n## Objective\nInspect.\n\n## Allowed source changes\nNONE\n\n## Acceptance criteria\n- AC-001 — source exists.\n")
            prep = self.run_cmd([PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"), "--project-root", str(project.resolve()), "--run-root", str(run.resolve()), "--plan", str((project / "PLAN.md").resolve())])
            self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr); rules = json.loads(prep.stdout)
            # Deliberately put the DB inside the project. dsd_attempt can derive/setup
            # the attempt, but run_worker must reject it before immutable reservation.
            bad_db = project / "bad-workers.db"
            state = {"project_worktree": str(project.resolve()), "execution_status": "active", "next_action": "launch", "worker_rules": rules, "worker_runtime": {"harness": "opencode-cli", "model": "x", "opencode": {"run_db": str(bad_db.resolve())}}, "phases": {"p1": {"status": "in-progress", "gate_barrier": {"status": "OPEN", "snapshot": None}, "tasks": {"U1": {"status": "prepared", "current_contract": {"revision": 1, "path": str(contract.resolve()), "sha256": hashlib.sha256(contract.read_bytes()).hexdigest()}}}}}}
            (run / "state.json").write_text(json.dumps(state))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch", "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1", "--role", "reviewer", "--auto-flag="])
            self.assertNotEqual(cp.returncode, 0)
            self.assertFalse((task_root / "attempts" / "reviewer-1").exists(), cp.stdout + cp.stderr)

    def test_dsd_state_named_transitions_replace_json_heredocs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"; run.mkdir(parents=True)
            (run / "state.json").write_text(json.dumps({"execution_status": "active", "next_action": "prepare", "phases": {}}))
            contract = run / "phases" / "p1" / "U1" / "contracts" / "r0001.md"; contract.parent.mkdir(parents=True)
            contract.write_text("# Task U1 — X\nContract revision: r0001\n\n## Objective\nX\n\n## Allowed source changes\nNONE\n\n## Acceptance criteria\n- AC-001 x\n")
            bound = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "bind-contract", "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1", "--contract", "phases/p1/U1/contracts/r0001.md", "--next-action", "launch reviewer"])
            self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)
            state = json.loads((run / "state.json").read_text())
            self.assertEqual(state["phases"]["p1"]["tasks"]["U1"]["current_contract"]["revision"], 1)
            self.assertEqual(state["next_action"], "launch reviewer")

            event = run / "phases" / "p1" / "U1" / "attempts" / "reviewer-1"; event.mkdir(parents=True)
            sha = hashlib.sha256(contract.read_bytes()).hexdigest()
            reservation = {"task_id": "U1", "role": "reviewer", "attempt": 1, "writes_project": False, "task_contract": str(contract.resolve()), "task_contract_sha256": sha, "reserved_at": "now"}
            reservation_path = event / "launch-reservation.json"; reservation_path.write_text(json.dumps(reservation))
            (event / "attempt.json").write_text(json.dumps({"started_at": "now", "worker_pid": 12345}))
            attempt = self.run_cmd([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "bind-attempt", "--run-root", str(run.resolve()), "--phase-id", "p1", "--task-id", "U1", "--event-dir", "phases/p1/U1/attempts/reviewer-1", "--next-action", "wait"])
            self.assertEqual(attempt.returncode, 0, attempt.stdout + attempt.stderr)
            state = json.loads((run / "state.json").read_text())
            self.assertEqual(state["phases"]["p1"]["tasks"]["U1"]["status"], "in-progress")
            self.assertEqual(state["next_action"], "wait")



if __name__ == "__main__":
    unittest.main()
