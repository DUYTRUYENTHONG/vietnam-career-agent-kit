"""Fictional planning and retrieval regressions, without models or real labels."""
from copy import deepcopy
import unittest
from core import cv_planning as c, tailor_benchmark as b
from tests import test_tailor_benchmark as fixture


class PlanningTests(unittest.TestCase):
    setUp = fixture.TailorBenchmarkTests.setUp
    annotation = fixture.TailorBenchmarkTests.annotation
    frozen = fixture.TailorBenchmarkTests.frozen
    records = fixture.TailorBenchmarkTests.records

    def reviewed(self, folder='prepared'):
        rows = b.read_rows(self.root/folder/'matching_review.jsonl')
        for row in rows:
            row.update(mandatory=True, hard=False, priority=3, status='partial',
                fact_ids=['F1'], reviewer_id='fictional-human', reviewer_type='human',
                source_checked=True, rationale='Fictional test attestation only.')
        return rows

    def test_retrieval_is_deterministic_not_a_match_label(self):
        query = deepcopy(self.case); query['requirement']['text'] = 'Python API tests'
        result = c.retrieve(query, 1)
        self.assertEqual(result, c.retrieve(query, 1))
        self.assertEqual(result[0]['fact_id'], 'F1')
        self.assertNotIn('status', result[0])
        changed = deepcopy(self.case); changed['requirement']['text'] = 'Kubernetes'
        self.assertEqual(c.retrieve(changed), [])
        self.assertEqual(c.tokens('DỮ LIỆU'), c.tokens('dữ liệu'))
        with self.assertRaises(ValueError):
            c.retrieve(self.case, 0)

    def test_v2_drops_function_words_without_changing_evidence_or_negation(self):
        case = deepcopy(self.case)
        case['requirement']['text'] = 'Basic understanding of Machine Learning'
        unrelated = deepcopy(case['facts'][0]); unrelated['id'] = 'F0'; unrelated['text'] = 'Configuration of email services'
        case['facts'][0]['text'] = 'Built ML pipelines'
        case['facts'].append(unrelated)
        original = deepcopy(case)
        self.assertEqual(c.retrieve(case, 5, 'bm25-v2'), [{'fact_id': 'F1', 'retrieval_score': c.retrieve(case)[0]['retrieval_score']}])
        self.assertEqual(case, original)
        self.assertIn('not', c.tokens('Not proficient in ML'))
        with self.assertRaises(ValueError):
            c.retrieve(case, 5, 'unfrozen-method')

    def test_blank_review_cannot_build_plan(self):
        c.prepare(self.root, [self.case], 'prepared')
        rows = b.read_rows(self.root/'prepared/matching_review.jsonl')
        with self.assertRaisesRegex(ValueError, 'human'):
            c.plan(self.root, 'prepared', rows, 'plan')
        self.assertFalse((self.root/'plan').exists())

    def test_partial_evidence_and_mandatory_gaps_stay_visible(self):
        other = deepcopy(self.case); other['case_id'] = 'second'; other['requirement']['id'] = 'R2'
        c.prepare(self.root, [self.case, other], 'prepared')
        rows = self.reviewed(); rows[1].update(status='unknown', fact_ids=[])
        c.plan(self.root, 'prepared', rows, 'plan', 1)
        plan = b.read_json(self.root/'plan/plan.json')
        self.assertEqual(plan['ordered_evidence'][0], self.case['facts'][0])
        self.assertEqual(plan['mandatory_attention'], ['fictional1', 'second'])
        self.assertEqual(len(plan['requirement_matrix']), 2)
        self.assertFalse(plan['application_authority'])
        with self.assertRaises(ValueError):
            c.plan(self.root, 'prepared', rows, 'plan', 1)

    def test_unknown_ids_changed_sources_and_omitted_requirements_block(self):
        c.prepare(self.root, [self.case], 'prepared')
        rows = self.reviewed(); rows[0]['fact_ids'] = ['invented']
        with self.assertRaisesRegex(ValueError, 'Unknown matching fact'):
            c.plan(self.root, 'prepared', rows, 'plan')
        with self.assertRaisesRegex(ValueError, 'every requirement'):
            c.plan(self.root, 'prepared', [], 'plan')
        (self.root/'source.txt').write_text('changed', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            c.plan(self.root, 'prepared', self.reviewed(), 'plan')

    def test_other_employers_cannot_be_combined_into_one_plan(self):
        other = deepcopy(self.case); other['case_id'] = 'other'; other['source_group'] = 'other-employer'
        with self.assertRaisesRegex(ValueError, 'one vacancy'):
            c.prepare(self.root, [self.case, other], 'prepared')

    def test_budget_prioritizes_mandatory_and_records_omitted_preference(self):
        second = deepcopy(self.case); second['case_id'] = 'preferred'; second['requirement']['id'] = 'R2'
        extra = deepcopy(self.case['facts'][0]); extra['id'] = 'F2'
        self.case['facts'].append(extra); second['facts'].append(extra)
        c.prepare(self.root, [self.case, second], 'prepared')
        rows = self.reviewed(); rows[0].update(status='demonstrated', priority=1)
        rows[1].update(status='demonstrated', mandatory=False, priority=3, fact_ids=['F2'])
        c.plan(self.root, 'prepared', rows, 'plan', 1)
        result = b.read_json(self.root/'plan/plan.json')
        self.assertEqual([f['id'] for f in result['ordered_evidence']], ['F1'])
        self.assertTrue(result['requirement_matrix'][1]['omitted_by_budget'])
        self.assertEqual(result['mandatory_attention'], [])

    def test_inconsistent_fact_scope_and_unsupported_match_flags_block(self):
        second = deepcopy(self.case); second['case_id'] = 'other'; second['requirement']['id'] = 'R2'
        second['facts'][0]['scope'] = 'Different contribution scope'
        c.prepare(self.root, [self.case, second], 'prepared')
        rows = self.reviewed()
        with self.assertRaisesRegex(ValueError, 'consistent scope'):
            c.plan(self.root, 'prepared', rows, 'plan')
        rows[0].update(status='missing')
        with self.assertRaisesRegex(ValueError, 'evidence disagree'):
            c.plan(self.root, 'prepared', rows, 'plan')

    def test_gold_not_used_to_rank_and_same_prompt_controls(self):
        fm = self.frozen()
        vm = c.retrieval_variant(self.root, 'frozen', 'retrieved', 1)
        self.assertEqual(fm['cohort_sha256'], vm['cohort_sha256'])
        self.assertEqual(fm['files']['gold.jsonl'], vm['files']['gold.jsonl'])
        inputs = b.read_rows(self.root/'retrieved/generation_inputs.jsonl')[0]['conditions']
        self.assertEqual(inputs['base_original'][0], inputs['base_evidence'][0])
        self.assertNotIn('acceptable_fact_ids', str(inputs))
        # Keep the original lexical miss as a baseline and measure the v2 fix.
        self.assertEqual(c.retrieval_report(self.root, 'frozen', 1, 'bm25-v1')['hit_rate_at_k'], 0)
        self.assertEqual(c.retrieval_report(self.root, 'frozen', 1, 'bm25-v2')['hit_rate_at_k'], 1)
        with self.assertRaisesRegex(ValueError, 'matched retrieval'):
            b.blind(self.root, 'retrieved', [], 'wrong-comparison', comparison='prompt')
        training = b.blind(self.root, 'retrieved', [], 'training-review', comparison='training')
        self.assertEqual(training['comparison'], 'training')

    def test_missing_retrieval_context_is_not_allowed_to_cite_hidden_fact(self):
        self.case['requirement']['text'] = 'Kubernetes'
        raw = 'Built Python API tests with AI assistance.\nKubernetes'
        (self.root/'source.txt').write_bytes(raw.encode())
        for source in [self.case['requirement']['source'], self.case['facts'][0]['source']]:
            source['sha256'] = b.digest(raw.encode())
        self.frozen(); c.retrieval_variant(self.root, 'frozen', 'retrieved')
        inputs = b.read_rows(self.root/'retrieved/generation_inputs.jsonl')[0]
        records = self.records()[:2]
        for row in records:
            row['messages_sha256'] = b.binding(inputs['conditions'][row['condition']])
        b.blind(self.root, 'retrieved', records, 'blind', comparison='retrieval')
        errors = [r['structural_error'] for r in b.read_rows(self.root/'blind/review_packet.jsonl')]
        self.assertTrue(any(e and 'not supplied' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
