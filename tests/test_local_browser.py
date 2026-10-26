import copy
import unittest
from unittest.mock import patch

import test_manifests as fixtures
import test_parallel_execution as parallel_fixtures
from test_tinyfish_forms import form
from core.parallel_execution import run_parallel_with_bridge
from core.workflow import WorkflowError
from adapters.local_browser import BRIDGE, LocalBrowserBridge, validate_plans


class LocalBrowserTests(unittest.TestCase):
    def setUp(self):
        fixtures.ManifestTests.setUp(self)
        mocked = patch('adapters.local_browser.public_host')
        mocked.start(); self.addCleanup(mocked.stop)
    tearDown = fixtures.ManifestTests.tearDown
    plan = fixtures.ManifestTests.plan
    approve = fixtures.ManifestTests.approve
    start = parallel_fixtures.ParallelExecutionTests.start
    receipt = parallel_fixtures.ParallelExecutionTests.receipt

    def setup_bridge(self, count=2):
        run = self.start(count, workers=count, bridge_id=BRIDGE)
        plans = {str(job): form(entry) for job, entry in self.entries.items()}
        test = self
        class Driver:
            def open(self, session, plan): return {'url': plan['destination']}
            def perform(self, session, plan, request, guard):
                guard(); result = test.receipt(request)
                for key in ('schema_version', 'request_id', 'binding_id'): result.pop(key)
                return result
            def release(self, session): pass
        return run, plans, LocalBrowserBridge(self.work, run, plans, driver=Driver())

    def test_isolated_full_protocol_and_confirmed_cleanup_share_tracker(self):
        run, plans, bridge = self.setup_bridge()
        for job in (1,2): bridge.open(job)
        self.assertEqual(len({s['binding_id'] for s in bridge.sessions.values()}), 2)
        result = run_parallel_with_bridge(self.work, run, bridge)
        self.assertEqual(result.data['state'], 'completed', result.json())
        self.assertEqual(self.work.tracker().data['observed_submissions'], 2)
        self.assertTrue(all(s['closed'] for s in bridge.sessions.values()))

    def test_wrong_mapping_accountless_session_replay_and_restart_rejected(self):
        run, plans, bridge = self.setup_bridge(1)
        invalid = copy.deepcopy(plans); invalid['1']['identity']['employer']['text'] = 'Changed'
        with self.assertRaises(WorkflowError): validate_plans(self.work, self.fingerprint, invalid)
        bridge.open(1)
        with self.assertRaises(WorkflowError): bridge.open(1)
        with self.assertRaises(WorkflowError): LocalBrowserBridge(self.work, run, plans, driver=bridge.driver)
        request = self.work.next_parallel_action(run,1).data['request']
        bridge.perform(request)
        with self.assertRaises(WorkflowError): bridge.perform(request)

    def test_revocation_blocks_dispatch_and_early_cleanup(self):
        run, plans, bridge = self.setup_bridge(1); bridge.open(1)
        request = self.work.next_parallel_action(run,1).data['request']
        self.work.revoke_manifest(self.fingerprint, 'Fictional revocation')
        with self.assertRaises(WorkflowError): bridge.perform(request)
        with self.assertRaises(WorkflowError): bridge.close_application_tab({'job_id':1,'binding_id':'guessed'})

    def test_dns_and_unstarted_launch_failures_leave_no_replacement_lock(self):
        run, plans, bridge = self.setup_bridge(1)
        with patch('adapters.local_browser.public_host', side_effect=WorkflowError('blocked','DNS rejected')):
            with self.assertRaises(WorkflowError): bridge.open(1)
        self.assertEqual(bridge.sessions,{})
        self.assertEqual(list(bridge.root.glob('*.intent.json')),[])
        with patch.object(bridge.driver,'open',side_effect=RuntimeError('Fictional launch failure')):
            with self.assertRaises(RuntimeError): bridge.open(1)
        self.assertEqual(bridge.sessions,{})
        self.assertEqual(list(bridge.root.glob('*.intent.json')),[])

    def test_client_is_stopped_even_when_browser_close_fails(self):
        import asyncio
        from adapters.local_browser import LocalForms
        from unittest.mock import AsyncMock
        browser=type('Browser',(),{})();browser.close=AsyncMock(side_effect=RuntimeError('Fictional close failure'))
        client=type('Client',(),{})();client.stop=AsyncMock()
        with self.assertRaises(RuntimeError): asyncio.run(LocalForms._dispose({'browser':browser,'client':client}))
        client.stop.assert_awaited_once()

    def test_failed_disposal_retains_connection_and_unstarted_intent(self):
        from adapters.local_browser import LocalForms
        from unittest.mock import AsyncMock
        driver=LocalForms(self.root)
        browser=type('Browser',(),{})();browser.close=AsyncMock(side_effect=RuntimeError('Fictional close failure'))
        client=type('Client',(),{})();client.stop=AsyncMock()
        connection={'browser':browser,'client':client};driver.connections['session']=connection
        with self.assertRaises(RuntimeError):driver.release({'session_id':'session'})
        self.assertIs(driver.connections['session'],connection)
        browser.close.side_effect=None
        driver.release({'session_id':'session'})
        self.assertNotIn('session',driver.connections)
        driver.loop.call_soon_threadsafe(driver.loop.stop)
        run,plans,bridge=self.setup_bridge(1)
        with patch.object(bridge.driver,'open',side_effect=RuntimeError('Fictional setup failure')), \
             patch.object(bridge.driver,'release',side_effect=RuntimeError('Fictional cleanup failure')):
            with self.assertRaises(RuntimeError):bridge.open(1)
        self.assertIn('1',bridge.sessions)
        self.assertTrue((bridge.root/'1.intent.json').exists())
