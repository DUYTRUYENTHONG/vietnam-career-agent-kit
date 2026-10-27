"""Learning exports reuse exact review and avoid direct train/eval leakage."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

from core.learning import export_reviewed, check_export, _split
from core.ledger import canonical_hash
from core.workflow import WorkflowError
from scripts.demo_wording import seed, fictional_review


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work, self.model = seed(Path(self.tmp.name)/'private')

    def reviewed(self):
        self.work.import_wording(1, self.model)
        self.work.review_wording(1, fictional_review(self.work.wording_packet(1).data))

    def test_only_exact_reviewed_wording_exports_and_single_group_is_not_training_ready(self):
        self.work.import_wording(1, self.model)
        with self.assertRaises(WorkflowError): export_reviewed(self.work, [1], 'datasets/test')
        self.assertFalse(self.work.inside('datasets/test').exists())
        self.work.review_wording(1, fictional_review(self.work.wording_packet(1).data))
        result = export_reviewed(self.work, [1], 'datasets/test').data
        self.assertEqual(1, result['example_count'])
        self.assertFalse(result['ready_for_split'])
        self.assertFalse(result['training_performed'])
        self.assertEqual(0, result['provider_calls'])
        self.assertTrue(check_export(self.work, 'datasets/test').data['current_evidence_checked'])
        example = json.loads(self.work.inside('datasets/test/examples.jsonl').read_text(encoding='utf8'))
        self.assertNotIn('contacts', json.loads(example['messages'][1]['content']))
        output = json.loads(example['messages'][2]['content'])
        statuses = [s['review_status'] for section in output['sections'] for group in section['groups'] for s in group['statements']]
        self.assertTrue(statuses and all(status == 'pending' for status in statuses))
        self.assertFalse(self.work.inside('datasets/test/train.jsonl').exists())
        with self.assertRaises(WorkflowError): export_reviewed(self.work, [1], 'datasets/test')

    def test_revoked_review_or_changed_export_never_remains_current(self):
        self.reviewed(); export_reviewed(self.work, [1], 'datasets/test')
        path = self.work.inside('datasets/test/examples.jsonl')
        original = path.read_bytes(); path.write_bytes(original+b'changed')
        with self.assertRaises(WorkflowError): check_export(self.work, 'datasets/test')
        path.write_bytes(original)
        self.work.reject_wording(1, 'Fictional later factual concern')
        with self.assertRaises(WorkflowError): check_export(self.work, 'datasets/test')
        for ids, path in [([], 'datasets/empty'), ([1, 1], 'datasets/duplicate'), ([True], 'datasets/bool')]:
            with self.assertRaises(ValueError): export_reviewed(self.work, ids, path)
        with self.assertRaises(WorkflowError): export_reviewed(self.work, [1], '../escape')

    def test_job_and_duplicate_output_components_never_cross_splits(self):
        rows = [{'example_id': str(i), 'group_id': job, 'output_hash': output}
                for i, (job, output) in enumerate([('job-a', 'output-1'), ('job-a', 'output-2'),
                    ('job-b', 'output-2'), ('job-c', 'output-3'), ('job-d', 'output-4')])]
        train, evaluation, groups = _split(rows)
        self.assertEqual(3, groups)
        self.assertTrue(train and evaluation)
        self.assertFalse({e['group_id'] for e in train} & {e['group_id'] for e in evaluation})
        self.assertFalse({e['output_hash'] for e in train} & {e['output_hash'] for e in evaluation})
        self.assertEqual((train, evaluation, groups), _split(deepcopy(rows)))

    def test_cli_export_check_and_boolean_manifest_counts_are_rejected(self):
        self.reviewed()
        cli = Path(__file__).resolve().parents[1]/'scripts/kit.py'
        args = [sys.executable, str(cli), '--data-dir', str(self.work.data_dir)]
        for command in (['learning-export', '--job-id', '1', '--output', 'datasets/cli'],
                        ['learning-check', '--directory', 'datasets/cli']):
            result = subprocess.run(args+command, capture_output=True, encoding='utf8', timeout=15)
            self.assertEqual(0, result.returncode, result.stdout+result.stderr)
        path = self.work.inside('datasets/cli/manifest.json')
        manifest = json.loads(path.read_text(encoding='utf8'))
        manifest['example_count'] = True
        manifest['manifest_fingerprint'] = canonical_hash({k: v for k, v in manifest.items() if k != 'manifest_fingerprint'})
        path.write_text(json.dumps(manifest), encoding='utf8')
        with self.assertRaises(WorkflowError): check_export(self.work, 'datasets/cli')

    def test_two_reviewed_jobs_export_disjoint_files_and_recomputed_manifest_cannot_fake_counts(self):
        self.reviewed()
        packet = self.work.wording_packet(1).data
        job, _ = self.work.job_document(1)
        other = deepcopy(job)
        other.update(platform_job_id=job['platform_job_id']+'-second', req_id=job['req_id']+'-second',
                     url=job['url']+'/second')
        self.work.import_job(other)
        self.work.assess(2, {'schema_version': '1.0', 'rows': packet['assessment']['rows']})
        model = deepcopy(self.model); model['job_id'] = 2
        for section in model['sections']:
            for group in section['groups']:
                for statement in group['statements']:
                    if 'F1' in statement['source_fact_ids']:
                        statement.update(text='Used SQL to query a fictional sales dataset.', transformation='faithful_paraphrase')
        self.work.import_wording(2, model)
        self.work.review_wording(2, fictional_review(self.work.wording_packet(2).data))
        result = export_reviewed(self.work, [1, 2], 'datasets/two-jobs').data
        self.assertTrue(result['ready_for_split'])
        self.assertTrue(check_export(self.work, 'datasets/two-jobs').data['current_evidence_checked'])
        for name in ('train.jsonl', 'evaluation.jsonl'):
            rows = self.work.inside('datasets/two-jobs/'+name).read_text(encoding='utf8').splitlines()
            self.assertEqual(1, len(rows))
        path = self.work.inside('datasets/two-jobs/manifest.json')
        manifest = json.loads(path.read_text(encoding='utf8'))
        manifest['example_count'] = 99
        manifest['manifest_fingerprint'] = canonical_hash({k: v for k, v in manifest.items() if k != 'manifest_fingerprint'})
        path.write_text(json.dumps(manifest), encoding='utf8')
        with self.assertRaises(WorkflowError): check_export(self.work, 'datasets/two-jobs')
