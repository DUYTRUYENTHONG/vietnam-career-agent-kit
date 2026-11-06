"""Fictional external-pilot coverage; identity is never inferred from wording."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.training_coverage import audit_coverage


def row(fid, text):
    return {'messages': [
        {'role': 'system', 'content': 'Fictional pilot'},
        {'role': 'user', 'content': json.dumps({'candidate_fact': {'id': fid, 'text': text}})},
        {'role': 'assistant', 'content': 'Unreviewed target'}]}


class CoverageTests(unittest.TestCase):
    def test_missing_changed_evaluation_only_and_explicit_alias(self):
        expected = [{'id': 'current-A', 'text': 'Used SQL.'},
                    {'id': 'B', 'text': 'Built a prototype.'},
                    {'id': 'C', 'text': 'Validated records.'},
                    {'id': 'D', 'text': 'Tested code.'}]
        report = audit_coverage(expected,
            [row('old-A', 'Used SQL.'), row('B', 'Built software.')],
            [row('C', 'Validated records.')], {'old-A': 'current-A'})
        self.assertEqual(['D'], report['absent_from_both'])
        self.assertEqual(['C', 'D'], report['absent_from_training'])
        self.assertEqual(['C'], report['evaluation_only'])
        self.assertEqual(['B'], report['text_differences'])
        self.assertFalse(report['training_authorized'])
        self.assertNotIn('Used SQL.', json.dumps(report))

    def test_same_text_does_not_imply_identity(self):
        report = audit_coverage([{'id': 'A', 'text': 'Used SQL.'}], [row('B', 'Used SQL.')])
        self.assertEqual(['A'], report['absent_from_training'])
        self.assertEqual(['B'], report['unexpected_ids'])

    def test_conflicting_variants_and_overlap_are_reported(self):
        report = audit_coverage([{'id': 'A', 'text': 'Used SQL.'}],
            [row('A', 'Used SQL.'), row('A', 'Used Python.')], [row('A', 'Used SQL.')])
        self.assertEqual(['A'], report['multiple_text_variants'])
        self.assertEqual(['A'], report['train_evaluation_fact_overlap'])
        self.assertEqual(['A'], report['text_differences'])
        self.assertEqual(2, report['training_rows'])

    def test_whitespace_only_difference_is_not_semantic_review(self):
        report = audit_coverage([{'id': 'A', 'text': 'Used SQL.'}], [row('A', ' Used\nSQL. ')])
        self.assertEqual([], report['text_differences'])

    def test_duplicate_expected_and_ambiguous_aliases_fail(self):
        facts = [{'id': 'A', 'text': 'A'}, {'id': 'B', 'text': 'B'}]
        for expected, aliases in [(facts + [facts[0]], {}),
                                  (facts, {'X': 'A', 'Y': 'A'}),
                                  (facts, {'A': 'B'}), (facts, {'X': 'missing'})]:
            with self.subTest(expected=expected, aliases=aliases), self.assertRaises(ValueError):
                audit_coverage(expected, [row('X', 'A')], aliases=aliases)

    def test_empty_or_malformed_inputs_fail_without_echoing_payload(self):
        for bad in [[], [{}], [row('A', '')], [{'messages': 'private payload'}]]:
            with self.subTest(bad=bad), self.assertRaises(ValueError) as error:
                audit_coverage([{'id': 'A', 'text': 'A'}], bad)
            self.assertNotIn('private payload', str(error.exception))

    def test_cli_is_read_only_and_binds_exact_input_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root/'expected.json'
            train = root/'train.jsonl'
            expected.write_text(json.dumps([{'id': 'A', 'text': 'Used SQL.'}]), encoding='utf8')
            train.write_text(json.dumps(row('A', 'Used SQL.'))+'\n', encoding='utf8')
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            script = Path(__file__).resolve().parents[1]/'scripts/audit_training_coverage.py'
            result = subprocess.run([sys.executable, str(script), '--expected', str(expected),
                '--train', str(train)], capture_output=True, text=True, encoding='utf8')
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual('review_required', report['status'])
            self.assertEqual(hashlib.sha256(before['train.jsonl']).hexdigest(),
                             report['input_file_sha256']['training'])
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            train.write_text('private broken payload', encoding='utf8')
            result = subprocess.run([sys.executable, str(script), '--expected', str(expected),
                '--train', str(train)], capture_output=True, text=True, encoding='utf8')
            self.assertEqual(1, result.returncode)
            self.assertEqual('needs_input', json.loads(result.stdout)['status'])
            self.assertNotIn('private broken payload', result.stdout + result.stderr)
            self.assertNotIn(str(root), result.stdout + result.stderr)

    def test_size_and_row_bounds_reject_without_sampling(self):
        from core.training_coverage import MAX_ROWS
        with self.assertRaises(ValueError):
            audit_coverage([{'id': 'A', 'text': 'A'}], [row('A', 'A')] * (MAX_ROWS + 1))
        with self.assertRaises(ValueError):
            audit_coverage([{'id': 'A', 'text': 'A'}], [row('A', 'A')] * MAX_ROWS, [row('A', 'A')])

    def test_cli_keeps_unicode_separators_inside_a_jsonl_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = 'Used SQL\u2028for reporting\u2029and validation.'
            expected = root/'expected.json'
            train = root/'train.jsonl'
            expected.write_text(json.dumps([{'id': 'A', 'text': text}], ensure_ascii=False), encoding='utf8')
            example = row('A', text)
            example['messages'][1]['content'] = json.dumps(
                {'candidate_fact': {'id': 'A', 'text': text}}, ensure_ascii=False)
            train.write_text(json.dumps(example, ensure_ascii=False)+'\n', encoding='utf8')
            script = Path(__file__).resolve().parents[1]/'scripts/audit_training_coverage.py'
            result = subprocess.run([sys.executable, str(script), '--expected', str(expected),
                '--train', str(train)], capture_output=True, text=True, encoding='utf8')
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(1, json.loads(result.stdout)['training_rows'])


if __name__ == '__main__':
    unittest.main()
