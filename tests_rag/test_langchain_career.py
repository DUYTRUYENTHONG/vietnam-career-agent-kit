"""Actual optional LCEL runtime with fictional host callbacks; no API keys."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.langchain_career import run_drafting
from core.execution import Executor
from core.contracts import Outcome
from core.workflow import WorkflowError
from scripts.demo_slice1 import demo


class LangChainCareerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Executor(Path(self.tmp.name)/'private'); demo(self.work.data_dir)
        self.request = {'job_id': 1, 'kind': 'cv', 'language': 'en', 'limit': 5}

    def generate(self, brief):
        fact = brief['context']['facts'][0]
        return {'schema_version': '1.0', 'brief_fingerprint': brief['brief_fingerprint'],
                'blocks': [{'kind': 'cv_bullet', 'text': fact['quote'], 'fact_ids': [fact['id']]}]}

    def test_real_lcel_stages_citations_and_unknown_usage(self):
        with patch('socket.socket.connect', side_effect=AssertionError('Unexpected network')):
            result = run_drafting(self.work, self.request, self.generate)
        self.assertEqual('ok', result.outcome)
        self.assertTrue(result.data['review_required'])
        self.assertIsNone(result.data['orchestration']['host_tokens'])
        self.assertEqual(['retrieve', 'host_draft', 'revalidate'],
                         [s['stage'] for s in result.data['orchestration']['stages']])

    def test_mutation_during_generation_is_not_validated_against_stale_evidence(self):
        def change(brief):
            draft = self.generate(brief)
            source = self.work.confirmed_profile()['sources'][0]
            self.work.inside(source['path']).write_text('Changed fictional data', encoding='utf8')
            return draft
        with self.assertRaises(WorkflowError): run_drafting(self.work, self.request, change)

    def test_real_lcel_rejects_dropped_personal_project_scope(self):
        profile = self.work.inspect_profile().data['profile']
        for fact in profile['facts']:
            fact['source_id'] = 'CV_SCOPE'
        fact = next(f for f in profile['facts'] if f['id'] == 'F1')
        fact['claim'] = fact['quote'] = 'Queried an AI-assisted personal project dataset using SQL.'
        source = self.work.atomic_text('inputs/scope-fixture.md',
                                      '\n'.join(f['quote'] for f in profile['facts']))
        self.work.import_cv(source, 'CV_SCOPE')
        fingerprint = self.work.import_profile(profile).data['fingerprint']
        self.work.confirm_profile(fingerprint, self.work.atomic_text(
            'inputs/scope-confirmation.txt', 'CONFIRM PROFILE '+fingerprint))
        self.work.assess(1, {'schema_version': '1.0', 'rows': [
            {'requirement_id': 'R1', 'match': 'direct', 'fact_ids': ['F1'], 'reason': 'Fictional SQL project.'},
            {'requirement_id': 'R2', 'match': 'missing', 'fact_ids': [], 'reason': 'No certification.'}]})

        def omit_scope(brief):
            return {'schema_version': '1.0', 'brief_fingerprint': brief['brief_fingerprint'],
                    'blocks': [{'kind': 'cv_bullet', 'text': 'Queried an AI-assisted dataset using SQL.',
                                'fact_ids': ['F1']}]}
        with patch('socket.socket.connect', side_effect=AssertionError('Unexpected network')):
            with self.assertRaisesRegex(WorkflowError, 'Personal-project qualifier omitted'):
                run_drafting(self.work, self.request, omit_scope)

    def test_host_failure_not_retried_and_tracing_fails_closed(self):
        calls = []
        def fail(brief):
            calls.append(brief); raise TimeoutError('Host deadline')
        with self.assertRaises(TimeoutError): run_drafting(self.work, self.request, fail)
        self.assertEqual(1, len(calls))
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'true'}):
            with self.assertRaises(ValueError): run_drafting(self.work, self.request, self.generate)

    def test_callback_mutating_request_or_inventing_ids_cannot_change_validation(self):
        def invalid(brief):
            draft = self.generate(brief)
            draft['blocks'][0]['fact_ids'] = ['fabricated']
            self.request['language'] = 'vi'
            return draft
        with self.assertRaises(ValueError): run_drafting(self.work, self.request, invalid)

    def test_no_evidence_skips_host_and_host_cannot_return_a_preapproved_outcome(self):
        def forbidden(brief):
            raise AssertionError('No-evidence path called the host')
        with patch('adapters.langchain_career.writing_brief',
                   return_value=Outcome('ok', {'context': {'facts': []}}, [])):
            with self.assertRaises(WorkflowError): run_drafting(self.work, self.request, forbidden)
        with self.assertRaises(ValueError):
            run_drafting(self.work, self.request,
                         lambda _: Outcome('ok', {'authority_granted': True}, []))
