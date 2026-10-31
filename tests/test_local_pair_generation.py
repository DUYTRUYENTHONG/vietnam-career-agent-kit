"""Fictional orchestration boundaries; model calls are patched, never downloaded."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adapters.local_pair_generation import run
from adapters.local_finetuning import model_hashes
from core.learning import export_reviewed
from core.learning import check_export
from core.workflow import WorkflowError
from scripts.demo_wording import seed, fictional_review


class LocalPairGenerationTests(unittest.TestCase):
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
        export = export_reviewed(self.work, [1, 2], 'datasets/test').data
        manifest = self.work.private_json(self.work.inside('datasets/test/manifest.json'))
        examples = [json.loads(line) for line in self.work.inside('datasets/test/examples.jsonl').read_text(encoding='utf8').splitlines()]
        self.example = next(e for e in examples if e['example_id'] in manifest['evaluation_example_ids'])
        self.model = Path(self.tmp.name)/'model'; self.model.mkdir()
        (self.model/'config.json').write_text('{}', encoding='utf8')
        (self.model/'model.safetensors').write_bytes(b'fictional-not-model-weights')
        self.training = self.work.inside('training/fixture'); self.training.mkdir(parents=True)
        self.adapter = self.training/'adapter'; self.adapter.mkdir()
        (self.adapter/'adapter_model.safetensors').write_bytes(b'fictional-not-adapter-weights')
        (self.adapter/'adapter_config.json').write_text('{}', encoding='utf8')
        result = {'training_performed': True, 'task': 'cv-wording',
                  'dataset_fingerprint': export['manifest_fingerprint'], 'base_model_files': model_hashes(self.model)}
        (self.training/'result.json').write_text(json.dumps(result), encoding='utf8')
        self.calls = []

    def generate(self, model, messages, **options):
        self.calls.append((deepcopy(messages), options))
        return {'text': self.example['messages'][-1]['content'], 'input_tokens': 100,
                'output_tokens': 80, 'generation_ms': 3.5, 'load_time_included': False}

    def invoke(self, **kwargs):
        with patch('adapters.local_pair_generation.generate', side_effect=self.generate):
            return run(self.work, 'datasets/test', self.model, 'training/fixture', 'evaluations/pair', **kwargs)

    def test_only_heldout_system_user_messages_reach_both_variants(self):
        result = self.invoke(max_new_tokens=128)
        self.assertEqual(2, len(self.calls))
        self.assertEqual(self.example['messages'][:-1], self.calls[0][0])
        self.assertEqual(self.calls[0][0], self.calls[1][0])
        self.assertIsNone(self.calls[0][1]['adapter_directory'])
        self.assertEqual(self.adapter, self.calls[1][1]['adapter_directory'])
        self.assertEqual(128, self.calls[0][1]['max_new_tokens'])
        self.assertFalse(result['promotion_performed'])
        root = self.work.inside('evaluations/pair')
        runs = self.work.private_json(root/'runs.json')
        self.assertEqual({'base', 'adapter'}, set(runs))
        self.assertEqual(80, runs['base']['outputs'][0]['metrics']['output_tokens'])
        self.assertNotIn('review', runs['base']['outputs'][0])
        report = self.work.private_json(root/'comparison.json')
        self.assertEqual(1, report['runs']['base']['contract_valid_rate'])
        self.assertIsNone(report['runs']['adapter']['caller_reported_factuality_rate'])
        self.assertTrue((root/'completed.json').is_file())

    def test_invalid_model_json_is_recorded_raw_without_repair_or_positive_review(self):
        original = self.generate
        def invalid(*args, **kwargs):
            return {**original(*args, **kwargs), 'text': '```json\n{}\n```'}
        with patch('adapters.local_pair_generation.generate', side_effect=invalid):
            self.invoke_unpatched()
        root = self.work.inside('evaluations/pair')
        self.assertEqual('```json\n{}\n```', self.work.private_json(root/'runs.json')['base']['outputs'][0]['text'])
        self.assertEqual(0, self.work.private_json(root/'comparison.json')['runs']['base']['contract_valid_rate'])

    def invoke_unpatched(self):
        return run(self.work, 'datasets/test', self.model, 'training/fixture', 'evaluations/pair')

    def test_wrong_training_task_dataset_or_base_weights_fail_before_generation(self):
        path = self.training/'result.json'
        saved = path.read_text(encoding='utf8')
        for key, value in [('task', 'career-growth'), ('dataset_fingerprint', 'stale'), ('training_performed', False), ('base_model_files', {})]:
            result = json.loads(saved); result[key] = value
            path.write_text(json.dumps(result), encoding='utf8')
            with self.assertRaises(ValueError): self.invoke()
            self.assertFalse(self.work.inside('evaluations/pair').exists())
        self.assertEqual([], self.calls)

    def test_bounds_and_existing_output_fail_without_model_call_or_overwrite(self):
        for changes in ({'max_examples': True}, {'max_examples': 0}, {'max_examples': 51},
                        {'max_new_tokens': True}, {'max_new_tokens': 2049}):
            with self.assertRaises(ValueError): self.invoke(**changes)
        root = self.work.inside('evaluations/pair'); root.mkdir(parents=True)
        (root/'keep').write_text('fixture', encoding='utf8')
        with self.assertRaises(ValueError): self.invoke()
        self.assertEqual('fixture', (root/'keep').read_text(encoding='utf8'))
        self.assertEqual([], self.calls)

    def test_failure_retains_partial_evidence_and_cannot_resume_or_retry(self):
        def broken(*args, **kwargs):
            if self.calls: raise RuntimeError('fictional local inference failure')
            return self.generate(*args, **kwargs)
        with patch('adapters.local_pair_generation.generate', side_effect=broken):
            with self.assertRaises(RuntimeError): self.invoke_unpatched()
        root = self.work.inside('evaluations/pair')
        self.assertTrue((root/'failure.json').is_file())
        self.assertTrue((root/'partial.json').is_file())
        self.assertFalse((root/'completed.json').exists())
        self.assertFalse((root/'runs.json').exists())
        with self.assertRaises(ValueError): self.invoke()
        self.assertEqual(1, len(self.calls))

    def test_changed_adapter_during_generation_cannot_mark_complete(self):
        original = self.generate
        def changed(*args, **kwargs):
            value = original(*args, **kwargs)
            (self.adapter/'adapter_model.safetensors').write_bytes(b'changed-fixture')
            return value
        with patch('adapters.local_pair_generation.generate', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'): self.invoke_unpatched()
        self.assertFalse(self.work.inside('evaluations/pair/completed.json').exists())

    def test_stale_review_is_rejected_before_generation(self):
        self.work.reject_wording(1, 'Fictional review revoked')
        with self.assertRaises((ValueError, WorkflowError)): self.invoke()
        self.assertEqual([], self.calls)
        self.assertFalse(self.work.inside('evaluations/pair').exists())

    def test_review_revocation_between_calls_preserves_only_incomplete_evidence(self):
        original = self.generate
        def revoked(*args, **kwargs):
            value = original(*args, **kwargs)
            self.work.reject_wording(1, 'Fictional mid-run revocation')
            return value
        with patch('adapters.local_pair_generation.generate', side_effect=revoked):
            with self.assertRaises((ValueError, WorkflowError)): self.invoke_unpatched()
        self.assertEqual(1, len(self.calls))
        self.assertTrue(self.work.inside('evaluations/pair/failure.json').is_file())
        self.assertFalse(self.work.inside('evaluations/pair/completed.json').exists())

    def test_private_path_escape_never_reaches_generation(self):
        with patch('adapters.local_pair_generation.generate') as generate:
            for training, output in [('../outside', 'evaluations/new'), ('training/fixture', '../outside')]:
                with self.assertRaises(WorkflowError):
                    run(self.work, 'datasets/test', self.model, training, output)
            generate.assert_not_called()

    def test_example_cap_rejects_whole_run_instead_of_silently_sampling(self):
        checked = check_export(self.work, 'datasets/test')
        # An isolated input-shape fixture for the orchestration cap. Normal exports
        # remain fully reconstructed by check_export in every other test.
        manifest_path = self.work.inside('datasets/test/manifest.json')
        manifest = self.work.private_json(manifest_path)
        extra = deepcopy(self.example); extra['example_id'] = 'fictional-extra-id'
        manifest['evaluation_example_ids'].append(extra['example_id'])
        manifest_path.write_text(json.dumps(manifest), encoding='utf8')
        with self.work.inside('datasets/test/examples.jsonl').open('a', encoding='utf8') as stream:
            stream.write(json.dumps(extra)+'\n')
        with patch('adapters.local_pair_generation.check_export', return_value=checked):
            with self.assertRaisesRegex(ValueError, 'no silent subset'): self.invoke(max_examples=1)
        self.assertEqual([], self.calls)
        self.assertFalse(self.work.inside('evaluations/pair').exists())

    def test_oversized_raw_output_never_creates_completed_or_partial_success(self):
        with patch('adapters.local_pair_generation.generate', return_value={'text': 'x'*200001}):
            with self.assertRaisesRegex(ValueError, 'bounded evaluation'): self.invoke_unpatched()
        self.assertTrue(self.work.inside('evaluations/pair/failure.json').exists())
        self.assertFalse(self.work.inside('evaluations/pair/partial.json').exists())
        self.assertFalse(self.work.inside('evaluations/pair/completed.json').exists())
