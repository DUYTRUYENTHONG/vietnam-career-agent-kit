"""Fictional cleanup delays must not hold unrelated application lanes."""
import threading
import unittest
from unittest.mock import patch

import test_parallel_execution as fixtures
from core.parallel_execution import run_parallel_with_bridge
from core.contracts import ContractError


class ParallelCleanupProgressTests(unittest.TestCase):
    setUp = fixtures.ParallelExecutionTests.setUp
    tearDown = fixtures.ParallelExecutionTests.tearDown
    start = fixtures.ParallelExecutionTests.start
    receipt = fixtures.ParallelExecutionTests.receipt
    plan = fixtures.ParallelExecutionTests.plan
    approve = fixtures.ParallelExecutionTests.approve

    def ack(self, item):
        return {'schema_version': '1.0', 'request_id': item['request_id'],
                'bridge_id': item['bridge_id'], 'binding_id': item['binding_id'],
                'status': 'closed', 'agent_owned': True, 'cleanup_requested': True}

    def test_slow_confirmed_tab_cleanup_does_not_hold_other_application_lane(self):
        run = self.start(2)
        cleanup_started = threading.Event()
        other_verified = threading.Event()
        progressed = []
        closes = []
        calls = []
        test = self

        class Bridge:
            def perform(self, request):
                calls.append((request['job_id'], request['action']))
                if request['job_id'] == 2 and request['action'] == 'inspect':
                    if not cleanup_started.wait(10):
                        raise TimeoutError('Fictional first cleanup never started')
                if request['job_id'] == 2 and request['action'] == 'verify':
                    other_verified.set()
                return test.receipt(request)

            def close_application_tab(self, request):
                closes.append(request['job_id'])
                if request['job_id'] == 1:
                    cleanup_started.set()
                    progressed.append(other_verified.wait(3))
                return test.ack(request)

        result = run_parallel_with_bridge(self.work, run, Bridge(), action_timeout_seconds=20)
        self.assertEqual([True], progressed, 'Cleanup held the unrelated lane until its wait expired')
        self.assertEqual('completed', result.data['state'])
        self.assertEqual([], result.data['worker_errors'])
        self.assertEqual([], result.data['cleanup']['requests'])
        self.assertEqual([1, 2], sorted(closes))
        self.assertEqual(1, calls.count((1, 'submit')))
        self.assertEqual(1, calls.count((2, 'submit')))
        with self.work._db() as db:
            self.assertEqual(2, db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0])
            self.assertEqual(2, db.execute("SELECT count(*) FROM execution_actions WHERE action='cleanup'").fetchone()[0])

    def test_stalled_cleanup_keeps_capacity_and_ignores_late_receipt(self):
        run = self.start(2, workers=1)
        release, finished = threading.Event(), threading.Event()
        closes = []
        test = self

        class Bridge:
            def perform(self, request):
                return test.receipt(request)

            def close_application_tab(self, request):
                closes.append(request['job_id'])
                release.wait(10)
                finished.set()
                return test.ack(request)

        try:
            result = run_parallel_with_bridge(self.work, run, Bridge(), action_timeout_seconds=1)
            self.assertEqual('completed', result.data['state'])
            self.assertEqual([], result.data['worker_errors'])
            self.assertEqual([1], closes)
            self.assertEqual([1], [r['job_id'] for r in result.data['cleanup_quarantined_requests']])
            self.assertFalse(result.data['cleanup_quarantined_requests'][0]['remote_termination_confirmed'])
            self.assertEqual(2, len(result.data['cleanup']['requests']))
            resumed = run_parallel_with_bridge(self.work, run, Bridge(), action_timeout_seconds=1)
            self.assertEqual([1], closes, 'Restart must not replay an uncertain tab close')
            self.assertEqual(1, len(resumed.data['cleanup_quarantined_requests']))
            release.set()
            self.assertTrue(finished.wait(5))
            with self.work._db() as db:
                self.assertEqual(2, db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0])
                self.assertEqual(0, db.execute("SELECT count(*) FROM execution_actions WHERE action='cleanup'").fetchone()[0])
            # An explicit observed receipt reconciles the old intent; no intent
            # deletion or replay is needed to finish the remaining owned tab.
            item = self.work.parallel_cleanup(run).data['requests'][0]
            self.work.record_parallel_cleanup(run, self.ack(item))
            reconciled = run_parallel_with_bridge(self.work, run, Bridge(), action_timeout_seconds=1)
            self.assertEqual([1, 2], closes)
            self.assertEqual([], reconciled.data['cleanup']['requests'])
        finally:
            release.set()

    def test_cleanup_receipt_cannot_acknowledge_another_binding(self):
        run = self.start(2)
        test = self

        class Bridge:
            def perform(self, request):
                return test.receipt(request)

            def close_application_tab(self, request):
                return {**test.ack(request), 'binding_id': 'another-tab'}

        result = run_parallel_with_bridge(self.work, run, Bridge())
        self.assertEqual('completed', result.data['state'])
        self.assertEqual(2, len(result.data['cleanup']['requests']))
        self.assertTrue(any('cleanup failed (ValueError)' in issue for issue in result.issues))
        with self.work._db() as db:
            self.assertEqual(0, db.execute("SELECT count(*) FROM execution_actions WHERE action='cleanup'").fetchone()[0])

    def test_concurrent_cleanup_callbacks_keep_all_receipt_writes_on_coordinator(self):
        run = self.start(2, workers=2)
        barrier = threading.Barrier(2, timeout=10)
        writers, callbacks = [], []
        test = self
        record_action = self.work.record_parallel_action
        record_cleanup = self.work.record_parallel_cleanup

        def action_writer(*args):
            writers.append(threading.get_ident())
            return record_action(*args)

        def cleanup_writer(*args):
            writers.append(threading.get_ident())
            return record_cleanup(*args)

        class Bridge:
            def perform(self, request):
                return test.receipt(request)

            def close_application_tab(self, request):
                callbacks.append(threading.get_ident())
                barrier.wait()
                return test.ack(request)

        with patch.object(self.work, 'record_parallel_action', side_effect=action_writer), \
                patch.object(self.work, 'record_parallel_cleanup', side_effect=cleanup_writer):
            result = run_parallel_with_bridge(self.work, run, Bridge(), cleanup_workers=2)
        self.assertEqual({threading.get_ident()}, set(writers))
        self.assertEqual(2, len(set(callbacks)))
        self.assertNotIn(threading.get_ident(), callbacks)
        self.assertEqual([], result.data['cleanup']['requests'])
        self.assertEqual([], result.data['worker_errors'])

    def test_invalid_cleanup_capacity_fails_before_any_dispatch(self):
        run = self.start(1, workers=1)
        for value in [0, -1, True, 1.5, 11, 2]:
            with self.subTest(value=value), self.assertRaises(ContractError):
                run_parallel_with_bridge(self.work, run, object(), cleanup_workers=value)
        with self.work._db() as db:
            self.assertEqual(0, db.execute('SELECT count(*) FROM execution_actions').fetchone()[0])
        self.assertFalse((self.root / 'execution/cleanup-intents').exists())

    def test_changed_confirmation_evidence_still_blocks_cleanup_ack(self):
        run = self.start(1)
        test = self

        class Bridge:
            def perform(self, request):
                return test.receipt(request)

            def close_application_tab(self, request):
                (test.root / request['screenshot']['path']).write_bytes(b'changed')
                return test.ack(request)

        result = run_parallel_with_bridge(self.work, run, Bridge())
        self.assertEqual('completed', result.data['state'])
        self.assertEqual(1, len(result.data['cleanup']['blocked']))
        with self.work._db() as db:
            self.assertEqual(1, db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0])
            self.assertEqual(0, db.execute("SELECT count(*) FROM execution_actions WHERE action='cleanup'").fetchone()[0])


if __name__ == '__main__':
    unittest.main()
