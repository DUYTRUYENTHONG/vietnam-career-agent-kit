"""Fictional orchestration and read-model regression tests."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_execution as execution_fixtures
from core.workflow import WorkflowError


class PipelineTests(unittest.TestCase):
    setUp = execution_fixtures.ExecutionTests.setUp
    tearDown = execution_fixtures.ExecutionTests.tearDown
    plan = execution_fixtures.ExecutionTests.plan
    approve = execution_fixtures.ExecutionTests.approve
    start = execution_fixtures.ExecutionTests.start
    receipt = execution_fixtures.ExecutionTests.receipt
    step = execution_fixtures.ExecutionTests.step
    until_submit = execution_fixtures.ExecutionTests.until_submit

    def test_runtime_expiry_during_validation_blocks_issued_action(self):
        from datetime import datetime, timedelta, timezone
        run = self.start()
        request = self.work.next_action(run).data['request']
        now = datetime.now(timezone.utc)
        with patch('core.execution.now_utc', side_effect=[now, now + timedelta(hours=1)]):
            with self.assertRaises(WorkflowError):
                self.work.check_action(run, request['request_id'])

    def test_advance_commits_receipt_then_returns_one_next_request(self):
        run = self.start()
        request = self.work.next_action(run).data['request']
        result = self.work.advance_execution(run, self.receipt(request))
        self.assertTrue(result.data['receipt_recorded'])
        self.assertEqual('fill', result.data['request']['action'])
        with self.assertRaises(WorkflowError):
            self.work.advance_execution(run, self.receipt(request))

    def test_advance_preserves_acknowledgement_when_next_action_is_blocked(self):
        run = self.start()
        request = self.work.next_action(run).data['request']
        self.work.revoke_manifest(self.fingerprint, 'Fictional revocation')
        result = self.work.advance_execution(run, self.receipt(request))
        self.assertEqual('blocked', result.outcome)
        self.assertTrue(result.data['receipt_recorded'])
        self.assertNotIn('request', result.data)
        self.assertEqual('active', self.work.execution_status(run).data['state'])

    def test_tracker_is_read_only_and_distinguishes_attempt_from_confirmation(self):
        run = self.start()
        self.until_submit(run)
        with patch.object(self.work, 'hash_file', side_effect=AssertionError('tracker must not hash artifacts')):
            result = self.work.tracker()
        row = result.data['jobs'][0]
        self.assertEqual('submission_uncertain', row['state'])
        self.assertEqual('submit', row['latest_action'])
        self.assertIn('verify', row['next_step'].lower())
        self.assertEqual(0, result.data['observed_submissions'])
        self.assertEqual(1, result.data['attempts'])
        request = self.work.next_action(run).data['request']
        self.work.record_action(run, self.receipt(request))
        result = self.work.tracker()
        self.assertEqual(1, result.data['observed_submissions'])
        self.assertEqual('confirmed_submitted', result.data['jobs'][0]['state'])
        self.assertFalse(result.data['validates_artifacts'])

    def test_tracker_cli_exports_a_catch_up_table(self):
        self.start()
        cli = Path(__file__).resolve().parents[1] / 'scripts/kit.py'
        completed = subprocess.run([sys.executable, str(cli), '--data-dir', str(self.root),
            'tracker', '--format', 'md', '--output', 'reports/tracker.md'],
            capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        exported = json.loads(completed.stdout)['data']
        content = (self.root / exported['path']).read_text(encoding='utf8')
        for label in ['Employer / role', 'Source', 'Status', 'Next step', 'Updated (UTC)', 'not revalidated']:
            self.assertIn(label, content)

    def test_real_cli_combined_loop_uses_thirteen_calls_and_lost_submit_recovers(self):
        run=self.start()
        cli=Path(__file__).resolve().parents[1]/'scripts/kit.py'
        calls=[]
        def invoke(*args):
            calls.append(args[0])
            result=subprocess.run([sys.executable,str(cli),'--data-dir',str(self.root),*args],
                capture_output=True,encoding='utf8',timeout=15)
            self.assertEqual(0,result.returncode,result.stdout+result.stderr)
            return json.loads(result.stdout)['data']
        current=invoke('next-action','--run-id',run)
        for phase in ['inspect','fill','upload','review','submit','verify']:
            request=current['request']
            self.assertEqual(phase,request['action'])
            invoke('check-action','--run-id',run,'--request-id',request['request_id'])
            file=self.root/'receipt.json';file.write_text(json.dumps(self.receipt(request)),encoding='utf8')
            current=invoke('advance-execution','--run-id',run,'--receipt',str(file))
        self.assertEqual('completed',current['state'])
        self.assertEqual(13,len(calls))
        # A lost combined response after review has already reserved submit.
        self.tearDown();self.setUp();run=self.start()
        for _ in range(3):self.step(run)
        review=self.work.next_action(run).data['request']
        self.assertEqual('submit',self.work.advance_execution(run,self.receipt(review)).data['request']['action'])
        self.assertEqual('verify',self.work.next_action(run).data['request']['action'])
        with self.work._db() as db:
            self.assertEqual(1,db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0])
