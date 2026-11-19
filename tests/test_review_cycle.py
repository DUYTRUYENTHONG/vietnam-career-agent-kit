"""Fictional before/after grades and recorded grader outputs only."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.contracts import ContractError
from core.learning import export_reviewed
from core.ledger import canonical_hash
from core.review_cycle import compare, decode, evaluate, read_examples
from scripts.demo_wording import seed, fictional_review


class ReviewCycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work, model = seed(self.root / 'private')
        self.work.import_wording(1, model)
        review = fictional_review(self.work.wording_packet(1).data)
        review['rubric_sha256'] = self.work.wording_packet(1).data['review_rubric_sha256']
        self.work.review_wording(1, review)
        export_reviewed(self.work, [1], 'datasets/before', task='cv-review')
        self.before_path = self.work.inside('datasets/before/examples.jsonl')
        self.before = read_examples(self.before_path)[0][0]

    def changed(self, *, score=3, evidence=False, same_cv=False):
        row = deepcopy(self.before)
        inputs = json.loads(row['messages'][1]['content'])
        if not same_cv:
            inputs['cv_sections'][0]['groups'][0]['statements'][0]['text'] += ' Fictional revision.'
        if evidence:
            inputs['facts'][0]['quote'] += ' Additional fictional context.'
        row['messages'][1]['content'] = json.dumps(inputs)
        target = json.loads(row['messages'][2]['content'])
        target['editorial']['relevance']['score'] = score
        row['messages'][2]['content'] = json.dumps(target)
        row['output_hash'] = canonical_hash(target)
        row['provenance'].update(draft_fingerprint=canonical_hash(inputs),
            wording_fingerprint=canonical_hash(inputs['cv_sections']), review_hash=canonical_hash(target))
        row['example_id'] = canonical_hash(row['provenance'])
        return row

    def test_dimension_deltas_do_not_invent_a_winner_or_training(self):
        after = self.changed(score=0)
        report = compare(self.before, after)
        old = json.loads(self.before['messages'][2]['content'])['editorial']['relevance']['score']
        self.assertEqual(-old, report['dimensions']['relevance']['delta'])
        self.assertFalse(report['evidence_changed'])
        self.assertFalse(report['training_performed'])
        self.assertFalse(report['current_evidence_revalidated'])
        self.assertNotIn('overall_score', report)

    def test_changed_evidence_and_identical_cv_are_not_tailoring_gains(self):
        self.assertIn('cannot be attributed', compare(self.before, self.changed(evidence=True))['interpretation'])
        self.assertIn('CV unchanged', compare(self.before, self.changed(same_cv=True))['interpretation'])

    def test_other_job_candidate_rubric_and_changed_requirements_rejected(self):
        for key in ('job_id', 'profile_fingerprint', 'review_rubric_sha256'):
            bad = self.changed()
            bad['provenance'][key] = 2 if key == 'job_id' else 'a' * 64
            bad['example_id'] = canonical_hash(bad['provenance'])
            with self.assertRaises((ContractError, KeyError)): compare(self.before, bad)
        bad = self.changed()
        inputs = json.loads(bad['messages'][1]['content']); inputs['requirements'] = []
        bad['messages'][1]['content'] = json.dumps(inputs)
        with self.assertRaises(ContractError): compare(self.before, bad)

    def test_changed_labels_and_unknown_citations_rejected(self):
        for change in ('score', 'citation', 'leak'):
            bad = self.changed()
            if change == 'leak':
                inputs = json.loads(bad['messages'][1]['content']); inputs['editorial'] = {}
                bad['messages'][1]['content'] = json.dumps(inputs)
            else:
                target = json.loads(bad['messages'][2]['content'])
                if change == 'score': target['editorial']['relevance']['score'] = True
                else: target['editorial']['relevance']['statement_ids'] = ['invented']
                bad['messages'][2]['content'] = json.dumps(target)
                bad['output_hash'] = canonical_hash(target)
            with self.assertRaises(ContractError): compare(self.before, bad)
        stale = self.changed(); stale['output_hash'] = '0' * 64
        with self.assertRaises(ContractError): compare(self.before, stale)

    def test_full_cohort_penalizes_missing_and_invalid_outputs(self):
        second = self.changed()
        target = json.loads(self.before['messages'][2]['content'])['editorial']
        report = evaluate([self.before, second], [{'example_id': self.before['example_id'], 'editorial': target}])
        self.assertEqual(1, report['invalid_or_missing_count'])
        self.assertEqual(.5, report['full_cohort_exact_score_vector_rate'])
        self.assertEqual(0, report['valid_only_mae']['relevance'])
        self.assertEqual(1.5, report['full_cohort_penalized_mae']['relevance'])
        report = evaluate([self.before], [{'example_id': self.before['example_id'], 'editorial': {}}])
        self.assertIsNone(report['valid_only_mae']['relevance'])
        self.assertEqual(3, report['full_cohort_penalized_mae']['relevance'])

    def test_prediction_duplicates_unknowns_and_duplicate_json_keys_rejected(self):
        prediction = {'example_id': self.before['example_id'], 'editorial': {}}
        for values in ([prediction, prediction], [{'example_id': 'unknown', 'editorial': {}}]):
            with self.assertRaises(ContractError): evaluate([self.before], values)
        for value in ('{"score":1,"score":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ContractError): decode(value)

    def test_cli_writes_new_private_report_without_changing_ledger_or_inputs(self):
        after = self.changed()
        after_path = self.root / 'after.jsonl'; after_path.write_text(json.dumps(after) + '\n', encoding='utf8')
        output = self.root / 'reports/comparison.json'
        command = [sys.executable, 'scripts/compare_cv_reviews.py', 'compare', '--before', str(self.before_path),
            '--after', str(after_path), '--job-id', '1', '--output', str(output)]
        ledger = self.work.db_path.read_bytes(); source = self.before_path.read_bytes()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(2, len(json.loads(output.read_text())['input_files']))
        self.assertEqual(ledger, self.work.db_path.read_bytes())
        self.assertEqual(source, self.before_path.read_bytes())
        self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
        command[-1] = str(Path('reports/forbidden-review.json').resolve())
        self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)

    def test_evaluation_cli_covers_recorded_predictions(self):
        predictions = self.root / 'predictions.json'
        predictions.write_text(json.dumps([{'example_id': self.before['example_id'],
            'editorial': json.loads(self.before['messages'][2]['content'])['editorial']}]), encoding='utf8')
        output = self.root / 'grader-report.json'
        result = subprocess.run([sys.executable, 'scripts/compare_cv_reviews.py', 'evaluate',
            '--references', str(self.before_path), '--predictions', str(predictions),
            '--output', str(output)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(output.read_text())
        self.assertEqual(1, report['valid_count'])
        self.assertEqual(0, report['full_cohort_penalized_mae']['specificity'])


if __name__ == '__main__': unittest.main()
