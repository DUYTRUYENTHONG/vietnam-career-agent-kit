"""Fictional standing-authority launch and interruption behavior."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_authorization as authorization_fixtures
from core.workflow import WorkflowError


class LaunchTests(unittest.TestCase):
    setUp=authorization_fixtures.AuthorizationTests.setUp
    tearDown=authorization_fixtures.AuthorizationTests.tearDown
    plan=authorization_fixtures.AuthorizationTests.plan
    scope=authorization_fixtures.AuthorizationTests.scope
    authorize=authorization_fixtures.AuthorizationTests.authorize
    manifest=authorization_fixtures.AuthorizationTests.manifest
    receipt=authorization_fixtures.AuthorizationTests.receipt

    def test_launch_derives_authority_starts_and_issues_first_action(self):
        grant=self.authorize();child=self.manifest()
        result=self.work.launch_execution(child,grant,'fictional-browser',30)
        self.assertTrue(result.data['authority_recorded'])
        self.assertTrue(result.data['run_started'])
        self.assertEqual(result.data['request']['action'],'inspect')
        self.assertEqual(result.data['request']['manifest_fingerprint'],child)
        self.assertEqual(self.work.check_authorization(grant).data['allocated_submissions'],1)
        self.assertEqual(self.work.check_manifest(child).data['approval_basis'],'standing_authorization')

    def test_invalid_bridge_or_unapproved_authority_cannot_allocate_or_launch(self):
        grant=self.work.create_authorization(self.scope()).data['fingerprint'];child=self.manifest()
        with self.assertRaises(WorkflowError):self.work.launch_execution(child,grant,'fictional-browser',30)
        grant=self.authorize()
        with self.assertRaises(WorkflowError):self.work.launch_execution(child,grant,'other-browser',30)
        self.assertEqual(self.work.check_authorization(grant).data['allocated_submissions'],0)
        with self.work._db() as db:self.assertEqual(db.execute('SELECT count(*) FROM execution_runs').fetchone()[0],0)

    def test_repeat_launch_reports_existing_run_without_replaying_or_reallocating(self):
        grant=self.authorize();child=self.manifest()
        first=self.work.launch_execution(child,grant,'fictional-browser',30)
        repeated=self.work.launch_execution(child,grant,'fictional-browser',30)
        self.assertEqual(repeated.outcome,'needs_input')
        self.assertTrue(repeated.data['existing_run'])
        self.assertEqual(repeated.data['run_id'],first.data['run_id'])
        self.assertEqual(repeated.data['pending_action'],'inspect')
        self.assertNotIn('request',repeated.data)
        self.assertEqual(self.work.check_authorization(grant).data['allocated_submissions'],1)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_runs').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM execution_actions').fetchone()[0],1)

    def test_first_request_failure_preserves_committed_run_for_reconciliation(self):
        grant=self.authorize();child=self.manifest()
        with patch.object(self.work,'next_action',side_effect=WorkflowError('blocked','Fictional interruption')):
            result=self.work.launch_execution(child,grant,'fictional-browser',30)
        self.assertEqual(result.outcome,'blocked')
        self.assertTrue(result.data['authority_recorded'])
        self.assertTrue(result.data['run_started'])
        self.assertEqual(self.work.execution_status(result.data['run_id']).data['state'],'active')
        self.assertNotIn('request',result.data)

    def test_real_cli_launch_does_not_clear_a_host_confirmation_blocker(self):
        grant=self.authorize();child=self.manifest()
        cli=Path(__file__).resolve().parents[1]/'scripts/kit.py'
        result=subprocess.run([sys.executable,str(cli),'--data-dir',str(self.root),
            'launch-execution','--fingerprint',child,'--authorization',grant,
            '--bridge-id','fictional-browser','--runtime-minutes','30'],
            capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        launched=json.loads(result.stdout)['data']
        receipt=self.receipt(launched['request'])
        receipt['form']['blockers']=['host_specific_disclosure_confirmation_required']
        with self.assertRaises(WorkflowError):self.work.record_action(launched['run_id'],receipt)
        with self.work._db() as db:self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],0)
