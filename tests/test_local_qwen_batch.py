"""Fictional SDK boundary tests; no weights, optional dependencies or downloads."""
from contextlib import nullcontext
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from adapters import local_qwen


class LocalQwenBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prompts = [[{'role': 'user', 'content': text}] for text in ('fictional one', 'fictional two')]
        self.prompt = Mock(shape=(1, 3))
        self.prompt.to.return_value = self.prompt
        output = Mock(); output.numel.return_value = 2
        result = Mock(); result.__getitem__ = Mock(return_value=output)
        self.model = Mock(); self.model.generate.return_value = result
        self.tokenizer = Mock(eos_token_id=1)
        self.tokenizer.apply_chat_template.return_value = self.prompt
        self.tokenizer.decode.return_value = 'fictional output'
        self.model_loader = Mock(return_value=self.model)
        self.tokenizer_loader = Mock(return_value=self.tokenizer)
        self.modules = {
            'torch': SimpleNamespace(no_grad=nullcontext, ones_like=lambda value: value),
            'transformers': SimpleNamespace(
                AutoModelForCausalLM=SimpleNamespace(from_pretrained=self.model_loader),
                AutoTokenizer=SimpleNamespace(from_pretrained=self.tokenizer_loader)),
        }

    def test_two_prompts_share_one_load_and_fresh_generation_inputs(self):
        with patch.dict('sys.modules', self.modules):
            rows = list(local_qwen.generate_many(self.root, self.prompts, max_new_tokens=4))
        self.assertEqual(1, self.model_loader.call_count)
        self.assertEqual(1, self.tokenizer_loader.call_count)
        self.assertEqual(2, self.model.generate.call_count)
        self.assertEqual(2, len(rows))
        self.assertGreaterEqual(rows[0]['model_load_ms'], 0)
        self.assertIsNone(rows[1]['model_load_ms'])
        for row in rows:
            self.assertEqual((3, 2), (row['input_tokens'], row['output_tokens']))
            self.assertFalse(row['sent'])
            self.assertFalse(row['semantic_truth_verified'])
            self.assertFalse(row['load_time_included'])
        for call in self.model.generate.call_args_list:
            self.assertNotIn('past_key_values', call.kwargs)
            self.assertFalse(call.kwargs['do_sample'])

    def test_all_prompts_are_validated_before_loading(self):
        for batch in ([], self.prompts * 26, self.prompts + [[{'role': 'tool', 'content': 'x'}]]):
            with patch.dict('sys.modules', self.modules):
                with self.assertRaises(ValueError):
                    list(local_qwen.generate_many(self.root, batch, max_new_tokens=4))
        self.model_loader.assert_not_called()

    def test_adapter_identity_still_precedes_sdk_loading(self):
        with patch.dict('sys.modules', self.modules):
            with self.assertRaises((ValueError, FileNotFoundError)):
                list(local_qwen.generate_many(self.root, self.prompts,
                     adapter_directory=self.root/'missing', max_new_tokens=4))
        self.model_loader.assert_not_called()

    def test_token_overflow_never_calls_generation(self):
        self.prompt.shape = (1, 8190)
        with patch.dict('sys.modules', self.modules):
            with self.assertRaisesRegex(ValueError, 'no truncation'):
                list(local_qwen.generate_many(self.root, self.prompts, max_new_tokens=4))
        self.model.generate.assert_not_called()

    def test_failure_does_not_retry_and_one_shot_api_is_preserved(self):
        self.model.generate.side_effect = [self.model.generate.return_value, RuntimeError('fictional failure')]
        with patch.dict('sys.modules', self.modules):
            stream = local_qwen.generate_many(self.root, self.prompts, max_new_tokens=4)
            self.assertEqual('fictional output', next(stream)['text'])
            with self.assertRaisesRegex(RuntimeError, 'fictional failure'): next(stream)
        self.assertEqual(2, self.model.generate.call_count)
        self.model.generate.side_effect = None
        with patch.dict('sys.modules', self.modules):
            row = local_qwen.generate(self.root, self.prompts[0], max_new_tokens=4)
        self.assertEqual('fictional output', row['text'])
