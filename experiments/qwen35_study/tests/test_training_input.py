import json
import unittest
from experiments.qwen35_study.train_4b import encode_example


class Tokenizer:
    eos_token_id = 1

    def apply_chat_template(self, messages, **kwargs):
        return json.dumps(messages, ensure_ascii=False) + 'ASSISTANT:'

    def encode(self, text, **kwargs):
        return [ord(c) + 2 for c in text]


class InputTests(unittest.TestCase):
    def row(self):
        return {'messages': [
            {'role': 'system', 'content': 'Only use supplied facts.'},
            {'role': 'user', 'content': json.dumps({'requirement': 'Use SQL',
                'facts': [{'id': 'F1', 'text': 'Used SQL with AI assistance.'}]})},
            {'role': 'assistant', 'content': '{"label":"partial","fact_ids":["F1"]}'}]}

    def test_prompt_is_masked_and_target_is_only_json(self):
        result = encode_example(self.row(), Tokenizer(), 2048)
        labels = result['labels']
        cut = next(i for i, v in enumerate(labels) if v != -100)
        self.assertTrue(all(x == -100 for x in labels[:cut]))
        self.assertEqual(labels[cut:], result['input_ids'][cut:])
        self.assertEqual(labels[-1], 1)

    def test_no_truncation_or_unknown_citations(self):
        with self.assertRaises(ValueError):
            encode_example(self.row(), Tokenizer(), 10)
        row = self.row()
        row['messages'][-1]['content'] = '{"label":"direct","fact_ids":["X"]}'
        with self.assertRaises(ValueError):
            encode_example(row, Tokenizer(), 2048)

    def test_rationale_or_metadata_cannot_enter_user_input(self):
        row = self.row()
        user = json.loads(row['messages'][1]['content'])
        user['rationale'] = 'private reference answer'
        row['messages'][1]['content'] = json.dumps(user)
        with self.assertRaises(ValueError):
            encode_example(row, Tokenizer(), 2048)
