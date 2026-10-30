"""Offline preparation regressions; no model SDKs or downloads in standard CI."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adapters.local_finetuning import encode, finite_loss, histogram, model_hashes, prepare, train
from core.workflow import WorkflowError
from core.learning import export_reviewed
from scripts.demo_wording import seed, fictional_review
from scripts.setup_qwen3 import download, ROOT
from adapters.local_qwen import generate


class LocalFineTuningTests(unittest.TestCase):
    def test_model_identity_changes_when_weight_bytes_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            weights = root/'model.safetensors'
            weights.write_bytes(b'fictional-bytes-not-a-model')
            before = model_hashes(root)
            weights.write_bytes(b'changed-fictional-bytes')
            self.assertNotEqual(before, model_hashes(root))

    def test_model_download_cannot_target_source_or_existing_files(self):
        with self.assertRaises(ValueError): download(ROOT/'model')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): download(tmp)

    def test_local_inference_rejects_unbounded_or_nonchat_input_before_import(self):
        for messages, limit in [([], 1), ([{'role': 'tool', 'content': 'x'}], 1),
                                ([{'role': 'user', 'content': 'x'*30001}], 1),
                                ([{'role': 'user', 'content': 'x'}], True)]:
            with self.assertRaises(ValueError): generate('', messages, max_new_tokens=limit)

    def test_prompt_is_masked_and_output_preserved_without_truncation(self):
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return [1, 2] if len(messages) == 2 else [1, 2, 3, 4]
        row = encode(Tokenizer(), [{}, {}, {}], 4)
        self.assertEqual([-100, -100, 3, 4], row['labels'])
        self.assertEqual({'count': 1, 'min': 4, 'max': 4, 'median': 4, 'total': 4}, histogram([row]))
        with self.assertRaises(ValueError):
            encode(Tokenizer(), [{}, {}, {}], 3)

    def test_incompatible_template_and_nonfinite_loss_fail(self):
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return [9] if len(messages) == 2 else [1, 2]
        with self.assertRaises(ValueError): encode(Tokenizer(), [{}, {}, {}], 100)
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError): finite_loss(value)

    def test_single_group_export_and_stale_review_cannot_train(self):
        with tempfile.TemporaryDirectory() as tmp:
            work, model = seed(Path(tmp)/'private')
            work.import_wording(1, model)
            work.review_wording(1, fictional_review(work.wording_packet(1).data))
            export_reviewed(work, [1], 'datasets/one')
            with self.assertRaisesRegex(ValueError, 'held-out split'):
                prepare(work, 'datasets/one', tmp, 'training/one')
            work.reject_wording(1, 'Fictional changed source assessment')
            with self.assertRaises(WorkflowError):
                prepare(work, 'datasets/one', tmp, 'training/one')
            self.assertFalse(work.inside('training').exists())

    def test_paths_and_changed_dataset_cannot_reserve_run(self):
        # File-boundary behavior around the existing independently tested exporter.
        with tempfile.TemporaryDirectory() as tmp:
            work, _ = seed(Path(tmp)/'private')
            model = Path(tmp)/'model'; model.mkdir()
            (model/'config.json').write_text('{}', encoding='utf8')
            source = work.inside('datasets/two'); source.mkdir(parents=True)
            for name in ('train.jsonl', 'evaluation.jsonl'):
                (source/name).write_text(json.dumps({'messages': [{'role': 'assistant', 'content': 'fictional'}]})+'\n', encoding='utf8')
            checked = {'ready_for_split': True, 'manifest_fingerprint': 'a'}
            with patch('adapters.local_finetuning.check_export') as check:
                check.return_value.data = checked
                with self.assertRaises(ValueError): prepare(work, 'datasets/two', model, 'datasets/overwrite')
                with self.assertRaises(ValueError): prepare(work, 'datasets/two', model, 'training')
                target = work.inside('training/existing'); target.mkdir(parents=True)
                with self.assertRaises(ValueError): prepare(work, 'datasets/two', model, 'training/existing')
                _, target, rows, fingerprint = prepare(work, 'datasets/two', model, 'training/new')
                self.assertEqual('a', fingerprint)
                self.assertEqual(1, len(rows['train']))
                self.assertFalse(target.exists())
                check.side_effect = [type('Result', (), {'data': checked})(),
                                     type('Result', (), {'data': {**checked, 'manifest_fingerprint': 'b'}})()]
                with self.assertRaisesRegex(ValueError, 'changed'):
                    prepare(work, 'datasets/two', model, 'training/new')
                self.assertFalse(target.exists())

    def test_invalid_configuration_fails_before_model_import(self):
        for changes in ({'epochs': True}, {'max_length': 4}, {'learning_rate': float('nan')},
                        {'device': 'automatic'}, {'target_modules': []}):
            kwargs = {'target_modules': ['q_proj'], **changes}
            with self.assertRaises(ValueError):
                train(None, '', '', '', **kwargs)
