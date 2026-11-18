"""First-layer machine review never produces human labels or approvals."""
import unittest
from core import cv_review_agents as a, cv_planning as c, tailor_benchmark as b
from tests import test_tailor_benchmark as fixture


class ReviewerTests(unittest.TestCase):
    setUp = fixture.TailorBenchmarkTests.setUp

    def requests(self):
        c.prepare(self.root, [self.case], 'prepared')
        return a.prepare(self.root, 'prepared', 'requests', [
            {'id': 'S1', 'text': 'Built Python API tests with AI assistance.', 'fact_id': 'F1'}])

    def response(self, role='evidence'):
        inputs = b.read_json(self.root/'requests/inputs.json')
        return {'role': role, 'reviewer_type': 'model', 'input_sha256': b.binding(inputs),
            'model_id': 'unknown', 'findings': []}

    def test_requests_have_three_roles_but_no_runtime_activation(self):
        manifest = self.requests()
        requests = b.read_rows(self.root/'requests/requests.jsonl')
        self.assertEqual({r['role'] for r in requests}, set(a.ROLES))
        self.assertEqual(manifest['model_calls_performed'], 0)
        self.assertFalse(manifest['native_agents_installed'])
        self.assertTrue(all('Never emit human review' in r['messages'][0]['content'] for r in requests))

    def test_clean_model_reviews_do_not_approve_anything(self):
        self.requests()
        a.collect(self.root, 'requests', [self.response(r) for r in a.ROLES], 'result')
        result = b.read_json(self.root/'result/advisory.json')
        self.assertEqual(result['missing_roles'], [])
        self.assertTrue(result['human_resolution_required'])
        for key in ('human_gold_created', 'document_approved', 'training_export', 'application_authority'):
            self.assertFalse(result[key])

    def test_human_relabelling_duplicate_roles_and_stale_binding_fail(self):
        self.requests()
        response = self.response(); response['reviewer_type'] = 'human'
        with self.assertRaisesRegex(ValueError, 'model-labelled'):
            a.collect(self.root, 'requests', [response], 'result')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            a.collect(self.root, 'requests', [self.response(), self.response()], 'result')
        response = self.response(); response['input_sha256'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'source-bound'):
            a.collect(self.root, 'requests', [response], 'result')

    def test_unknown_finding_citations_and_changed_source_fail(self):
        self.requests(); response = self.response()
        response['findings'] = [{'case_id': self.case['case_id'], 'fact_ids': ['invented'],
            'statement_ids': ['S1'], 'category': 'scope', 'severity': 'warn',
            'rationale': 'Fictional concern.', 'suggested_action': 'Human check.'}]
        with self.assertRaisesRegex(ValueError, 'unknown evidence'):
            a.collect(self.root, 'requests', [response], 'result')
        (self.root/'source.txt').write_text('changed', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            a.collect(self.root, 'requests', [self.response()], 'result')

    def test_missing_reviewer_stays_missing(self):
        self.requests()
        a.collect(self.root, 'requests', [self.response()], 'result')
        result = b.read_json(self.root/'result/advisory.json')
        self.assertEqual(result['missing_roles'], ['requirements', 'editorial'])


if __name__ == '__main__':
    unittest.main()
