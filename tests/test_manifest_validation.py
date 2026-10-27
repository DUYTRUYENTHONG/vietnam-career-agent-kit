"""Every entry stays checked; long passes must detect final source/expiry drift."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_manifests as fixtures
from test_documents import fake_render
from core.workflow import WorkflowError


class ManifestValidationTests(unittest.TestCase):
    tearDown = fixtures.ManifestTests.tearDown
    plan = fixtures.ManifestTests.plan
    approve = fixtures.ManifestTests.approve

    def setUp(self):
        fixtures.ManifestTests.setUp(self)
        root = Path(__file__).resolve().parents[1] / 'examples/fictional'
        load = lambda name: json.loads((root / name).read_text(encoding='utf8'))
        job = load('job.json')
        job.update(platform_job_id='fictional-2', req_id='FICT-2', url='https://jobs.example.test/FICT-2')
        self.work.import_job(job)
        self.work.assess(2, load('matrix.json'))
        self.draft2 = self.work.prepare(2, load('plan.json')).data
        with patch('core.documents.render_files', side_effect=fake_render):
            self.render2 = self.work.render(2).data
        review = {'schema_version': '1.0', 'render_fingerprint': self.render2['fingerprint'],
                  'reviewed_pages': [1],
                  'checks': dict.fromkeys(['content', 'layout', 'glyphs', 'language'], True)}
        path = self.root / 'review-2.json'
        path.write_text(json.dumps(review), encoding='utf8')
        self.work.review_documents(self.render2['render_id'], path)
        plan = self.plan()
        second = copy.deepcopy(plan['entries'][0])
        second.update(job_id=2, render_id=self.render2['render_id'],
                      destination='https://apply.example.test/form/FICT-2')
        plan['entries'].append(second)
        plan['submission_limit'] = 2
        result = self.work.create_manifest(plan).data
        self.approve(result)
        self.fingerprint = result['fingerprint']

    def test_all_job_reads_are_repeated_on_every_pass(self):
        for _ in range(2):
            with patch.object(self.work, 'job_document', wraps=self.work.job_document) as jobs:
                self.work.check_manifest(self.fingerprint)
            self.assertEqual([1, 1, 2, 2], [call.args[0] for call in jobs.call_args_list])

    def test_other_entry_pdf_draft_and_jd_tampering_still_block(self):
        paths = [self.root / self.render2['files']['pdf']['path'],
                 self.root / self.draft2['files']['cv']['path'],
                 self.work.inside(self.work.get_job(2)['raw_jd_path'])]
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(b'FICTIONAL TAMPERED INPUT')
                try:
                    with self.assertRaises(WorkflowError):
                        self.work.check_manifest(self.fingerprint)
                finally:
                    path.write_bytes(original)
                self.assertTrue(self.work.check_manifest(self.fingerprint).data['approved'])

    def test_other_entry_rejected_review_still_blocks(self):
        self.work.reject_documents(self.render2['render_id'], 'Fictional layout issue')
        with self.assertRaises(WorkflowError):
            self.work.check_manifest(self.fingerprint)

    def test_source_change_between_calls_is_not_cached(self):
        self.work.check_manifest(self.fingerprint)
        source = self.work.inspect_profile().data['sources'][0]
        self.work.inside(source['path']).write_bytes(b'FICTIONAL CHANGED SOURCE')
        with self.assertRaises(WorkflowError):
            self.work.check_manifest(self.fingerprint)

    def test_profile_source_change_during_pass_is_detected_at_end(self):
        source = self.work.inspect_profile().data['sources'][0]
        original = self.work.manifest_render

        def changed_during_validation(entry, fingerprint):
            result = original(entry, fingerprint)
            if entry['job_id'] == 2:
                self.work.inside(source['path']).write_bytes(b'FICTIONAL MID-PASS CHANGE')
            return result

        with patch.object(self.work, 'manifest_render', side_effect=changed_during_validation):
            with self.assertRaises(WorkflowError):
                self.work.check_manifest(self.fingerprint)

    def test_expiry_during_long_validation_pass_blocks(self):
        now = datetime.now(timezone.utc)
        with patch('core.manifests.now_utc', side_effect=[now, now + timedelta(hours=3)]):
            with self.assertRaises(WorkflowError):
                self.work.check_manifest(self.fingerprint)
