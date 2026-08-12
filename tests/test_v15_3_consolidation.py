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


class V153ConsolidationTest(unittest.TestCase):
    def run_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)

    def make_run(self, root: Path, *, proof_pattern: list[str] | None = None):
        project = root / "project"; project.mkdir(parents=True)
        self.assertEqual(self.run_cmd(["git", "init"], cwd=project).returncode, 0)
        self.run_cmd(["git", "config", "user.email", "dsd@test.invalid"], cwd=project)
        self.run_cmd(["git", "config", "user.name", "DSD Test"], cwd=project)
        (project / "base.txt").write_text("base\n")
        self.run_cmd(["git", "add", "base.txt"], cwd=project)
        self.run_cmd(["git", "commit", "-m", "base"], cwd=project)
        run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r"; run.mkdir(parents=True)
        plan = project / "plan.md"; plan.write_text("# Plan\n")
        rules_cp = self.run_cmd([
            PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
            "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
            "--plan", str(plan.resolve()), "--skill-root", str(ROOT.resolve()),
        ])
        self.assertEqual(rules_cp.returncode, 0, rules_cp.stdout + rules_cp.stderr)
        rules = json.loads(rules_cp.stdout)
        contract = run / "phases" / "p1" / "U1" / "contracts" / "r0001.md"
        spec = {
            "run_root": str(run.resolve()), "task_id": "U1", "revision": 1,
            "output": str(contract.resolve()), "unit": "review", "objective": "Review bounded behavior",
            "acceptance": ["AC-001 production behavior is correct"],
        }
        if proof_pattern:
            spec["proof_pattern"] = proof_pattern
        spec_path = run / "contract-spec.json"; spec_path.write_text(json.dumps(spec))
        contract_cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "render_task_contract.py"), "--spec", str(spec_path)])
        self.assertEqual(contract_cp.returncode, 0, contract_cp.stdout + contract_cp.stderr)
        contract_meta = json.loads(contract_cp.stdout)
        return project, run, rules, contract, contract_meta

    def test_prompt_loads_proof_library_only_when_named_and_hashes_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project, run, rules, contract, _ = self.make_run(root)
            evidence = run / "prior.md"; evidence.write_text("prior evidence\n")
            out = run / "prompt.txt"
            cp = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"), "--role", "reviewer", "--task-id", "U1",
                "--run-root", str(run.resolve()), "--worker-rules", rules["path"], "--task", str(contract.resolve()),
                "--report", str((run / "report.md").resolve()), "--evidence", str(evidence.resolve()), "--output", str(out.resolve()),
            ])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            text = out.read_text()
            self.assertNotIn("PROOF-PATTERNS.md", text)
            self.assertIn(hashlib.sha256(evidence.read_bytes()).hexdigest(), text)

            project2, run2, rules2, contract2, _ = self.make_run(root / "second", proof_pattern=["DURABILITY"])
            out2 = run2 / "prompt.txt"
            cp2 = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"), "--role", "reviewer", "--task-id", "U1",
                "--run-root", str(run2.resolve()), "--worker-rules", rules2["path"], "--task", str(contract2.resolve()),
                "--report", str((run2 / "report.md").resolve()), "--output", str(out2.resolve()),
            ])
            self.assertEqual(cp2.returncode, 0, cp2.stdout + cp2.stderr)
            self.assertIn("PROOF-PATTERNS.md — only: DURABILITY", out2.read_text())

    def test_evidence_clerk_is_always_project_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); _, run, _, _, _ = self.make_run(root)
            bad_spec = run / "clerk.json"
            bad_spec.write_text(json.dumps({
                "run_root": str(run.resolve()), "task_id": "C1", "revision": 1,
                "output": str((run / "phases" / "p1" / "C1" / "contracts" / "r0001.md").resolve()),
                "unit": "clerk", "objective": "Interpret evidence", "role": "evidence-clerk",
                "write_path": ["docs/status.md"],
            }))
            cp = self.run_cmd([PYTHON, str(ROOT / "scripts" / "render_task_contract.py"), "--spec", str(bad_spec)])
            self.assertEqual(cp.returncode, 2)
            self.assertIn("always project-read-only", cp.stderr)

    def test_normal_attempt_flow_accepts_natural_report_without_report_grammar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); project, run, rules, contract, contract_meta = self.make_run(root)
            bindir = root / "bin"; bindir.mkdir()
            fake = bindir / "opencode"
            fake.write_text(r'''#!/usr/bin/env python3
import json, os, re, sys
from pathlib import Path
args=sys.argv[1:]
db=Path(os.environ.get("OPENCODE_DB","/tmp/fake.db"))
title_file=Path(str(db)+".title")
if args[:2]==["session","list"]:
    title=title_file.read_text() if title_file.exists() else ""
    print(json.dumps([{"id":"ses_fake","title":title}] if title else [])); raise SystemExit(0)
if args and args[0]=="run":
    title=args[args.index("--title")+1]; title_file.parent.mkdir(parents=True, exist_ok=True); title_file.write_text(title)
    prompt=args[-1]
    m=re.search(r"^Report: (.+)$", prompt, re.M)
    if not m: raise SystemExit(3)
    report=Path(m.group(1).strip())
    report.write_text("Reviewed the production path and exercised the required behavior.\nNo task-relevant defect was found; the requirement is established by the recorded probe.\n")
    print("complete"); raise SystemExit(0)
raise SystemExit(2)
''')
            fake.chmod(0o755)
            db = root / "external" / "workers.db"
            state = run / "state.json"
            state.write_text(json.dumps({
                "execution_status": "active", "next_action": "launch reviewer",
                "project_worktree": str(project.resolve()), "run_root": str(run.resolve()),
                "worker_rules": {k: rules[k] for k in ("revision", "path", "sha256", "protocol_dir", "protocol_fingerprint", "manifest", "manifest_sha256")},
                "worker_runtime": {"harness": "opencode-cli", "model": "fake/model", "opencode": {"run_db": str(db.resolve())}},
                "context_checkpoint": {"status": "none"},
                "phases": {"p1": {"status": "in-progress", "gate_barrier": {"status": "OPEN"}, "tasks": {"U1": {
                    "status": "prepared", "dependency_status": "valid", "current_contract": contract_meta,
                    "decomposition_required": False, "zero_intended_change_streak": 0, "next_role": "reviewer", "transport_attempts": 0,
                }}}},
            }, indent=2))
            checked = self.run_cmd([PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state.resolve())])
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            env = os.environ.copy(); env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            launched = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch", "--state", str(state.resolve()),
                "--phase", "p1", "--task", "U1", "--role", "reviewer",
            ], env=env)
            self.assertEqual(launched.returncode, 0, launched.stdout + launched.stderr)
            launch_data = json.loads(launched.stdout)
            attempt_dir = Path(launch_data["attempt_dir"])
            self.assertEqual(attempt_dir.name, "reviewer-1")
            for name in ("prompt.txt", "scope-baseline.json", "report.md", "launch-reservation.json"):
                self.assertTrue((attempt_dir / name).exists(), name)
            terminal = attempt_dir / "terminal.json"
            deadline = time.monotonic() + 10
            while not terminal.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(terminal.exists(), "detached fake worker never produced terminal")
            gated = self.run_cmd([
                PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "gate", "--state", str(state.resolve()),
                "--phase", "p1", "--task", "U1",
            ], env=env)
            self.assertEqual(gated.returncode, 0, gated.stdout + gated.stderr)
            gate_data = json.loads(gated.stdout)
            self.assertTrue(gate_data["mechanical_ok"])
            self.assertFalse(gate_data["report_recovery_required"])
            self.assertTrue(any("production path" in line for line in gate_data["decision_surface"]))
            gate_artifact = json.loads(Path(gate_data["evidence_gate"]).read_text())
            self.assertNotIn("verdict", gate_artifact)
            self.assertNotIn("clerk_reasons", gate_artifact)
            final_state = json.loads(state.read_text())
            task = final_state["phases"]["p1"]["tasks"]["U1"]
            self.assertEqual(task["status"], "process-exited")
            self.assertTrue(Path(task["evidence_gate_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
