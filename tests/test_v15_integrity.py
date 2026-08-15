from __future__ import annotations

import hashlib
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

PROTOCOL_NAMES = ('COMMON.md', 'PROOF-PATTERNS.md', 'roles/dsd-implementer/SKILL.md', 'roles/dsd-fixer/SKILL.md', 'roles/dsd-reviewer/SKILL.md', 'roles/dsd-verification/SKILL.md', 'roles/dsd-discovery/SKILL.md', 'roles/dsd-phase-surveyor/SKILL.md', 'roles/dsd-recovery/SKILL.md', 'roles/dsd-phase-auditor/SKILL.md', 'roles/dsd-evidence-clerk/SKILL.md')


class V15IntegrityTest(unittest.TestCase):
    def run_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)

    def init_git_project(self, root: Path) -> Path:
        project = root / "project"
        project.mkdir()
        self.assertEqual(self.run_cmd(["git", "init"], cwd=project).returncode, 0)
        self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
        self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
        return project

    def capture(self, project: Path, run: Path, name: str = "scope.json") -> Path:
        baseline = run / name
        cp = self.run_cmd([
            PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture",
            "--root", str(project.resolve()), "--output", str(baseline.resolve()),
            "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy",
        ])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return baseline


    def make_terminal_event(self, run: Path, task: Path, report: Path, baseline: Path, role: str, *, task_id: str = "U1") -> Path:
        revision = run / "worker-rules" / "r0001"
        revision.mkdir(parents=True, exist_ok=True)
        rules = revision / "WORKER_RULES.md"
        if not rules.exists():
            rules.write_text("rules\n")
        protocol = revision / "protocol"
        protocol.mkdir(exist_ok=True)
        h = hashlib.sha256()
        protocol_hashes = {}
        for name in PROTOCOL_NAMES:
            path = protocol / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(name + "\n")
            h.update(name.encode("utf-8")); h.update(b"\0"); h.update(path.read_bytes()); h.update(b"\0")
            protocol_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = revision / "MANIFEST.json"
        manifest.write_text(json.dumps({
            "format": "dsd-worker-rules-manifest-v2",
            "revision": 1,
            "path": str(rules.resolve()),
            "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
            "protocol_dir": str(protocol.resolve()),
            "protocol_fingerprint": h.hexdigest(),
            "protocol": protocol_hashes,
        }, indent=2, sort_keys=True) + "\n")
        terminal_dir = run / ".test-attempts" / f"{role}-{report.stem}"
        terminal_dir.mkdir(parents=True, exist_ok=True)
        terminal = terminal_dir / "terminal.json"
        prompt = terminal_dir / "launch-prompt.txt"
        prompt.write_text("test launch prompt\n")
        terminal.write_text(json.dumps({
            "format": "dsd-worker-terminal-v2",
            "status": "completed",
            "exit_code": 0,
            "task_id": task_id,
            "role": role,
            "report": str(report.resolve()),
            "prompt_file": str(prompt.resolve()),
            "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
            "task_contract": str(task.resolve()),
            "task_contract_sha256": hashlib.sha256(task.read_bytes()).hexdigest(),
            "worker_rules": str(rules.resolve()),
            "worker_rules_sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
            "worker_rules_manifest": str(manifest.resolve()),
            "worker_rules_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "scope_baseline": str(baseline.resolve()),
            "scope_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        }))
        return terminal

    def impl_report(self, path: Path) -> None:
        path.write_text("Completed the bounded work and recorded the relevant technical evidence.\n")



    def test_evidence_clerk_is_always_project_read_only(self):
        import sys as _sys
        scripts = str((ROOT / "scripts").resolve())
        _sys.path.insert(0, scripts)
        try:
            from _contract import role_writes_project
            self.assertFalse(role_writes_project("evidence-clerk", "# Clerk\n## Allowed source changes\nNONE\n"))
            self.assertFalse(role_writes_project("evidence-clerk", "# Clerk\n## Allowed source changes\n- `docs/progress.md`\n"))
        finally:
            if _sys.path and _sys.path[0] == scripts:
                _sys.path.pop(0)

    def test_reportless_zero_exit_empty_scope_is_factually_labeled_no_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / "source.py").write_text("VALUE=1\n")
            self.run_cmd(["git", "add", "source.py"], cwd=project)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "contract.md"; task.write_text("# Task\n## Allowed source changes\n- `source.py`\n")
            report = run / "report.md"
            skeleton = b"DSD_WORKER_REPORT_PLACEHOLDER_V1\n"
            report.write_bytes(skeleton)
            baseline = self.capture(project, run)
            legacy_terminal = self.make_terminal_event(run, task, report, baseline, "implementer")
            legacy = json.loads(legacy_terminal.read_text())
            event = legacy_terminal.parent
            reservation = event / "launch-reservation.json"
            reservation_data = {
                "format": "dsd-worker-launch-reservation-v2", "task_id": "U1", "role": "implementer", "attempt": 1,
                "writes_project": True, "report": str(report.resolve()),
                "report_skeleton_sha256": hashlib.sha256(skeleton).hexdigest(),
                "prompt_file": legacy["prompt_file"], "prompt_sha256": legacy["prompt_sha256"],
                "task_contract": str(task.resolve()), "task_contract_sha256": legacy["task_contract_sha256"],
                "worker_rules": legacy["worker_rules"], "worker_rules_sha256": legacy["worker_rules_sha256"],
                "worker_rules_manifest": legacy["worker_rules_manifest"], "worker_rules_manifest_sha256": legacy["worker_rules_manifest_sha256"],
                "scope_baseline": str(baseline.resolve()), "scope_baseline_sha256": legacy["scope_baseline_sha256"],
            }
            reservation.write_text(json.dumps(reservation_data, indent=2) + "\n")
            frozen = event / "scope-diff.json"
            cmp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare", "--root", str(project.resolve()), "--baseline", str(baseline.resolve()), "--output", str(frozen.resolve())])
            self.assertEqual(cmp.returncode, 0, cmp.stdout + cmp.stderr)
            legacy_terminal.write_text(json.dumps({
                "format": "dsd-worker-terminal-v3", "status": "completed", "exit_code": 0, "task_id": "U1",
                "role": "implementer", "attempt": 1, "launch_reservation": str(reservation.resolve()),
                "launch_reservation_sha256": hashlib.sha256(reservation.read_bytes()).hexdigest(),
                "terminal_scope": {"path": str(frozen.resolve()), "sha256": hashlib.sha256(frozen.read_bytes()).hexdigest()},
                "terminal_scope_error": None,
            }))
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(run.resolve()), "--task", str(task.resolve()), "--report", str(report.resolve()),
                "--role", "implementer", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                "--terminal-event", str(legacy_terminal.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 4, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertTrue(data["integrity_ok"]); self.assertTrue(data["needs_report_recovery"])
            self.assertEqual(data["report_state"], "launcher-skeleton")
            self.assertEqual(data["scope"]["changed_count"], 0)
            self.assertEqual(data["attempt_output"], "reportless-no-change")

    def test_historical_scope_gate_freezes_first_diff_and_does_not_recompute(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / "allowed.py").write_text("VALUE=1\n")
            (project / "outside.py").write_text("OTHER=1\n")
            self.run_cmd(["git", "add", "allowed.py", "outside.py"], cwd=project)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "contract.md"
            task.write_text("# Task\n## Allowed source changes\n- `allowed.py`\n")
            report = run / "impl.md"; self.impl_report(report)
            baseline = self.capture(project, run)
            self.make_terminal_event(run, task, report, baseline, "implementer")
            (project / "allowed.py").write_text("VALUE=2\n")
            clean = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(run.resolve()), "--task", str(task.resolve()), "--report", str(report.resolve()),
                "--role", "implementer", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            first = json.loads(clean.stdout)
            first_diff = Path(first["scope"]["diff"]); first_hash = first["scope"]["diff_sha256"]
            (project / "outside.py").write_text("OTHER=2\n")
            again = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(run.resolve()), "--task", str(task.resolve()), "--report", str(report.resolve()),
                "--role", "implementer", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            second = json.loads(again.stdout)
            self.assertEqual(Path(second["scope"]["diff"]), first_diff)
            self.assertEqual(second["scope"]["diff_sha256"], first_hash)
            self.assertNotIn("outside.py", [x.get("path") for x in json.loads(first_diff.read_text())["changed"]])

    def test_terminal_bound_scope_is_stable_across_regate_and_hash_protected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / "allowed.py").write_text("VALUE=1\n")
            (project / "outside.py").write_text("OTHER=1\n")
            self.run_cmd(["git", "add", "allowed.py", "outside.py"], cwd=project)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "contract.md"; task.write_text("# Task\n## Allowed source changes\n- `allowed.py`\n")
            report = run / "impl.md"; self.impl_report(report)
            baseline = self.capture(project, run)
            legacy_terminal = self.make_terminal_event(run, task, report, baseline, "implementer")
            legacy = json.loads(legacy_terminal.read_text())
            event = legacy_terminal.parent
            reservation = event / "launch-reservation.json"
            reservation_data = {
                "format": "dsd-worker-launch-reservation-v2", "task_id": "U1", "role": "implementer", "attempt": 1,
                "writes_project": True, "report": str(report.resolve()),
                "prompt_file": legacy["prompt_file"], "prompt_sha256": legacy["prompt_sha256"],
                "task_contract": str(task.resolve()), "task_contract_sha256": legacy["task_contract_sha256"],
                "worker_rules": legacy["worker_rules"], "worker_rules_sha256": legacy["worker_rules_sha256"],
                "worker_rules_manifest": legacy["worker_rules_manifest"], "worker_rules_manifest_sha256": legacy["worker_rules_manifest_sha256"],
                "scope_baseline": str(baseline.resolve()), "scope_baseline_sha256": legacy["scope_baseline_sha256"],
            }
            reservation.write_text(json.dumps(reservation_data, indent=2) + "\n")
            (project / "allowed.py").write_text("VALUE=2\n")
            frozen = event / "scope-diff.json"
            cmp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare", "--root", str(project.resolve()), "--baseline", str(baseline.resolve()), "--output", str(frozen.resolve())])
            self.assertEqual(cmp.returncode, 0, cmp.stdout + cmp.stderr)
            legacy_terminal.write_text(json.dumps({
                "format": "dsd-worker-terminal-v3", "status": "completed", "exit_code": 0, "task_id": "U1",
                "role": "implementer", "attempt": 1, "launch_reservation": str(reservation.resolve()),
                "launch_reservation_sha256": hashlib.sha256(reservation.read_bytes()).hexdigest(),
                "terminal_scope": {"path": str(frozen.resolve()), "sha256": hashlib.sha256(frozen.read_bytes()).hexdigest()},
                "terminal_scope_error": None,
            }))
            cmd = [PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()), "--task", str(task.resolve()), "--report", str(report.resolve()), "--role", "implementer", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--terminal-event", str(legacy_terminal.resolve()), "--json"]
            first = self.run_cmd(cmd); self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            (project / "outside.py").write_text("OTHER=2\n")
            second = self.run_cmd(cmd); self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(json.loads(first.stdout)["scope"]["diff_sha256"], json.loads(second.stdout)["scope"]["diff_sha256"])
            frozen.write_text(frozen.read_text() + " ")
            tampered = self.run_cmd(cmd); self.assertEqual(tampered.returncode, 1, tampered.stdout + tampered.stderr)
            self.assertTrue(any("terminal scope artifact changed" in e for e in json.loads(tampered.stdout)["errors"]))

    def test_explicit_no_write_restriction_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / "source.py").write_text("x=1\n")
            self.run_cmd(["git", "add", "source.py"], cwd=project)
            self.run_cmd(["git", "commit", "-m", "base"], cwd=project)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "task.md"; task.write_text("# T\n## Allowed source changes\nNONE\n")
            report = run / "r.md"; self.impl_report(report)
            baseline = self.capture(project, run)
            self.make_terminal_event(run, task, report, baseline, "implementer")
            (project / "source.py").write_text("x=2\n")
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "evidence_gate.py"),
                "--run-root", str(run.resolve()), "--task", str(task.resolve()), "--report", str(report.resolve()),
                "--role", "implementer", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json",
            ])
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            self.assertTrue(any("WRITE-RESTRICTION" in e for e in json.loads(cp.stdout)["errors"]))

    def test_run_worker_duplicate_attempt_reservation_blocks_second_launch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; bin_dir = root / "bin"; project.mkdir(); bin_dir.mkdir()
            fake = bin_dir / "opencode"
            fake.write_text("#!/usr/bin/env python3\nimport json,sys\nif sys.argv[1:3]==['session','list']:\n print(json.dumps([])); raise SystemExit(0)\nif len(sys.argv)>1 and sys.argv[1]=='run':\n print('done'); raise SystemExit(0)\nraise SystemExit(2)\n")
            fake.chmod(0o755)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            attempt = run / "attempt"; attempt.mkdir(); prompt = attempt / "prompt.txt"; prompt.write_text("x")
            task = run / "contract.md"; task.write_text("# Task U1\n")
            rules_dir = run / "worker-rules" / "r0001"; rules_dir.mkdir(parents=True)
            rules = rules_dir / "WORKER_RULES.md"; rules.write_text("rules\n")
            protocol = rules_dir / "protocol"; protocol.mkdir()
            h = hashlib.sha256(); protocol_hashes = {}
            for name in PROTOCOL_NAMES:
                f = protocol / name; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(name + "\n")
                h.update(name.encode()); h.update(b"\0"); h.update(f.read_bytes()); h.update(b"\0")
                protocol_hashes[name] = hashlib.sha256(f.read_bytes()).hexdigest()
            manifest = rules_dir / "MANIFEST.json"
            manifest.write_text(json.dumps({
                "format": "dsd-worker-rules-manifest-v2", "revision": 1,
                "path": str(rules.resolve()), "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
                "protocol_dir": str(protocol.resolve()), "protocol_fingerprint": h.hexdigest(),
                "protocol": protocol_hashes,
            }, indent=2, sort_keys=True) + "\n")
            scope = attempt / "scope-baseline.json"; scope.write_text("{}\n")
            report = run / "report.md"; log = attempt / "worker.log"; db = root / "external" / "workers.db"
            env = os.environ.copy(); env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
            cmd = [
                PYTHON, str(ROOT / "scripts" / "run_worker.py"), "--project-root", str(project.resolve()),
                "--run-root", str(run.resolve()), "--task-id", "U1", "--role", "implementer",
                "--prompt-file", str(prompt.resolve()), "--task-contract", str(task.resolve()), "--worker-rules", str(rules.resolve()),
                "--scope-baseline", str(scope.resolve()), "--report", str(report.resolve()),
                "--event-dir", str(attempt.resolve()), "--log", str(log.resolve()), "--db", str(db.resolve()), "--auto-flag", "",
            ]
            first = self.run_cmd(cmd, env=env); self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = self.run_cmd(cmd, env=env); self.assertEqual(second.returncode, 2, second.stdout + second.stderr)
            self.assertTrue("already exists" in second.stderr or "reservation" in second.stderr)


    def test_scope_snapshot_records_symlink_identity_without_hashing_external_target(self):
        if os.name == "nt":
            self.skipTest("symlink permissions vary on Windows")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir()
            outside = root / "outside.txt"; outside.write_text("secret-v1\n")
            (project / "link.txt").symlink_to(outside)
            snap = root / "snapshot.json"
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project.resolve()), "--output", str(snap.resolve()), "link.txt"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            entry = json.loads(snap.read_text())["entries"]["link.txt"]
            self.assertEqual(entry["kind"], "symlink"); before = entry["sha256"]
            outside.write_text("secret-v2\n")
            diff = root / "diff.json"
            self.assertEqual(self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare", "--root", str(project.resolve()), "--baseline", str(snap.resolve()), "--output", str(diff.resolve())]).returncode, 0)
            self.assertEqual(json.loads(diff.read_text())["changed"], [])
            (project / "link.txt").unlink(); (project / "link.txt").symlink_to(root / "other.txt")
            diff2 = root / "diff2.json"
            self.assertEqual(self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare", "--root", str(project.resolve()), "--baseline", str(snap.resolve()), "--output", str(diff2.resolve())]).returncode, 0)
            change = json.loads(diff2.read_text())["changed"][0]
            self.assertEqual(change["path"], "link.txt"); self.assertNotEqual(change["after"]["sha256"], before)

    def test_check_state_binds_active_attempt_to_prompt_scope_and_worker_rules(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run = root / "DeepSeekAndDestroy" / "run"
            run.mkdir(parents=True)
            revision = run / "worker-rules" / "r0001"
            revision.mkdir(parents=True)
            rules = revision / "WORKER_RULES.md"
            rules.write_text("rules\n")
            protocol = revision / "protocol"
            protocol.mkdir()
            h = hashlib.sha256()
            for name in PROTOCOL_NAMES:
                f = protocol / name
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(name + "\n")
                h.update(name.encode())
                h.update(b"\0")
                h.update(f.read_bytes())
                h.update(b"\0")
            manifest = rules.parent / "MANIFEST.json"
            manifest.write_text(json.dumps({
                "format": "dsd-worker-rules-manifest-v2",
                "revision": 1,
                "path": str(rules.resolve()),
                "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
                "protocol_dir": str(protocol.resolve()),
                "protocol_fingerprint": h.hexdigest(),
                "protocol": {name: hashlib.sha256((protocol / name).read_bytes()).hexdigest() for name in PROTOCOL_NAMES},
            }, indent=2, sort_keys=True) + "\n")
            task = run / "task.md"
            task.write_text("task\n")
            attempt_dir = run / "attempt"
            attempt_dir.mkdir()
            prompt = attempt_dir / "launch-prompt.txt"
            prompt.write_text("prompt\n")
            baseline = attempt_dir / "scope-baseline.json"
            baseline.write_text("{}\n")
            reservation = attempt_dir / "launch-reservation.json"
            reservation.write_text(json.dumps({
                "prompt_file": str(prompt.resolve()),
                "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                "task_contract": str(task.resolve()),
                "task_contract_sha256": hashlib.sha256(task.read_bytes()).hexdigest(),
                "worker_rules": str(rules.resolve()),
                "worker_rules_sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
                "worker_rules_manifest": str(manifest.resolve()),
                "worker_rules_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "scope_baseline": str(baseline.resolve()),
                "scope_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                "role": "reviewer",
                "attempt": 1,
            }))
            report = run / "review-1.md"
            state = {
                "execution_status": "active",
                "next_action": "wait reviewer",
                "worker_runtime": {"harness": "opencode-cli"},
                "worker_rules": {
                    "revision": 1,
                    "path": str(rules.resolve()),
                    "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
                    "protocol_dir": str(protocol.resolve()),
                    "protocol_fingerprint": h.hexdigest(),
                    "manifest": str(manifest.resolve()),
                    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                },
                "context_checkpoint": {"status": "none"},
                "phases": {
                    "p1": {
                        "status": "in-progress",
                        "tasks": {
                            "U1": {
                                "status": "in-progress",
                                                                "current_contract": {
                                    "revision": 1,
                                    "path": str(task.resolve()),
                                    "sha256": hashlib.sha256(task.read_bytes()).hexdigest(),
                                },
                                "current_attempt": {
                                    "role": "reviewer",
                                    "attempt": 1,
                                    "prompt_path": str(prompt.resolve()),
                                    "scope_baseline": str(baseline.resolve()),
                                    "scope_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                                    "launch_reservation": str(reservation.resolve()),
                                    "worker_rules_revision": 1,
                                    "worker_rules_path": str(rules.resolve()),
                                    "report_path": str(report.resolve()),
                                    "event_dir": str(attempt_dir.resolve()),
                                    "terminal_event": str((attempt_dir / "terminal.json").resolve()),
                                    "monitor_pid": os.getpid(),
                                    "launched_at": "2026-08-10T17:00:00Z",
                                    "liveness": "confirmed",
                                },
                            }
                        },
                    }
                },
            }
            state_path = run / "state.json"
            state_path.write_text(json.dumps(state))
            clean = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state_path.resolve())])
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)

            # A newer run-default rules revision must not invalidate an already
            # launched attempt that remains cryptographically bound to r0001.
            revision2 = run / "worker-rules" / "r0002"
            revision2.mkdir(parents=True)
            rules2 = revision2 / "WORKER_RULES.md"; rules2.write_text("rules v2\n")
            protocol2 = revision2 / "protocol"; protocol2.mkdir()
            h2 = hashlib.sha256()
            for name in PROTOCOL_NAMES:
                f = protocol2 / name; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(name + " v2\n")
                h2.update(name.encode()); h2.update(b"\0"); h2.update(f.read_bytes()); h2.update(b"\0")
            manifest2 = revision2 / "MANIFEST.json"
            manifest2.write_text(json.dumps({
                "format": "dsd-worker-rules-manifest-v2",
                "revision": 2,
                "path": str(rules2.resolve()),
                "sha256": hashlib.sha256(rules2.read_bytes()).hexdigest(),
                "protocol_dir": str(protocol2.resolve()),
                "protocol_fingerprint": h2.hexdigest(),
                "protocol": {name: hashlib.sha256((protocol2 / name).read_bytes()).hexdigest() for name in PROTOCOL_NAMES},
            }, indent=2, sort_keys=True) + "\n")
            state["worker_rules"] = {
                "revision": 2, "path": str(rules2.resolve()),
                "sha256": hashlib.sha256(rules2.read_bytes()).hexdigest(),
                "protocol_dir": str(protocol2.resolve()), "protocol_fingerprint": h2.hexdigest(),
                "manifest": str(manifest2.resolve()),
                "manifest_sha256": hashlib.sha256(manifest2.read_bytes()).hexdigest(),
            }
            state_path.write_text(json.dumps(state))
            newer_default = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state_path.resolve())])
            self.assertEqual(newer_default.returncode, 0, newer_default.stdout + newer_default.stderr)

            prompt.write_text("mutated\n")
            bad = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state_path.resolve())])
            self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
            self.assertIn("immutable prompt_file changed after reservation", bad.stdout)

    def test_evidence_gate_rejects_bound_authority_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / "base.py").write_text("VALUE=1\n")
            self.run_cmd(["git", "add", "base.py"], cwd=project)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "contract.md"
            task.write_text("# Task\n## Allowed source changes\nNONE\n")
            report = run / "impl.md"; self.impl_report(report)
            baseline = self.capture(project, run)
            terminal = self.make_terminal_event(run, task, report, baseline, "implementer")
            terminal_data = json.loads(terminal.read_text())
            rules = Path(terminal_data["worker_rules"])
            prompt = Path(terminal_data["prompt_file"])
            protocol_core = rules.parent / "protocol" / "COMMON.md"
            manifest = Path(terminal_data["worker_rules_manifest"])
            originals = {
                task: task.read_bytes(), baseline: baseline.read_bytes(), rules: rules.read_bytes(),
                prompt: prompt.read_bytes(), protocol_core: protocol_core.read_bytes(), manifest: manifest.read_bytes(),
            }

            cases = [
                (prompt, "immutable launch prompt changed"),
                (task, "immutable task_contract changed"),
                (baseline, "immutable scope_baseline changed"),
                (rules, "immutable worker_rules changed"),
                (protocol_core, "worker-rules snapshot integrity failed"),
                (manifest, "worker-rules snapshot integrity failed"),
            ]
            for path, expected in cases:
                with self.subTest(path=path.name):
                    path.write_bytes(originals[path] + b"tamper\n")
                    cp = self.run_cmd([
                        PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()),
                        "--task", str(task.resolve()), "--report", str(report.resolve()), "--role", "implementer",
                        "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()),
                        "--terminal-event", str(terminal.resolve()), "--json",
                    ])
                    self.assertNotEqual(cp.returncode, 0, cp.stdout + cp.stderr)
                    self.assertIn(expected, cp.stdout + cp.stderr)
                    path.write_bytes(originals[path])

    def test_dot_prefixed_write_paths_preserve_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            run = project / "DeepSeekAndDestroy" / "run"
            contract = run / "task" / "contracts" / "r0001.md"
            project.mkdir(parents=True)
            run.mkdir(parents=True)
            plan = project / "PLAN.md"
            plan.write_text("plan\n")
            spec = run / "spec.json"
            spec.write_text(json.dumps({
                "run_root": str(run.resolve()), "task_id": "U1", "revision": 1,
                "output": str(contract.resolve()), "title": "dot path", "objective": "preserve dot prefix",
                "authority": [str(plan.resolve())], "write_paths": [".github/workflows"],
            }))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "render_task_contract.py"), "--spec", str(spec)])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertEqual(data["write_restriction"], [".github/workflows"])
            self.assertIn("`.github/workflows`", contract.read_text())

    def test_scope_snapshot_refuses_to_overwrite_immutable_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = root / "project"; project.mkdir(); (project / "x.txt").write_text("x\n")
            snap = root / "scope.json"
            cmd = [PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project.resolve()), "--output", str(snap.resolve()), "x.txt"]
            first = self.run_cmd(cmd); self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = self.run_cmd(cmd); self.assertEqual(second.returncode, 2, second.stdout + second.stderr)
            self.assertIn("immutable scope artifact already exists", second.stderr)

    def test_verify_resume_mechanically_accepts_mutable_progress_and_rejects_authority_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            run = project / "DeepSeekAndDestroy" / "plans" / "p1" / "runs" / "r1"
            run.mkdir(parents=True)
            plan_ref = run / "plan" / "plan-reference.md"; plan_ref.parent.mkdir(); plan_ref.write_text("plan ref\n")
            authority = run / "authority-index.json"; authority.write_text("{}\n")
            config = run / "effective-configuration.md"; config.write_text("config\n")
            handover = run / "HANDOVER.md"; handover.write_text("handover\n")
            state_path = run / "state.json"
            state = {
                "run_id": "r1", "plan_id": "p1", "plan_source_sha256": "stable-plan-id",
                "execution_status": "active", "next_action": "wait worker",
                "handover": str(handover.resolve()),
                "plan_reference": str(plan_ref.resolve()),
                "authority_index": str(authority.resolve()),
                "effective_config": str(config.resolve()),
                "context_checkpoint": {"status": "none"},
            }
            state_path.write_text(json.dumps(state))
            prepared = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "context_checkpoint.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "prepare", "--harness", "codex", "--reason", "test",
            ])
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            sequence = json.loads(prepared.stdout)["sequence"]

            # Mutable execution progress is allowed while compacted.
            live = json.loads(state_path.read_text()); live["next_action"] = "review completed worker"; state_path.write_text(json.dumps(live))
            verified = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "context_checkpoint.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "verify-resume", "--sequence", str(sequence), "--harness", "codex",
            ])
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            self.assertTrue(json.loads(verified.stdout)["continuity_verified"])

            plan_ref.write_text("drifted authority\n")
            drifted = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "context_checkpoint.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "verify-resume", "--sequence", str(sequence), "--harness", "codex",
            ])
            self.assertEqual(drifted.returncode, 2, drifted.stdout + drifted.stderr)
            self.assertIn("Governing authority drift", drifted.stderr)
            final_state = json.loads(state_path.read_text())
            self.assertEqual(final_state["context_checkpoint"]["status"], "rehydration-required")
            self.assertFalse(final_state["context_checkpoint"]["continuity_verified"])


    def test_ignored_extra_inventory_catches_additions_and_removals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / ".gitignore").write_text("runtime/\n")
            (project / "tracked.txt").write_text("base\n")
            self.run_cmd(["git", "add", ".gitignore", "tracked.txt"], cwd=project)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
            runtime = project / "runtime"; runtime.mkdir(); (runtime / "lock-a").write_text("a\n")
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "task.md"; task.write_text("# Task\n## Allowed source changes\n- `runtime`\n\n## Extra scope inventory\n- `runtime`\n")
            baseline = run / "scope.json"
            cap = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "capture", "--root", str(project.resolve()), "--output", str(baseline.resolve()), "--git-worktree", "--exclude-prefix", "DeepSeekAndDestroy", "--task-contract", str(task.resolve())])
            self.assertEqual(cap.returncode, 0, cap.stdout + cap.stderr)
            (runtime / "lock-a").unlink(); (runtime / "lock-b").write_text("b\n")
            out = run / "diff.json"
            cmp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "scope_snapshot.py"), "compare", "--root", str(project.resolve()), "--baseline", str(baseline.resolve()), "--output", str(out.resolve())])
            self.assertEqual(cmp.returncode, 0, cmp.stdout + cmp.stderr)
            data = json.loads(out.read_text())
            self.assertIn("runtime/lock-b", data["added"])
            self.assertIn("runtime/lock-a", data["removed"])
            self.assertEqual(data["extra_inventory_specs"], ["runtime"])

    def test_verification_role_can_write_when_contract_declares_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / "generated.txt").write_text("old\n")
            self.run_cmd(["git", "add", "generated.txt"], cwd=project)
            self.assertEqual(self.run_cmd(["git", "commit", "-m", "base"], cwd=project).returncode, 0)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "task.md"; task.write_text("# Verification\n## Allowed source changes\n- `generated.txt`\n")
            report = run / "verification.md"; report.write_text("Verification exercised the assigned predicate and recorded the result.\n")
            baseline = self.capture(project, run)
            self.make_terminal_event(run, task, report, baseline, "verification")
            (project / "generated.txt").write_text("new\n")
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()), "--task", str(task.resolve()), "--report", str(report.resolve()), "--role", "verification", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json"])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(json.loads(cp.stdout)["integrity_ok"])

    def test_verification_without_write_scope_remains_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project = self.init_git_project(root)
            (project / "generated.txt").write_text("old\n")
            self.run_cmd(["git", "add", "generated.txt"], cwd=project); self.run_cmd(["git", "commit", "-m", "base"], cwd=project)
            run = project / "DeepSeekAndDestroy" / "run"; run.mkdir(parents=True)
            task = run / "task.md"; task.write_text("# Verification\n## Allowed source changes\nNONE\n")
            report = run / "verification.md"; report.write_text("Verification exercised the assigned predicate and recorded the result.\n")
            baseline = self.capture(project, run); self.make_terminal_event(run, task, report, baseline, "verification")
            (project / "generated.txt").write_text("new\n")
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "evidence_gate.py"), "--run-root", str(run.resolve()), "--task", str(task.resolve()), "--report", str(report.resolve()), "--role", "verification", "--project-root", str(project.resolve()), "--scope-baseline", str(baseline.resolve()), "--json"])
            self.assertEqual(cp.returncode, 1, cp.stdout + cp.stderr)
            self.assertTrue(any("READONLY-SCOPE-MOVED" in e for e in json.loads(cp.stdout)["errors"]))



if __name__ == "__main__":
    unittest.main()
