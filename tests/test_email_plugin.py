import base64
from email import policy
from email.parser import BytesParser
import json
import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import test_manifests as fixtures
from test_documents import fake_render
from core.execution import Executor
from core.workflow import WorkflowError
from adapters.email_execution import BRIDGE, EmailExecution, mailbox


class FakeGmail:
    def __init__(self):
        self.calls = []; self.account = {'id': 'fictional-google-id', 'email': 'candidate@example.com'}
        self.failure = False
        self.preflight_failure = False

    def profile(self): return dict(self.account)

    def send(self, raw, expected_account):
        if expected_account != self.profile(): raise ValueError('Account changed')
        self.calls.append(raw)
        if self.failure: raise TimeoutError('Fictional lost acknowledgement')
        return {'id': 'fictional-message', 'threadId': 'fictional-thread'}

    @contextmanager
    def prepare(self, account):
        if self.preflight_failure or account != self.profile():
            raise WorkflowError('blocked', 'Fictional identity preflight failure')
        yield lambda raw: self.send(raw, account)


class EmailPluginTests(unittest.TestCase):
    tearDown = fixtures.ManifestTests.tearDown
    plan = fixtures.ManifestTests.plan
    approve = fixtures.ManifestTests.approve

    def setUp(self):
        def pdf(content, directory, soffice=None):
            result = fake_render(content, directory, soffice)
            (directory / 'cv.pdf').write_bytes(b'%PDF-1.4\nFICTIONAL TEST ONLY')
            return result
        with patch.object(fixtures, 'fake_render', side_effect=pdf):
            fixtures.ManifestTests.setUp(self)
        self.work = Executor(self.root); self.work.init()
        self.client = FakeGmail(); self.engine = EmailExecution(self.work, self.client)

    def email_plan(self):
        plan = self.plan()
        plan['execution'] = {'bridge_id': BRIDGE, 'runtime_minutes': 30}
        entry = plan['entries'][0]
        entry['answers'] = {k: {'value': v, 'source': 'candidate_confirmed', 'fact_ids': [], 'kind': 'ordinary'}
            for k, v in {'sender': 'candidate@example.com', 'to': 'hiring@example.org',
                          'subject': 'Ứng tuyển - Fictional candidate', 'body': 'Fictional application.\nNo real candidate.'}.items()}
        entry['required_answers'] = list(entry['answers']); entry['consents'] = []
        return plan

    def start(self, plan=None):
        result = self.work.create_manifest(plan or self.email_plan()).data
        self.approve(result); self.fingerprint = result['fingerprint']
        return self.engine.start(self.fingerprint).data['run_id']

    def test_send_uses_exact_mime_and_one_canonical_immutable_receipt(self):
        run = self.start(); result = self.engine.send_next(run)
        self.assertEqual(result.data['state'], 'completed')
        parsed = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(self.client.calls[0]))
        self.assertEqual(str(parsed['To']), 'hiring@example.org')
        self.assertEqual(str(parsed['Subject']), 'Ứng tuyển - Fictional candidate')
        self.assertIsNone(parsed['Bcc']); self.assertIsNone(parsed['Cc'])
        self.assertEqual(len(list(parsed.iter_attachments())), 1)
        self.assertEqual(self.work.get_job(1)['state'], 'confirmed_submitted')
        self.assertFalse(result.data['receipt']['employer_delivery_verified'])
        self.engine.send_next(run)
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(self.work.tracker().data['observed_submissions'], 1)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE execution_submissions SET snapshot_json='{}'")

    def test_timeout_or_restart_never_resends(self):
        run = self.start(); self.client.failure = True
        self.assertEqual(self.engine.send_next(run).outcome, 'submission_unknown')
        self.assertEqual(self.work.get_job(1)['state'], 'submission_uncertain')
        EmailExecution(self.work, self.client).send_next(run)
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(self.work.tracker().data['observed_submissions'], 0)

    def test_identity_preflight_failure_creates_no_attempt_and_can_be_corrected(self):
        run=self.start();self.client.preflight_failure=True
        with self.assertRaises(WorkflowError):self.engine.send_next(run)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],0)
        self.assertNotEqual(self.work.get_job(1)['state'],'submission_uncertain')
        self.assertEqual(self.client.calls,[])
        self.client.preflight_failure=False
        self.assertEqual(self.engine.send_next(run).outcome,'ok')

    def test_approval_required_and_mailbox_switch_or_revocation_blocks(self):
        result = self.work.create_manifest(self.email_plan()).data
        with self.assertRaises(WorkflowError): self.engine.start(result['fingerprint'])
        self.approve(result)
        run = self.engine.start(result['fingerprint']).data['run_id']
        self.client.account['id'] = 'switched-account'
        with self.assertRaises(WorkflowError): self.engine.send_next(run)
        self.client.account['id'] = 'fictional-google-id'
        self.work.revoke_manifest(result['fingerprint'], 'Fictional revocation')
        with self.assertRaises(WorkflowError): self.engine.send_next(run)
        self.assertEqual(self.client.calls, [])

    def test_changed_attachment_and_browser_route_are_blocked(self):
        run = self.start()
        with self.assertRaises(WorkflowError): self.work.next_action(run)
        path = self.root / self.render['files']['pdf']['path']; path.write_bytes(b'changed')
        with self.assertRaises(WorkflowError): self.engine.send_next(run)
        self.assertEqual(self.client.calls, [])

    def test_generic_start_cannot_convert_email_scope_to_browser_actions(self):
        from core.parallel_execution import ParallelExecutor
        self.work = ParallelExecutor(self.root); self.work.init()
        result = self.work.create_manifest(self.email_plan()).data; self.approve(result)
        for start in (self.work.start_execution, self.work.start_parallel_execution):
            with self.assertRaises(WorkflowError): start(result['fingerprint'], BRIDGE, 30)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_runs').fetchone()[0], 0)

    def test_header_injection_display_names_and_new_consents_rejected(self):
        for address in ['a@example.com\r\nBcc:b@example.org', 'Name <a@example.com>', 'a@example.com,b@example.org']:
            with self.subTest(address=address), self.assertRaises(WorkflowError): mailbox(address)
        for mutate in ['subject', 'consent', 'sender']:
            plan = self.email_plan()
            if mutate == 'subject': plan['entries'][0]['answers']['subject']['value'] = 'Hi\nBcc:another'
            elif mutate == 'sender': plan['entries'][0]['answers']['sender']['value'] = 'other@example.org'
            else: plan['entries'][0]['consents'] = [{'id':'new','text':'New agreement','choice':True}]
            result = self.work.create_manifest(plan).data; self.approve(result)
            with self.subTest(mutate=mutate), self.assertRaises(WorkflowError): self.engine.start(result['fingerprint'])
        self.assertEqual(self.client.calls, [])
