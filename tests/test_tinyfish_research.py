import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adapters.providers.tinyfish import TinyFish
from adapters.providers.tinyfish_research import fetch, preview
from core.execution import Executor
from core.workflow import WorkflowError
from test_provider_contracts import plan
from test_tinyfish import dns, page


class TinyFishResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-tinyfish-')
        self.addCleanup(self.temp.cleanup)
        self.work = Executor(Path(self.temp.name)/'workspace'); self.work.init()
        self.raw = plan()
        self.fingerprint = preview(self.raw).data['fingerprint']
        self.calls = []
        def transport(method, url, payload):
            self.calls.append(payload)
            with self.work._db() as db:
                self.assertEqual(db.execute("SELECT state FROM provider_tasks").fetchone()[0], 'intent')
                self.assertEqual(db.execute('SELECT requests FROM research_plans').fetchone()[0], 1)
            return {'results': [page(u) for u in payload['urls']]}
        self.provider = TinyFish(transport, resolver=dns)

    def test_preview_and_approval_do_not_disclose(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('network')):
            self.assertEqual(preview(self.raw).data['network_calls'], 0)
        with self.assertRaises(WorkflowError): fetch(self.work, self.raw, 'wrong', self.provider)
        self.assertEqual(self.calls, [])

    def test_intent_precedes_post_and_success_replays_without_credentials(self):
        result = fetch(self.work, self.raw, self.fingerprint, self.provider)
        self.assertEqual(result.outcome, 'ok')
        self.assertEqual(result.data['applications'], 0)
        evidence = result.data['evidence'][0]
        target = self.work.inside(evidence['artifact_path'])
        captured = json.loads(target.read_text(encoding='utf8'))
        self.assertEqual(captured['provider'], 'tinyfish-fetch')
        self.assertEqual(captured['liveness'], 'unverified')
        target.unlink()  # A committed DB record repairs a crash before file export.
        with patch('adapters.providers.tinyfish_research.TinyFish', side_effect=AssertionError('no credentials')):
            replay = fetch(self.work, self.raw, self.fingerprint)
        self.assertEqual(replay.data['evidence'], result.data['evidence'])
        self.assertTrue(target.exists())
        self.assertEqual(len(self.calls), 1)
        target.write_text('tampered', encoding='utf8')
        with self.assertRaises(WorkflowError): fetch(self.work, self.raw, self.fingerprint)

    def test_uncertain_never_retries_even_changed_plan(self):
        def fail(*args):
            self.calls.append(args)
            raise RuntimeError('SECRET')
        self.provider.transport = fail
        first = fetch(self.work, self.raw, self.fingerprint, self.provider)
        self.assertEqual(first.data['state'], 'uncertain')
        self.assertNotIn('SECRET', json.dumps(first.json()))
        fetch(self.work, self.raw, self.fingerprint, self.provider)
        changed = dict(self.raw, plan_id='changed')
        with self.assertRaises(WorkflowError):
            fetch(self.work, changed, preview(changed).data['fingerprint'], self.provider)
        self.assertEqual(len(self.calls), 1)

    def test_partial_result_keeps_valid_evidence(self):
        self.raw['urls'].append('https://jobs.example.test/role?id=2')
        self.provider.transport = lambda *a: {'results': [page(self.raw['urls'][0])], 'errors': ['SECRET']}
        result = fetch(self.work, self.raw, preview(self.raw).data['fingerprint'], self.provider)
        self.assertEqual(result.outcome, 'manual_required')
        self.assertEqual(len(result.data['evidence']), 1)
        self.assertNotIn('SECRET', json.dumps(result.json()))

    def test_process_interruption_leaves_nonreplayable_intent(self):
        def crash(*args):
            self.calls.append(args)
            raise KeyboardInterrupt()
        self.provider.transport = crash
        with self.assertRaises(KeyboardInterrupt):
            fetch(self.work, self.raw, self.fingerprint, self.provider)
        replay = fetch(self.work, self.raw, self.fingerprint, self.provider)
        self.assertEqual(replay.data['state'], 'intent')
        self.assertEqual(replay.outcome, 'manual_required')
        self.assertEqual(len(self.calls), 1)

    def test_budget_rejected_before_post(self):
        self.raw['urls'].append('https://jobs.example.test/role?id=2')
        self.raw['limits']['credit_reservation'] = 1
        with self.assertRaises(WorkflowError):
            fetch(self.work, self.raw, preview(self.raw).data['fingerprint'], self.provider)
        self.assertEqual(self.calls, [])
