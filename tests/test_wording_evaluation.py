"""Fictional paired evaluation; no model calls or automatic semantic scores."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from core.learning import export_reviewed
from core.wording_evaluation import compare, raw_hash
from core.workflow import WorkflowError
from scripts.demo_wording import seed, fictional_review
from scripts.evaluate_wording import main


class WordingEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work, model = seed(Path(self.tmp.name)/'private')
        self.work.import_wording(1, model)
        self.work.review_wording(1, fictional_review(self.work.wording_packet(1).data))
        packet = self.work.wording_packet(1).data
        job, _ = self.work.job_document(1)
        other = deepcopy(job)
        other.update(platform_job_id=job['platform_job_id']+'-two', req_id=job['req_id']+'-two', url=job['url']+'/two')
        self.work.import_job(other)
        self.work.assess(2, {'schema_version': '1.0', 'rows': packet['assessment']['rows']})
        model = deepcopy(model); model['job_id'] = 2
        for section in model['sections']:
            for group in section['groups']:
                for statement in group['statements']:
                    if 'F1' in statement['source_fact_ids']:
                        statement.update(text='Used SQL to query a fictional sales dataset.', transformation='faithful_paraphrase')
        self.work.import_wording(2, model)
        self.work.review_wording(2, fictional_review(self.work.wording_packet(2).data))
        result = export_reviewed(self.work, [1, 2], 'datasets/test').data
        manifest = self.work.private_json(self.work.inside('datasets/test/manifest.json'))
        examples = [json.loads(line) for line in self.work.inside('datasets/test/examples.jsonl').read_text(encoding='utf8').splitlines()]
        self.example = next(e for e in examples if e['example_id'] in manifest['evaluation_example_ids'])
        self.run = {'model_identity': 'fictional-base-revision', 'dataset_fingerprint': result['manifest_fingerprint'],
            'outputs': [{'example_id': self.example['example_id'], 'text': self.example['messages'][2]['content']}]}
        self.runs = {'base': deepcopy(self.run), 'adapter': deepcopy(self.run)}
        self.runs['adapter']['model_identity'] = 'fictional-base-revision plus fictional-adapter-hash'

    def test_exact_outputs_do_not_become_semantic_approval_or_metrics(self):
        report = compare(self.work, 'datasets/test', self.runs)
        self.assertEqual(1, report['runs']['base']['contract_valid_rate'])
        self.assertEqual(1, report['runs']['base']['reference_exact_match_rate'])
        self.assertIsNone(report['runs']['base']['caller_reported_factuality_rate'])
        self.assertIsNone(report['runs']['base']['examples'][0]['metrics'])
        self.assertFalse(report['semantic_truth_verified'])
        self.assertFalse(report['promotion_performed'])

    def test_fenced_duplicate_key_and_nonfinite_json_fail_without_repair(self):
        for raw in ['```json\n{}\n```', '{"language":"en","language":"vi","sections":[]}', '{"language":NaN,"sections":[]}']:
            self.runs['adapter']['outputs'][0]['text'] = raw
            report = compare(self.work, 'datasets/test', self.runs)
            self.assertEqual(0, report['runs']['adapter']['contract_valid_rate'])
            self.assertEqual(1, report['runs']['base']['contract_valid_rate'])

    def test_unsupported_skill_and_review_hash_changes_are_rejected(self):
        output = self.runs['adapter']['outputs'][0]
        content = json.loads(output['text'])
        content['sections'][0]['groups'][0]['statements'][0]['text'] += ' Expert AWS production.'
        output['text'] = json.dumps(content)
        self.assertEqual(0, compare(self.work, 'datasets/test', self.runs)['runs']['adapter']['contract_valid_rate'])
        output['review'] = {'example_id': self.example['example_id'], 'dataset_fingerprint': self.run['dataset_fingerprint'],
            'raw_output_sha256': 'wrong', 'reviewer': 'fictional test reviewer',
            'factuality': False, 'qualifiers_preserved': True, 'specificity': 2, 'rationale': 'Fictional fixture: unsupported expertise.'}
        with self.assertRaises(ValueError): compare(self.work, 'datasets/test', self.runs)
        output['review']['raw_output_sha256'] = raw_hash(output['text'])
        report = compare(self.work, 'datasets/test', self.runs)
        self.assertEqual(0, report['runs']['adapter']['caller_reported_factuality_rate'])

    def test_review_cannot_move_to_another_dataset_or_job_with_same_output(self):
        output = self.runs['adapter']['outputs'][0]
        review = {'example_id': output['example_id'], 'dataset_fingerprint': self.run['dataset_fingerprint'],
            'raw_output_sha256': raw_hash(output['text']), 'reviewer': 'fictional test reviewer',
            'factuality': True, 'qualifiers_preserved': True, 'specificity': 4, 'rationale': 'Fictional exact reference.'}
        output['review'] = review
        report = compare(self.work, 'datasets/test', self.runs)
        self.assertEqual(1, report['runs']['adapter']['caller_reported_factuality_rate'])
        self.assertIsNone(report['adapter_minus_base']['caller_reported_factuality_rate'])
        for key in ('example_id', 'dataset_fingerprint'):
            original = review[key]; review[key] = 'different'
            with self.assertRaises(ValueError): compare(self.work, 'datasets/test', self.runs)
            review[key] = original

    def test_missing_unknown_training_examples_and_stale_dataset_fail(self):
        for mutation in ('missing', 'unknown', 'fingerprint'):
            runs = deepcopy(self.runs)
            if mutation == 'missing': runs['base']['outputs'] = []
            elif mutation == 'unknown': runs['base']['outputs'][0]['example_id'] = 'not-held-out'
            else: runs['base']['dataset_fingerprint'] = 'stale'
            with self.assertRaises(ValueError): compare(self.work, 'datasets/test', runs)
        self.work.reject_wording(1, 'Fictional review revoked')
        with self.assertRaises(WorkflowError): compare(self.work, 'datasets/test', self.runs)

    def test_metrics_never_accept_boolean_tokens_or_nan_time(self):
        for key, value in [('input_tokens', True), ('generation_ms', float('nan')), ('output_tokens', -1)]:
            runs = deepcopy(self.runs)
            runs['base']['outputs'][0]['metrics'] = {'input_tokens': None, 'output_tokens': None, 'generation_ms': None, 'load_time_included': False}
            runs['base']['outputs'][0]['metrics'][key] = value
            with self.assertRaises(ValueError): compare(self.work, 'datasets/test', runs)

    def test_cli_writes_only_new_private_report_and_does_not_change_draft(self):
        before = self.work.wording_packet(1).data['fingerprint']
        self.work.inside('runs.json').write_text(json.dumps(self.runs), encoding='utf8')
        args = ['--data-dir', str(self.work.data_dir), '--dataset', 'datasets/test',
                '--runs', 'runs.json', '--output', 'evaluations/pair.json']
        main(args)
        self.assertFalse(self.work.private_json(self.work.inside('evaluations/pair.json'))['authority_granted'])
        self.assertEqual(before, self.work.wording_packet(1).data['fingerprint'])
        with self.assertRaises(ValueError): main(args)
        with self.assertRaises(ValueError): main(args[:-1]+['../escape.json'])
