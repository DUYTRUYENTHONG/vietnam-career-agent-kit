"""Read-only training preflight; fictional evidence and no optional SDK calls."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from adapters import local_finetuning as runner
from scripts.demo_wording import seed


class TrainingPreflightTests(unittest.TestCase):
    def fixture(self, root):
        work, _ = seed(root/'private')
        model = root/'model'
        model.mkdir()
        (model/'config.json').write_text('{}', encoding='utf8')
        source = work.inside('datasets/reviewed')
        source.mkdir(parents=True)
        messages = [{'role': role, 'content': 'fictional'}
                    for role in ('system', 'user', 'assistant')]
        for name in ('train.jsonl', 'evaluation.jsonl'):
            (source/name).write_text(json.dumps({'messages': messages})+'\n', encoding='utf8')
        tokenizer = Mock()
        tokenizer.apply_chat_template.side_effect = lambda messages, **kw: (
            [1, 2] if len(messages) == 2 else [1, 2, 3, 4])
        auto_tokenizer = Mock()
        auto_tokenizer.from_pretrained.return_value = tokenizer
        cuda = Mock()
        cuda.is_available.return_value = True
        cuda.get_device_name.return_value = 'Fictional CUDA device'
        sdk = {'torch': SimpleNamespace(cuda=cuda),
               'transformers': SimpleNamespace(AutoTokenizer=auto_tokenizer)}
        return work, model, sdk, auto_tokenizer

    def test_checks_both_splits_without_weights_or_workspace_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            work, model, sdk, loader = self.fixture(Path(tmp))
            before = {str(p): p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()}
            with patch.dict('sys.modules', sdk), patch.dict('os.environ', {}), \
                    patch.object(runner, 'validate_dataset') as checked:
                checked.return_value.data = {'ready_for_split': True, 'manifest_fingerprint': 'reviewed'}
                result = runner.preflight(work, 'datasets/reviewed', model, 'training/new',
                                          target_modules=['q_proj'], device='cuda')
            self.assertEqual('reviewed', result['dataset_fingerprint'])
            self.assertEqual('Fictional CUDA device', result['device_name'])
            self.assertEqual(4, result['token_lengths']['evaluation']['total'])
            self.assertEqual({'train': 2, 'evaluation': 2}, result['assistant_tokens'])
            for key in ('training_performed', 'model_weights_loaded', 'memory_fit_verified', 'promoted'):
                self.assertIs(result[key], False)
            loader.from_pretrained.assert_called_once_with(str(model), local_files_only=True,
                                                           trust_remote_code=False)
            self.assertEqual(before, {str(p): p.read_bytes() for p in Path(tmp).rglob('*') if p.is_file()})
            self.assertFalse(work.inside('training').exists())

    def test_unavailable_cuda_fails_without_cpu_fallback_or_tokenizer_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            work, model, sdk, loader = self.fixture(Path(tmp))
            sdk['torch'].cuda.is_available.return_value = False
            with patch.dict('sys.modules', sdk), patch.dict('os.environ', {}), \
                    patch.object(runner, 'validate_dataset') as checked:
                checked.return_value.data = {'ready_for_split': True, 'manifest_fingerprint': 'reviewed'}
                with self.assertRaisesRegex(ValueError, 'CUDA selected but unavailable'):
                    runner.preflight(work, 'datasets/reviewed', model, 'training/new',
                                     target_modules=['q_proj'], device='cuda')
            loader.from_pretrained.assert_not_called()
            self.assertFalse(work.inside('training').exists())

    def test_explicit_cpu_does_not_probe_or_require_cuda(self):
        with tempfile.TemporaryDirectory() as tmp:
            work, model, sdk, _ = self.fixture(Path(tmp))
            with patch.dict('sys.modules', sdk), patch.dict('os.environ', {}), \
                    patch.object(runner, 'validate_dataset') as checked:
                checked.return_value.data = {'ready_for_split': True, 'manifest_fingerprint': 'reviewed'}
                result = runner.preflight(work, 'datasets/reviewed', model, 'training/new',
                                          target_modules=['q_proj'], device='cpu')
            self.assertEqual('cpu', result['device_name'])
            sdk['torch'].cuda.is_available.assert_not_called()
            sdk['torch'].cuda.get_device_name.assert_not_called()

    def test_oversize_or_changed_evidence_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            work, model, sdk, loader = self.fixture(Path(tmp))
            loader.from_pretrained.return_value.apply_chat_template.side_effect = (
                lambda messages, **kw: [1, 2] if len(messages) == 2 else [1, 2]+[3]*127)
            good = SimpleNamespace(data={'ready_for_split': True, 'manifest_fingerprint': 'a'})
            changed = SimpleNamespace(data={'ready_for_split': True, 'manifest_fingerprint': 'b'})
            with patch.dict('sys.modules', sdk), patch.dict('os.environ', {}), \
                    patch.object(runner, 'validate_dataset', return_value=good) as checked:
                with self.assertRaisesRegex(ValueError, 'no truncation'):
                    runner.preflight(work, 'datasets/reviewed', model, 'training/new',
                                     target_modules=['q_proj'], max_length=128)
                loader.from_pretrained.return_value.apply_chat_template.side_effect = (
                    lambda messages, **kw: [1, 2] if len(messages) == 2 else [1, 2, 3])
                checked.side_effect = [good, good, changed]
                with self.assertRaisesRegex(ValueError, 'changed'):
                    runner.preflight(work, 'datasets/reviewed', model, 'training/new',
                                     target_modules=['q_proj'])
            self.assertFalse(work.inside('training').exists())

    def test_cli_preflight_does_not_dispatch_training(self):
        args = ['local_finetuning', '--data-dir', 'fictional-private', '--directory', 'datasets/v1',
                '--model-directory', 'fictional-model', '--output', 'training/new',
                '--target-module', 'q_proj', '--preflight']
        output = StringIO()
        with patch('sys.argv', args), patch.object(runner, 'Documents'), \
                patch.object(runner, 'preflight', return_value={'training_performed': False}) as check, \
                patch.object(runner, 'train') as train, redirect_stdout(output):
            runner.main()
        self.assertEqual({'training_performed': False}, json.loads(output.getvalue()))
        check.assert_called_once()
        train.assert_not_called()
