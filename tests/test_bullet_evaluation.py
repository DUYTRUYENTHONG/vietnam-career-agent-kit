"""Fictional bullet comparisons keep task, source, context and raw-output bindings."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from adapters.local_finetuning import model_hashes
from adapters.local_pair_generation import run
from core.learning import export_reviewed
from core.wording_evaluation import compare, raw_hash
from scripts.evaluate_wording import main
from tests import test_bullet_learning as fixtures


class BulletEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BulletLearningTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.reviewed(); self.fixture.second_job()
        self.work = self.fixture.work
        self.export = export_reviewed(self.work, [1, 2], 'datasets/pair', task='cv-bullet-wording').data
        manifest = self.work.private_json(self.work.inside('datasets/pair/manifest.json'))
        rows = [json.loads(line) for line in self.work.inside('datasets/pair/examples.jsonl').read_text(encoding='utf8').splitlines()]
        self.example = next(e for e in rows if e['example_id'] in manifest['evaluation_example_ids'])
        self.target = json.loads(self.example['messages'][-1]['content'])
        run = {'model_identity': 'fictional-base', 'dataset_fingerprint': self.export['manifest_fingerprint'],
               'outputs': [{'example_id': self.example['example_id'], 'text': self.example['messages'][-1]['content'],
                            'metrics': {'input_tokens': 50, 'output_tokens': 20, 'generation_ms': 10.0, 'load_time_included': False}}]}
        self.runs = {'base': deepcopy(run), 'adapter': deepcopy(run)}
        self.runs['adapter']['model_identity'] = 'fictional-base plus adapter'

    def report(self):
        return compare(self.work, 'datasets/pair', self.runs, task='cv-bullet-wording')

    def test_exact_reviewed_bullet_is_valid_without_import_or_semantic_approval(self):
        before = self.work.db_path.read_bytes()
        result = self.report()
        self.assertEqual('cv-bullet-wording', result['task'])
        self.assertEqual(1, result['runs']['base']['contract_valid_rate'])
        self.assertEqual(1, result['runs']['adapter']['reference_exact_match_rate'])
        self.assertIsNone(result['runs']['adapter']['caller_reported_factuality_rate'])
        self.assertEqual(2000, result['runs']['base']['observed_metrics_summary']['generation_output_tokens_per_second'])
        self.assertFalse(result['semantic_truth_verified']); self.assertFalse(result['promotion_performed'])
        self.assertEqual(before, self.work.db_path.read_bytes())

    def test_selected_statement_context_and_requirement_bindings_cannot_be_swapped(self):
        for change in [lambda x: x.update(language='vi'), lambda x: x.update(section_kind='skills'),
                       lambda x: x.update(context_fact_id=None), lambda x: x['statement'].update(id='another'),
                       lambda x: x['statement'].update(source_fact_ids=['P0']),
                       lambda x: x['statement'].update(requirement_ids=[]),
                       lambda x: x.update(extra='not allowed')]:
            candidate = deepcopy(self.target); change(candidate)
            self.runs['adapter']['outputs'][0]['text'] = json.dumps(candidate)
            report = self.report()
            self.assertEqual(0, report['runs']['adapter']['contract_valid_rate'])
            self.assertTrue(report['runs']['adapter']['examples'][0]['issues'])

    def test_existing_fact_qualifier_and_locator_checks_apply_to_bullet(self):
        for change in [lambda x: x['statement'].update(source_locators=['invented']),
                       lambda x: x['statement'].update(text='Architected AWS production systems.', transformation='faithful_paraphrase'),
                       lambda x: x['statement'].update(review_status='approved')]:
            candidate = deepcopy(self.target); change(candidate)
            self.runs['adapter']['outputs'][0]['text'] = json.dumps(candidate)
            self.assertEqual(0, self.report()['runs']['adapter']['contract_valid_rate'])

    def test_raw_invalid_output_metrics_and_exact_review_binding_are_preserved(self):
        output = self.runs['adapter']['outputs'][0]
        output['text'] = '```json\n{}\n```'
        output['review'] = {'example_id': self.example['example_id'], 'dataset_fingerprint': self.export['manifest_fingerprint'],
            'raw_output_sha256': raw_hash(output['text']), 'reviewer': 'fictional separate reviewer',
            'factuality': False, 'qualifiers_preserved': False, 'specificity': 1, 'rationale': 'Invalid JSON.'}
        report = self.report()
        self.assertEqual(0, report['runs']['adapter']['contract_valid_rate'])
        self.assertEqual(20, report['runs']['adapter']['observed_metrics_summary']['output_tokens_total'])
        output['review']['raw_output_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'Review does not bind'): self.report()

    def test_task_mismatch_is_not_inferred_from_manifest(self):
        with self.assertRaisesRegex(ValueError, 'full-CV'): compare(self.work, 'datasets/pair', self.runs)
        with self.assertRaises(ValueError): compare(self.work, 'datasets/pair', self.runs, task='cv-review')

    def test_cli_explicit_task_writes_private_report_once(self):
        path = self.work.inside('evaluations/recorded.json'); path.parent.mkdir()
        path.write_text(json.dumps(self.runs), encoding='utf8')
        args = ['--data-dir', str(self.work.data_dir), '--dataset', 'datasets/pair', '--runs', 'evaluations/recorded.json',
                '--output', 'evaluations/report.json', '--task', 'cv-bullet-wording']
        with redirect_stdout(io.StringIO()): main(args)
        self.assertEqual('cv-bullet-wording', self.work.private_json(self.work.inside('evaluations/report.json'))['task'])
        with self.assertRaises(ValueError): main(args)

    def test_paired_generator_uses_explicit_matching_task_without_reference_leakage(self):
        model = Path(self.fixture.tmp.name)/'model'; model.mkdir()
        (model/'config.json').write_text('{}', encoding='utf8')
        (model/'model.safetensors').write_bytes(b'fictional-not-model-weights')
        training = self.work.inside('training/fixture'); adapter = training/'adapter'
        adapter.mkdir(parents=True)
        (adapter/'adapter_config.json').write_text('{}', encoding='utf8')
        (adapter/'adapter_model.safetensors').write_bytes(b'fictional-not-adapter-weights')
        result = {'training_performed': True, 'task': 'cv-bullet-wording',
                  'dataset_fingerprint': self.export['manifest_fingerprint'], 'base_model_files': model_hashes(model)}
        (training/'result.json').write_text(json.dumps(result), encoding='utf8')
        calls = []
        def generated(model, batches, **kwargs):
            calls.append((deepcopy(batches), kwargs))
            yield {'text': self.example['messages'][-1]['content'], 'input_tokens': 50, 'output_tokens': 20,
                   'generation_ms': 10.0, 'load_time_included': False, 'model_load_ms': 1.0}
        with patch('adapters.local_pair_generation.generate_many', side_effect=generated):
            completed = run(self.work, 'datasets/pair', model, 'training/fixture', 'evaluations/pair', task='cv-bullet-wording')
        self.assertEqual('cv-bullet-wording', completed['task'])
        self.assertEqual([self.example['messages'][:-1]], calls[0][0])
        self.assertEqual(calls[0][0], calls[1][0])
        self.assertIsNone(calls[0][1]['adapter_directory'])
        self.assertEqual(adapter, calls[1][1]['adapter_directory'])
        self.assertEqual(1, self.work.private_json(self.work.inside('evaluations/pair/comparison.json'))['runs']['base']['contract_valid_rate'])
        self.assertFalse(completed['promotion_performed'])

    def test_bullet_generator_default_fails_before_model_loading(self):
        with patch('adapters.local_pair_generation.generate_many') as generate:
            with self.assertRaisesRegex(ValueError, 'full-CV'):
                run(self.work, 'datasets/pair', 'missing', 'training/missing', 'evaluations/no-output')
            generate.assert_not_called()
        self.assertFalse(self.work.inside('evaluations/no-output').exists())

    def test_blinded_bullet_packet_retains_selected_scope_without_variant_metadata(self):
        from core.wording_review import prepare_review
        packet, key = prepare_review(self.work, 'datasets/pair', self.runs, task='cv-bullet-wording')
        self.assertEqual('cv-bullet-wording', packet['task'])
        self.assertEqual(2, len(packet['cases']))
        inputs = json.loads(self.example['messages'][1]['content'])
        for case in packet['cases']:
            self.assertEqual(inputs['context_fact_id'], case['selected_bullet']['context_fact_id'])
            self.assertEqual(inputs['statement_fact_id'], case['selected_bullet']['statement_fact_id'])
            self.assertNotIn('model_identity', case); self.assertNotIn('metrics', case)
            self.assertNotIn('variant', case); self.assertNotIn('reference_answer', case)
            self.assertIsNone(case['review']['factuality'])
        self.assertEqual({'base', 'adapter'}, {v['variant'] for v in key['case_mapping'].values()})
