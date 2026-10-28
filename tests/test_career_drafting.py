"""Draft provenance checks do not certify semantic truth or grant authority."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from core.career_drafting import writing_brief, check_draft
from core.execution import Executor
from core.workflow import WorkflowError
from scripts.demo_slice1 import demo


class DraftingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Executor(Path(self.tmp.name)/'private')
        demo(self.work.data_dir)
        self.request = {'job_id': 1, 'kind': 'email', 'language': 'en', 'limit': 5}

    def draft(self, brief):
        fact = brief['context']['facts'][0]
        return {'schema_version': '1.0', 'brief_fingerprint': brief['brief_fingerprint'],
                'blocks': [{'kind': 'subject', 'text': 'Application for the advertised role', 'fact_ids': []},
                           {'kind': 'body', 'text': fact['quote'], 'fact_ids': [fact['id']]}]}

    def test_valid_cited_email_stays_pending_without_writes(self):
        brief = writing_brief(self.work, **self.request).data
        self.assertEqual(['subject', 'body'], [b['kind'] for b in brief['output_contract']['blocks']])
        draft = json.loads(json.dumps(brief['output_contract']))
        draft['brief_fingerprint'] = brief['brief_fingerprint']
        fact = brief['context']['facts'][0]
        draft['blocks'][1].update(text=fact['quote'], fact_ids=[fact['id']])
        result = check_draft(self.work, self.request, draft)
        self.assertEqual('ok', result.outcome)
        self.assertTrue(result.data['review_required'])
        self.assertFalse(result.data['semantic_truth_verified'])
        self.assertFalse(result.data['authority_granted'])
        self.assertEqual(draft, result.data['draft'])
        self.assertEqual(0, result.data['model_api_calls'])

    def test_invalid_citations_and_empty_claims_are_rejected(self):
        brief = writing_brief(self.work, **self.request).data
        for ids in ([], ['unknown'], [brief['context']['facts'][0]['id']]*2):
            draft = self.draft(brief)
            draft['blocks'][1]['fact_ids'] = ids
            with self.assertRaises(ValueError): check_draft(self.work, self.request, draft)
        draft = self.draft(brief); draft['sent'] = True
        with self.assertRaises(ValueError): check_draft(self.work, self.request, draft)
        draft = self.draft(brief); draft['blocks'][0]['text'] = 'Subject\nInjected header'
        with self.assertRaises(ValueError): check_draft(self.work, self.request, draft)

    def test_changed_source_or_request_invalidates_the_draft(self):
        brief = writing_brief(self.work, **self.request).data
        draft = self.draft(brief)
        changed = dict(self.request, language='vi')
        with self.assertRaises(WorkflowError): check_draft(self.work, changed, draft)
        source = self.work.confirmed_profile()['sources'][0]
        self.work.inside(source['path']).write_text('Altered fictional source', encoding='utf8')
        with self.assertRaises(WorkflowError): check_draft(self.work, self.request, draft)

    def test_cv_bullets_and_limits_and_no_matching_evidence(self):
        request = dict(self.request, kind='cv')
        brief = writing_brief(self.work, **request).data
        draft = self.draft(brief)
        draft['blocks'] = [dict(draft['blocks'][1], kind='cv_bullet')]
        self.assertEqual('ok', check_draft(self.work, request, draft).outcome)
        ids = [f['id'] for f in brief['context']['facts']]
        self.assertGreater(len(ids), 1)
        draft['blocks'][0]['fact_ids'] = ids
        with self.assertRaises(ValueError): check_draft(self.work, request, draft)
        draft['blocks'][0]['fact_ids'] = ids[:1]
        draft['blocks'][0]['text'] = 'x'*4001
        with self.assertRaises(ValueError): check_draft(self.work, request, draft)
        for options in ({'job_id': True}, {'kind': 'send'}, {'language': 'de'}, {'limit': True}):
            with self.assertRaises(ValueError): writing_brief(self.work, **dict(request, **options))
        with self.assertRaises(ValueError): check_draft(self.work, {}, draft)

    def test_citation_is_not_a_semantic_approval(self):
        brief = writing_brief(self.work, **self.request).data
        draft = self.draft(brief)
        draft['blocks'][1]['text'] = 'Unsupported invented achievement with a valid citation.'
        result = check_draft(self.work, self.request, draft)
        self.assertFalse(result.data['semantic_truth_verified'])
        self.assertTrue(result.data['review_required'])
        self.assertIn('independent', result.issues[0])

    def test_cli_roundtrip_checks_private_packet(self):
        cli = Path(__file__).resolve().parents[1]/'scripts/kit.py'
        command = [sys.executable, str(cli), '--data-dir', str(self.work.data_dir)]
        result = subprocess.run(command+['career-writing-brief', '--job-id', '1'],
                                capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, result.returncode, result.stdout+result.stderr)
        brief = json.loads(result.stdout)['data']
        packet = {'request': self.request, 'draft': self.draft(brief)}
        self.work.atomic_text('draft.json', json.dumps(packet))
        result = subprocess.run(command+['career-check-draft', '--file', str(self.work.inside('draft.json'))],
                                capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, result.returncode, result.stdout+result.stderr)
        self.assertTrue(json.loads(result.stdout)['data']['review_required'])
