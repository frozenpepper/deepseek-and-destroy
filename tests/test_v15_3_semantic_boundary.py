from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PROTOCOL_NAMES = (
    'COMMON.md', 'PROOF-PATTERNS.md', 'roles/dsd-implementer/SKILL.md',
    'roles/dsd-fixer/SKILL.md', 'roles/dsd-reviewer/SKILL.md',
    'roles/dsd-verification/SKILL.md', 'roles/dsd-discovery/SKILL.md',
    'roles/dsd-phase-surveyor/SKILL.md', 'roles/dsd-recovery/SKILL.md',
    'roles/dsd-phase-auditor/SKILL.md', 'roles/dsd-evidence-clerk/SKILL.md',
)


class SemanticBoundaryTest(unittest.TestCase):
    def run_cmd(self, cmd, **kwargs):
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)

    def init_git(self, root: Path) -> Path:
        project = root / 'project'; project.mkdir()
        self.assertEqual(self.run_cmd(['git','init'], cwd=project).returncode, 0)
        self.run_cmd(['git','config','user.email','dsd@test.invalid'], cwd=project)
        self.run_cmd(['git','config','user.name','DSD Test'], cwd=project)
        (project/'source.py').write_text('VALUE = 1\n')
        self.run_cmd(['git','add','source.py'], cwd=project)
        self.assertEqual(self.run_cmd(['git','commit','-m','base'], cwd=project).returncode, 0)
        return project

    def worker_rules(self, run: Path) -> Path:
        rev = run/'worker-rules'/'r0001'; rev.mkdir(parents=True, exist_ok=True)
        rules = rev/'WORKER_RULES.md'; rules.write_text('rules\n')
        protocol = rev/'protocol'; protocol.mkdir()
        h = hashlib.sha256(); hashes = {}
        for name in PROTOCOL_NAMES:
            path = protocol/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(name+'\n')
            h.update(name.encode()); h.update(b'\0'); h.update(path.read_bytes()); h.update(b'\0')
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = rev/'MANIFEST.json'
        manifest.write_text(json.dumps({
            'format':'dsd-worker-rules-manifest-v2','revision':1,'path':str(rules.resolve()),
            'sha256':hashlib.sha256(rules.read_bytes()).hexdigest(),'protocol_dir':str(protocol.resolve()),
            'protocol_fingerprint':h.hexdigest(),'protocol':hashes,
        }, indent=2, sort_keys=True)+'\n')
        return rules

    def baseline(self, project: Path, run: Path) -> Path:
        path = run/'scope.json'
        cp = self.run_cmd([PYTHON,str(ROOT/'scripts'/'scope_snapshot.py'),'capture','--root',str(project.resolve()),'--output',str(path.resolve()),'--git-worktree','--exclude-prefix','DeepSeekAndDestroy'])
        self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
        return path

    def terminal_v2(self, run: Path, task: Path, report: Path, baseline: Path, role: str) -> Path:
        rules = self.worker_rules(run)
        event = run/'attempt'; event.mkdir(exist_ok=True)
        prompt = event/'prompt.txt'; prompt.write_text('prompt\n')
        terminal = event/'terminal.json'
        terminal.write_text(json.dumps({
            'format':'dsd-worker-terminal-v2','status':'completed','exit_code':0,'task_id':'U1','role':role,
            'report':str(report.resolve()),'prompt_file':str(prompt.resolve()),'prompt_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),
            'task_contract':str(task.resolve()),'task_contract_sha256':hashlib.sha256(task.read_bytes()).hexdigest(),
            'worker_rules':str(rules.resolve()),'worker_rules_sha256':hashlib.sha256(rules.read_bytes()).hexdigest(),
            'worker_rules_manifest':str((rules.parent/'MANIFEST.json').resolve()),
            'worker_rules_manifest_sha256':hashlib.sha256((rules.parent/'MANIFEST.json').read_bytes()).hexdigest(),
            'scope_baseline':str(baseline.resolve()),'scope_baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),
        }))
        return terminal

    def test_integrity_gate_does_not_adjudicate_worker_prose(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); project=self.init_git(root); run=project/'DeepSeekAndDestroy'/'run'; run.mkdir(parents=True)
            task=run/'task.md'; task.write_text('# Task\n## Allowed source changes\nNONE\n\n## Acceptance criteria\n- AC-001 — behavior works.\n')
            report=run/'review.md'
            report.write_text('''I reviewed the change.\nThere is no magic verdict label here.\n203 tests / 201 passed / 7 failed — this arithmetic is intentionally nonsense.\nI discuss the requirement without repeating its AC identifier.\nThe reader must interpret what this means.\n''')
            baseline=self.baseline(project,run); terminal=self.terminal_v2(run,task,report,baseline,'reviewer')
            cp=self.run_cmd([PYTHON,str(ROOT/'scripts'/'evidence_gate.py'),'--run-root',str(run.resolve()),'--task',str(task.resolve()),'--report',str(report.resolve()),'--role','reviewer','--project-root',str(project.resolve()),'--scope-baseline',str(baseline.resolve()),'--terminal-event',str(terminal.resolve()),'--json'])
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
            data=json.loads(cp.stdout)
            self.assertTrue(data['integrity_ok']); self.assertTrue(data['ready_for_interpretation'])
            for forbidden in ('verdict','fast_path_eligible','review_contract','clerk_required','clerk_reasons'):
                self.assertNotIn(forbidden,data)

    def test_integrity_gate_still_hard_fails_objective_scope_violation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); project=self.init_git(root); run=project/'DeepSeekAndDestroy'/'run'; run.mkdir(parents=True)
            task=run/'task.md'; task.write_text('# Task\n## Allowed source changes\nNONE\n')
            report=run/'review.md'; report.write_text('Looks fine to me.\n')
            baseline=self.baseline(project,run); terminal=self.terminal_v2(run,task,report,baseline,'reviewer')
            (project/'source.py').write_text('VALUE = 2\n')
            cp=self.run_cmd([PYTHON,str(ROOT/'scripts'/'evidence_gate.py'),'--run-root',str(run.resolve()),'--task',str(task.resolve()),'--report',str(report.resolve()),'--role','reviewer','--project-root',str(project.resolve()),'--scope-baseline',str(baseline.resolve()),'--terminal-event',str(terminal.resolve()),'--json'])
            self.assertEqual(cp.returncode,1,cp.stdout+cp.stderr)
            self.assertTrue(any('READONLY-SCOPE-MOVED' in x for x in json.loads(cp.stdout)['errors']))

    def test_contract_renderer_assigns_ids_and_rejects_retired_clerk_field(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); project=root/'project'; project.mkdir(); run=project/'DeepSeekAndDestroy'/'run'; run.mkdir(parents=True)
            spec=run/'spec.json'; out=run/'contracts'/'r0001.md'
            data={
                'run_root':str(run.resolve()),'task_id':'U1','revision':1,'title':'Natural contract','objective':'Do the thing.',
                'output':str(out.resolve()),'acceptance':['the result survives restart','AC-009 — invalid input fails closed'],
                'write_paths':[],
            }
            spec.write_text(json.dumps(data))
            cp=self.run_cmd([PYTHON,str(ROOT/'scripts'/'render_task_contract.py'),'--spec',str(spec)])
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
            text=out.read_text(); self.assertIn('AC-001 — the result survives restart',text); self.assertIn('AC-009 — invalid input fails closed',text)
            self.assertNotIn('Evidence Clerk Checks', text)
            data['clerk_checks']=['legacy footgun']; spec.write_text(json.dumps(data))
            cp=self.run_cmd([PYTHON,str(ROOT/'scripts'/'render_task_contract.py'),'--spec',str(spec)])
            self.assertEqual(cp.returncode,2,cp.stdout+cp.stderr)
            self.assertIn('retired Clerk-recursion field', cp.stderr)

    def test_acceptance_binds_semantic_evidence_without_storing_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/'DeepSeekAndDestroy'/'run'; run.mkdir(parents=True)
            contract=run/'task.md'; contract.write_text('# Task\nContract revision: r0001\n\n## Allowed source changes\nNONE\n')
            state={'execution_status':'active','next_action':'decide','phases':{'p1':{'status':'in-progress','gate_barrier':{'status':'OPEN','snapshot':None},'tasks':{'U1':{
                'status':'process-exited','current_contract':{'revision':1,'path':str(contract.resolve()),'sha256':hashlib.sha256(contract.read_bytes()).hexdigest()}
            }}}}}
            (run/'state.json').write_text(json.dumps(state))
            source_report=run/'review.md'; source_report.write_text('Natural review report.\n')
            source_gate=run/'review-gate.json'; source_gate.write_text(json.dumps({'format':'dsd-integrity-gate-v2','integrity_ok':True,'ready_for_interpretation':True,'errors':[],'role':'reviewer','task':str(contract.resolve()),'report':str(source_report.resolve()),'report_sha256':hashlib.sha256(source_report.read_bytes()).hexdigest()}))
            clerk=run/'clerk.md'; clerk.write_text('Compact interpretation consumed by the parent.\n')
            clerk_gate=run/'clerk-gate.json'; clerk_gate.write_text(json.dumps({'format':'dsd-integrity-gate-v2','integrity_ok':True,'ready_for_interpretation':True,'errors':[],'role':'evidence-clerk','task':str(contract.resolve()),'report':str(clerk.resolve()),'report_sha256':hashlib.sha256(clerk.read_bytes()).hexdigest()}))
            cp=self.run_cmd([PYTHON,str(ROOT/'scripts'/'dsd_state.py'),'accept-task','--run-root',str(run.resolve()),'--phase-id','p1','--task-id','U1','--evidence-gate',str(source_gate.resolve()),'--semantic-evidence',str(clerk.resolve()),'--semantic-evidence-gate',str(clerk_gate.resolve()),'--next-action','next task'])
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
            task=json.loads((run/'state.json').read_text())['phases']['p1']['tasks']['U1']
            self.assertEqual(task['status'],'accepted')
            self.assertEqual(task['accepted']['semantic_report']['path'],str(clerk.resolve()))
            self.assertNotIn('last_verdict',task)

    def test_routine_clerk_read_only_reservation_overrides_source_contract_write_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); project=self.init_git(root); run=project/'DeepSeekAndDestroy'/'run'; run.mkdir(parents=True)
            task=run/'task.md'; task.write_text('# Task\n## Allowed source changes\n- `source.py`\n')
            report=run/'clerk.md'; report.write_text('I interpreted the source worker report.\n')
            baseline=self.baseline(project,run)
            rules=self.worker_rules(run); manifest=rules.parent/'MANIFEST.json'
            event=run/'clerk-attempt'; event.mkdir(); prompt=event/'prompt.txt'; prompt.write_text('prompt\n'); log=event/'worker.log'; log.write_text('')
            reservation=event/'launch-reservation.json'
            reservation.write_text(json.dumps({
                'format':'dsd-worker-launch-reservation-v2','task_id':'U1','role':'evidence-clerk','attempt':1,
                'writes_project':False,'report':str(report.resolve()),'log':str(log.resolve()),
                'prompt_file':str(prompt.resolve()),'prompt_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),
                'task_contract':str(task.resolve()),'task_contract_sha256':hashlib.sha256(task.read_bytes()).hexdigest(),
                'worker_rules':str(rules.resolve()),'worker_rules_sha256':hashlib.sha256(rules.read_bytes()).hexdigest(),
                'worker_rules_manifest':str(manifest.resolve()),'worker_rules_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                'scope_baseline':str(baseline.resolve()),'scope_baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),
            }))
            terminal=event/'terminal.json'; terminal.write_text(json.dumps({
                'format':'dsd-worker-terminal-v3','status':'completed','exit_code':0,'task_id':'U1','role':'evidence-clerk','attempt':1,
                'launch_reservation':str(reservation.resolve()),'launch_reservation_sha256':hashlib.sha256(reservation.read_bytes()).hexdigest(),
            }))
            # Even though the originating technical contract allows source.py, this
            # exact routine Clerk attempt was reserved read-only. Any movement is a
            # hard integrity fact, not something prose interpretation may waive.
            (project/'source.py').write_text('VALUE = 2\n')
            cp=self.run_cmd([PYTHON,str(ROOT/'scripts'/'evidence_gate.py'),'--run-root',str(run.resolve()),'--task',str(task.resolve()),'--report',str(report.resolve()),'--role','evidence-clerk','--project-root',str(project.resolve()),'--scope-baseline',str(baseline.resolve()),'--terminal-event',str(terminal.resolve()),'--log',str(log.resolve()),'--json'])
            self.assertEqual(cp.returncode,1,cp.stdout+cp.stderr)
            data=json.loads(cp.stdout)
            self.assertFalse(data['writes_project'])
            self.assertTrue(any('READONLY-SCOPE-MOVED' in x for x in data['errors']))

    def test_role_registry_matches_role_skill_directories(self):
        sys.path.insert(0, str(ROOT/'scripts'))
        try:
            from _roles import ROLE_NAMES, ROLE_SKILLS
        finally:
            sys.path.pop(0)
        discovered={p.parent.name.removeprefix('dsd-') for p in (ROOT/'worker'/'roles').glob('dsd-*/SKILL.md')}
        self.assertEqual(set(ROLE_NAMES), discovered)
        for role, rel in ROLE_SKILLS.items():
            self.assertTrue((ROOT/'worker'/rel).is_file(), role)

    def test_mutating_task_acceptance_requires_fresh_reviewer_provenance_not_implementer(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/'DeepSeekAndDestroy'/'run'; run.mkdir(parents=True)
            contract=run/'task.md'; contract.write_text('# Task\nContract revision: r0001\n\n## Allowed source changes\n- `source.py`\n')
            report=run/'implementer.md'; report.write_text('Implementation complete.\n')
            gate=run/'implementer-gate.json'; gate.write_text(json.dumps({
                'format':'dsd-integrity-gate-v1','integrity_ok':True,'ok':True,'ready_for_interpretation':True,'errors':[],
                'role':'implementer','task':str(contract.resolve()),'report':str(report.resolve()),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
            }))
            clerk=run/'clerk.md'; clerk.write_text('Implementation looks complete; next route should be fresh review.\n')
            clerk_gate=run/'clerk-gate.json'; clerk_gate.write_text(json.dumps({
                'format':'dsd-integrity-gate-v1','integrity_ok':True,'ok':True,'ready_for_interpretation':True,'errors':[],
                'role':'evidence-clerk','task':str(contract.resolve()),'report':str(clerk.resolve()),'report_sha256':hashlib.sha256(clerk.read_bytes()).hexdigest(),
            }))
            state={'execution_status':'active','next_action':'decide','phases':{'p1':{'status':'in-progress','gate_barrier':{'status':'OPEN','snapshot':None},'tasks':{'U1':{
                'status':'process-exited',
                'current_contract':{'revision':1,'path':str(contract.resolve()),'sha256':hashlib.sha256(contract.read_bytes()).hexdigest()},
            }}}}}
            (run/'state.json').write_text(json.dumps(state))
            cp=self.run_cmd([PYTHON,str(ROOT/'scripts'/'dsd_state.py'),'accept-task','--run-root',str(run.resolve()),'--phase-id','p1','--task-id','U1','--evidence-gate',str(gate.resolve()),'--semantic-evidence',str(clerk.resolve()),'--semantic-evidence-gate',str(clerk_gate.resolve())])
            self.assertEqual(cp.returncode,2,cp.stdout+cp.stderr)
            self.assertIn('fresh Reviewer integrity gate',cp.stderr)

    def test_removed_semantic_regex_helpers_are_really_gone(self):
        for name in ('check_review_contract.py','_report.py','_report_contract.py','decision_packet.py'):
            self.assertFalse((ROOT/'scripts'/name).exists(), name)
        code='\n'.join(p.read_text() for p in (ROOT/'scripts').glob('*.py'))
        self.assertNotIn('fast_path_eligible',code)
        self.assertNotIn('ROLE_TERMINALS',code)


if __name__ == '__main__':
    unittest.main()
