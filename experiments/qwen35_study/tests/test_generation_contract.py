import json
import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

from experiments.qwen35_study.generation import generate_row


class Encoded(dict):
    def __init__(self, size):
        super().__init__(input_ids=SimpleNamespace(shape=(1, size)))
        self.input_ids = self['input_ids']

    def to(self, device):
        return self


class Generated:
    def __getitem__(self, index):
        return SimpleNamespace(numel=lambda: 6)


class GenerationContract(unittest.TestCase):
    def fixtures(self, raw, size=50):
        tokenizer = Mock()
        tokenizer.eos_token_id = 1
        tokenizer.apply_chat_template.return_value = 'rendered input'
        tokenizer.return_value = Encoded(size)
        tokenizer.decode.return_value = raw
        model = Mock()
        model.generate.return_value = Generated()
        torch = SimpleNamespace(cuda=SimpleNamespace(synchronize=Mock()),
                                inference_mode=nullcontext)
        facts = {'F1': {'id': 'F1', 'text': 'Used SQL with AI assistance.'}}
        req = {'id': 'R1', 'text': 'Independently developed SQL pipelines.'}
        gold = {'label': 'partial', 'fact_ids': ['F1']}
        return tokenizer, model, torch, facts, req, gold

    def test_one_attempt_fixed_budget_and_no_reference_in_prompt(self):
        tokenizer, model, torch, facts, req, gold = self.fixtures(
            '{"label":"partial","fact_ids":["F1"]}')
        row = generate_row(model, tokenizer, torch, 'case', req, facts, gold)
        visible = tokenizer.apply_chat_template.call_args.args[0]
        self.assertEqual([m['role'] for m in visible], ['system', 'user'])
        user = json.loads(visible[1]['content'])
        self.assertEqual(set(user), {'requirement', 'facts'})
        self.assertNotIn('label', user)
        kwargs = model.generate.call_args.kwargs
        self.assertEqual(kwargs['max_new_tokens'], 128)
        self.assertFalse(kwargs['do_sample'])
        self.assertEqual(model.generate.call_count, 1)
        self.assertEqual(row['input_tokens'], 50)
        self.assertEqual(row['output_tokens'], 6)
        self.assertEqual(row['prediction'], gold)
        self.assertFalse(row['includes_loading_or_tokenization'])

    def test_invalid_json_or_unknown_citation_is_kept_without_retry(self):
        for raw in ('not json', '{"label":"direct","fact_ids":["invented"]}'):
            tokenizer, model, torch, facts, req, gold = self.fixtures(raw)
            row = generate_row(model, tokenizer, torch, 'case', req, facts, gold)
            self.assertIsNone(row['prediction'])
            self.assertTrue(row['error'])
            self.assertEqual(row['raw'], raw)
            self.assertEqual(model.generate.call_count, 1)

    def test_over_budget_never_calls_generate(self):
        tokenizer, model, torch, facts, req, gold = self.fixtures('', size=2049)
        with self.assertRaisesRegex(ValueError, 'no truncation'):
            generate_row(model, tokenizer, torch, 'case', req, facts, gold)
        model.generate.assert_not_called()
