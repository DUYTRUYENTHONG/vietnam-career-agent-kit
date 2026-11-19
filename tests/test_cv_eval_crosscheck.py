"""Cross-grader diagnostics on fictional recorded judgments, not human gold."""
from copy import deepcopy
import json
import subprocess
import sys
import unittest
from core import review_cycle as r
from tests import test_review_cycle as fixture


class CrosscheckTests(unittest.TestCase):
    setUp = fixture.ReviewCycleTests.setUp

    def graders(self):
        editorial = json.loads(self.before['messages'][2]['content'])['editorial']
        digest = r.judge_inputs([self.before])['inputs_sha256']
        return [{'grader_id': gid, 'model_id': 'unknown', 'model_revision': 'unknown',
            'inputs_sha256': digest, 'predictions': [{'example_id': self.before['example_id'],
                'editorial': deepcopy(editorial)}]} for gid in ('pass-A', 'pass-B')]

    def test_reference_assistant_target_is_not_in_inference_messages(self):
        inputs = r.judge_inputs([self.before])
        self.assertFalse(inputs['reference_targets_included'])
        self.assertEqual([m['role'] for m in inputs['requests'][0]['messages']], ['system', 'user'])
        self.assertEqual(inputs['model_calls_performed'], 0)
        self.assertTrue(all(d['score'] is None for d in inputs['grader_template']['predictions'][0]['editorial'].values()))
        original = self.before['messages'][0]['content']
        inputs['requests'][0]['messages'][0]['content'] = 'changed inference copy'
        self.assertEqual(self.before['messages'][0]['content'], original)

    def test_same_host_agreement_does_not_establish_independence_or_approval(self):
        report = r.crosscheck([self.before], self.graders())
        self.assertEqual(report['pairs'][0]['full_cohort_exact_score_vector_rate'], 1)
        self.assertFalse(report['distinct_model_ids_declared'])
        for key in ('independence_verified', 'human_gold_created', 'model_promoted', 'application_authority'):
            self.assertFalse(report[key])
        self.assertTrue(report['human_review_required'])
        graders = self.graders(); graders[0]['model_id'] = 'Unknown'; graders[1]['model_id'] = 'declared-model'
        self.assertFalse(r.crosscheck([self.before], graders)['distinct_model_ids_declared'])

    def test_missing_grader_outputs_remain_in_full_cohort(self):
        graders = self.graders(); graders[0]['predictions'] = []
        report = r.crosscheck([self.before], graders)
        self.assertEqual(report['graders']['pass-A']['full_cohort_penalized_mae']['relevance'], 3)
        self.assertEqual(report['pairs'][0]['unresolved_cases'], 1)
        self.assertEqual(report['pairs'][0]['full_cohort_exact_score_vector_rate'], 0)
        self.assertIsNone(report['pairs'][0]['valid_pair_mean_absolute_difference'])
        self.assertEqual(report['triage'][0]['invalid_or_missing_graders'], ['pass-A'])

    def test_disagreement_escalates_without_a_winner(self):
        graders = self.graders()
        graders[0]['predictions'][0]['editorial']['relevance']['score'] = 0
        graders[1]['predictions'][0]['editorial']['relevance']['score'] = 3
        report = r.crosscheck([self.before], graders)
        self.assertEqual(report['triage'][0]['score_spreads']['relevance'], 3)
        self.assertNotIn('winner', report)

    def test_bad_citations_penalized_and_wrong_inputs_or_duplicate_graders_block(self):
        graders = self.graders(); graders[0]['predictions'][0]['editorial']['clarity']['statement_ids'] = ['unknown']
        report = r.crosscheck([self.before], graders)
        self.assertEqual(report['graders']['pass-A']['invalid_or_missing_count'], 1)
        graders = self.graders(); graders[0]['inputs_sha256'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'changed inference inputs'):
            r.crosscheck([self.before], graders)
        graders = self.graders(); graders[1]['grader_id'] = graders[0]['grader_id']
        with self.assertRaisesRegex(ValueError, 'Duplicate grader'):
            r.crosscheck([self.before], graders)

    def test_distinct_declared_models_still_not_verified(self):
        graders = self.graders()
        for index, grader in enumerate(graders):
            grader['model_id'] = 'fictional-model-'+str(index)
        report = r.crosscheck([self.before], graders, 'fictional-model-0')
        self.assertTrue(report['distinct_model_ids_declared'])
        self.assertTrue(report['same_writer_model_declared'])
        self.assertFalse(report['model_identity_verified'])

    def test_cli_preserves_references_and_refuses_overwrite(self):
        predictions = self.root/'graders.json'; predictions.write_text(json.dumps(self.graders()), encoding='utf8')
        output = self.root/'crosscheck.json'
        command = [sys.executable, 'scripts/cv_eval_crosscheck.py', '--references', str(self.before_path),
                   '--graders', str(predictions), '--output', str(output)]
        before = self.before_path.read_bytes()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(json.loads(output.read_text())['kind'], 'cv_grader_crosscheck')
        self.assertEqual(self.before_path.read_bytes(), before)
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
