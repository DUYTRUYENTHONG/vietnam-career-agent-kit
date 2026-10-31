"""Fictional blind review preparation, with no generation or positive review labels."""
from copy import deepcopy
import hashlib
import json
import unittest

from core.wording_review import prepare_review
from core.workflow import WorkflowError
from scripts.prepare_wording_review import main
import test_wording_evaluation as fixture


class WordingReviewTests(unittest.TestCase):
    setUp = fixture.WordingEvaluationTests.setUp

    def test_packet_preserves_raw_evidence_but_hides_identity_reference_and_scores(self):
        self.runs['adapter']['outputs'][0]['text'] = '```json\n{"wrong":"RAW UNREPAIRED"}\n```'
        before = self.work.wording_packet(1).data['fingerprint']
        packet, key = prepare_review(self.work, 'datasets/test', self.runs)
        self.assertEqual(2, len(packet['cases']))
        self.assertEqual(2, len(key['case_mapping']))
        self.assertNotIn('fictional-base-revision', json.dumps(packet))
        self.assertNotIn('reference_exact_match', json.dumps(packet))
        self.assertNotIn('model_identity', json.dumps(packet))
        for case in packet['cases']:
            identity = key['case_mapping'][case['case_id']]
            original = self.runs[identity['variant']]['outputs'][0]
            self.assertEqual(original['text'], case['raw_text'])
            self.assertEqual(hashlib.sha256(case['raw_text'].encode()).hexdigest(), case['raw_output_sha256'])
            self.assertTrue(all(value is None for value in case['review'].values()))
            self.assertTrue(case['source_facts'])
            self.assertTrue(case['source_hashes'])
            self.assertTrue(case['job']['raw_jd'])
            self.assertEqual(json.loads(self.example['messages'][1]['content'])['facts'], case['source_facts'])
        self.assertFalse(packet['promotion_performed'])
        self.assertFalse(packet['semantic_truth_verified'])
        self.assertEqual(before, self.work.wording_packet(1).data['fingerprint'])

    def test_case_ids_are_new_and_existing_labels_metrics_never_leak(self):
        output = self.runs['base']['outputs'][0]
        output['metrics'] = {'input_tokens': 123, 'output_tokens': 45,
                             'generation_ms': 678, 'load_time_included': False}
        first, _ = prepare_review(self.work, 'datasets/test', self.runs)
        second, _ = prepare_review(self.work, 'datasets/test', self.runs)
        self.assertTrue({c['case_id'] for c in first['cases']}.isdisjoint(c['case_id'] for c in second['cases']))
        self.assertNotIn('metrics', json.dumps(first))

    def test_stale_or_partial_runs_never_produce_a_packet(self):
        partial = deepcopy(self.runs); partial['base']['outputs'] = []
        with self.assertRaises(ValueError): prepare_review(self.work, 'datasets/test', partial)
        self.work.reject_wording(1, 'Fictional review revoked')
        with self.assertRaises(WorkflowError): prepare_review(self.work, 'datasets/test', self.runs)

    def test_cli_separates_operator_key_and_refuses_overwrite_escape(self):
        self.work.inside('runs.json').write_text(json.dumps(self.runs), encoding='utf8')
        args = ['--data-dir', str(self.work.data_dir), '--dataset', 'datasets/test',
                '--runs', 'runs.json', '--output', 'evaluations/blind-001']
        main(args)
        root = self.work.inside('evaluations/blind-001')
        marker = json.loads((root/'completed.json').read_text())
        for name, digest in marker['files'].items():
            self.assertEqual(digest, hashlib.sha256((root/name).read_bytes()).hexdigest())
        self.assertFalse(marker['scores_created'])
        with self.assertRaises(ValueError): main(args)
        with self.assertRaises(ValueError): main(args[:-1]+['../escape'])
        with self.assertRaises(ValueError): main(args[:-1]+['evaluations'])


if __name__ == '__main__':
    unittest.main()
