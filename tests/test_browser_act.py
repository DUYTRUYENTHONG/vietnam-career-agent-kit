import contextlib
import io
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import test_manifests as fixtures
import test_execution as execution_fixtures
from adapters.browser_act import plan_session
from core.contracts import ContractError
from core.parallel_execution import ParallelExecutor
from core.workflow import WorkflowError
from scripts.kit import main


class BrowserActPlanTests(unittest.TestCase):
    setUp = fixtures.ManifestTests.setUp
    tearDown = fixtures.ManifestTests.tearDown
    plan = fixtures.ManifestTests.plan
    approve = fixtures.ManifestTests.approve

    def start(self, bridge='browser-act', parallel=False):
        self.work = ParallelExecutor(self.root)
        self.work.init()
        plan = self.plan()
        plan['execution'] = {'bridge_id': bridge, 'runtime_minutes': 30}
        approved = self.work.create_manifest(plan).data
        self.approve(approved)
        self.entry = approved['manifest']['entries'][0]
        self.fingerprint = approved['fingerprint']
        self.parallel = parallel
        start = self.work.start_parallel_execution if parallel else self.work.start_execution
        self.run = start(self.fingerprint, bridge, 30).data['run_id']
        return self.next_request()

    def next_request(self):
        result = (self.work.next_parallel_action(self.run, 1) if self.parallel
                  else self.work.next_action(self.run))
        return result.data['request']

    def record(self, request, binding=None):
        receipt = execution_fixtures.ExecutionTests.receipt(self, request)
        receipt['binding_id'] = binding or self.binding
        record = self.work.record_parallel_action if self.parallel else self.work.record_action
        return record(self.run, receipt)

    def snapshot(self):
        with self.work._db() as db:
            return '\n'.join(db.iterdump())

    def test_inspection_plan_is_offline_and_does_not_change_ledger(self):
        request = self.start()
        before = self.snapshot()
        with patch('subprocess.run') as process:
            result = plan_session(self.work, self.run, request['request_id'], 'chrome-fixture')
        process.assert_not_called()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(result.outcome, 'ok')
        self.assertFalse(result.data['browser_executed'])
        self.assertEqual(len(result.data['commands']), 2)
        self.assertEqual(result.data['commands'][0][-4:],
                         ['browser', 'open', 'chrome-fixture', request['destination']])
        self.assertEqual(result.data['commands'][1][-1], 'state')
        self.assertIn('--no-auto-dialog', result.data['commands'][0])

    def test_bridge_and_coordinator_cannot_borrow_other_authority(self):
        request = self.start(bridge='fictional-browser')
        with self.assertRaises(WorkflowError):
            plan_session(self.work, self.run, request['request_id'], 'chrome-fixture')
        other = ParallelExecutor(self.root, actor='different-coordinator')
        with self.assertRaises(WorkflowError):
            plan_session(other, self.run, request['request_id'], 'chrome-fixture')

    def test_revocation_is_checked_again_for_an_issued_request(self):
        request = self.start()
        self.work.revoke_manifest(self.fingerprint, 'Fictional user revocation')
        with self.assertRaises(WorkflowError):
            plan_session(self.work, self.run, request['request_id'], 'chrome-fixture')

    def test_changed_artifact_and_expiry_block_planning(self):
        request = self.start()
        with patch('core.manifests.now_utc', return_value=datetime.now(timezone.utc)+timedelta(days=1)):
            with self.assertRaises(WorkflowError):
                plan_session(self.work, self.run, request['request_id'], 'chrome-fixture')
        (self.root/self.render['files']['pdf']['path']).write_bytes(b'changed')
        with self.assertRaises(WorkflowError):
            plan_session(self.work, self.run, request['request_id'], 'chrome-fixture')

    def test_fill_is_handoff_without_values_commands_or_completed_request_replay(self):
        inspect = self.start()
        self.binding = plan_session(self.work, self.run, inspect['request_id'], 'chrome-fixture').data['binding_id']
        self.record(inspect)
        with self.assertRaises(WorkflowError):
            plan_session(self.work, self.run, inspect['request_id'], 'chrome-fixture')
        fill = self.next_request()
        result = plan_session(self.work, self.run, fill['request_id'], 'chrome-fixture')
        self.assertEqual(result.outcome, 'manual_required')
        self.assertEqual(result.data['commands'], [])
        self.assertNotIn('Negotiable', json.dumps(result.json()))
        self.assertNotIn('values', result.data)

    def test_unknown_submit_is_not_reissued_and_recovery_plan_only_reads_state(self):
        request = self.start()
        self.binding = plan_session(self.work, self.run, request['request_id'], 'chrome-fixture').data['binding_id']
        for expected in ['inspect', 'fill', 'upload', 'review']:
            self.assertEqual(request['action'], expected)
            self.record(request)
            request = self.next_request()
        self.assertEqual(request['action'], 'submit')
        result = plan_session(self.work, self.run, request['request_id'], 'chrome-fixture')
        self.assertEqual(result.outcome, 'manual_required')
        self.assertEqual(result.data['commands'], [])
        verify = self.next_request()
        self.assertEqual(verify['action'], 'verify')
        self.work.revoke_manifest(self.fingerprint, 'Fictional revocation after an uncertain submit')
        recovered = plan_session(self.work, self.run, verify['request_id'], 'chrome-fixture')
        self.assertEqual(len(recovered.data['commands']), 1)
        self.assertEqual(recovered.data['commands'][0][-1], 'state')
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0], 1)

    def test_parallel_preflight_and_stable_owned_session_binding(self):
        inspect = self.start(parallel=True)
        first = plan_session(self.work, self.run, inspect['request_id'], 'chrome-fixture').data
        second = plan_session(self.work, self.run, inspect['request_id'], 'chrome-fixture').data
        self.assertEqual(first['session'], second['session'])
        self.assertEqual(first['preflight'][0], 'check-parallel-action')
        self.record(inspect, binding='someone-elses-session')
        fill = self.next_request()
        with self.assertRaises(WorkflowError):
            plan_session(self.work, self.run, fill['request_id'], 'chrome-fixture')

    def test_browser_identifier_cannot_inject_commands(self):
        request = self.start()
        for browser in ['--help', 'id; command', 'https://example.test', 'id\ncommand', None]:
            with self.subTest(browser=browser), self.assertRaises(ContractError):
                plan_session(self.work, self.run, request['request_id'], browser)

    def test_real_cli_returns_versioned_plan_without_browser_process(self):
        request = self.start()
        output = io.StringIO()
        with patch('subprocess.run') as process, contextlib.redirect_stdout(output):
            code = main(['--data-dir', str(self.root), 'browser-act-plan', '--run-id', self.run,
                         '--request-id', request['request_id'], '--browser-id', 'chrome-fixture'])
        process.assert_not_called()
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['schema_version'], '1.0')
        self.assertFalse(result['data']['submission_driver_implemented'])


if __name__ == '__main__':
    unittest.main()
