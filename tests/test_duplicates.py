import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.workflow import Preparation, WorkflowError

ROOT = Path(__file__).resolve().parents[1]


class DuplicateCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.work = Preparation(self.base / 'private', self.repo)
        self.work.init()

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, ident, **changes):
        record = dict(platform='fictional', platform_job_id=ident,
                      employer='Example Software', req_id=ident,
                      title='Solutions Consultant', city='HCMC',
                      url='https://jobs.example.test/' + ident,
                      raw_jd='Fictional role only.')
        record.update(changes)
        return self.work.add_job(**record)

    def test_different_ids_and_urls_surface_prior_attempts_without_merging(self):
        first = self.add('post-a', city='Ho Chi Minh City')
        second = self.add('post-b', title='  SOLUTIONS   CONSULTANT ')
        with self.work._db() as db:
            db.execute("UPDATE jobs SET state='submission_uncertain' WHERE id=?", (first['id'],))
        before = [self.work.get_job(row['id']) for row in (first, second)]
        with patch.object(self.work, 'hash_file', side_effect=AssertionError('No artifact scan')):
            result = self.work.duplicate_candidates(second['id'])
        self.assertEqual('ok', result.outcome)
        self.assertTrue(result.data['requires_identity_review'])
        self.assertFalse(result.data['deduplication_complete'])
        self.assertEqual([first['id']], [row['id'] for row in result.data['candidates']])
        candidate = result.data['candidates'][0]
        self.assertEqual(['same_employer_title_city'], candidate['signals'])
        self.assertTrue(candidate['prior_attempt_needs_reconciliation'])
        self.assertEqual(before, [self.work.get_job(row['id']) for row in (first, second)])

    def test_same_url_is_a_hint_even_when_title_or_city_changes(self):
        first = self.add('post-a')
        second = self.add('post-b', title='Renamed Role', city='Hanoi', url=first['url'])
        result = self.work.duplicate_candidates(second['id']).data
        self.assertEqual(['same_url'], result['candidates'][0]['signals'])
        self.assertFalse(result['candidates'][0]['prior_attempt_needs_reconciliation'])

    def test_distinct_employer_title_or_city_and_other_workspaces_are_not_included(self):
        first = self.add('post-a')
        self.add('post-b', employer='Different Employer')
        self.add('post-c', title='Senior Solutions Consultant')
        self.add('post-d', city='Hanoi')
        other = Preparation(self.base / 'other-private', self.repo)
        other.init()
        other.add_job(platform='fictional', platform_job_id='elsewhere', employer=first['employer'],
                      req_id='elsewhere', title=first['title'], city=first['city'],
                      url='https://jobs.example.test/elsewhere', raw_jd='Fictional only.')
        result = self.work.duplicate_candidates(first['id']).data
        self.assertEqual([], result['candidates'])
        self.assertFalse(result['requires_identity_review'])
        self.assertFalse(result['external_history_checked'])
        self.assertFalse(result['deduplication_complete'])

    def test_closed_confirmed_records_remain_visible_and_no_event_is_written(self):
        first = self.add('post-a')
        second = self.add('post-b')
        with self.work._db() as db:
            db.execute("UPDATE jobs SET state='confirmed_submitted',liveness='closed' WHERE id=?", (first['id'],))
            before = db.execute('SELECT count(*) FROM events').fetchone()[0]
        result = self.work.duplicate_candidates(second['id']).data
        self.assertEqual('closed', result['candidates'][0]['liveness'])
        self.assertTrue(result['candidates'][0]['prior_attempt_needs_reconciliation'])
        with self.work._db() as db:
            self.assertEqual(before, db.execute('SELECT count(*) FROM events').fetchone()[0])

    def test_unknown_job_is_structured_and_real_cli_exposes_candidates(self):
        with self.assertRaises(WorkflowError) as error:
            self.work.duplicate_candidates(999)
        self.assertEqual('needs_input', error.exception.outcome)
        self.add('post-a')
        second = self.add('post-b')
        for ident, code in [(second['id'], 0), (999, 2)]:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/kit.py'),
                                     '--data-dir', str(self.work.data_dir),
                                     'duplicate-candidates', '--job-id', str(ident)],
                                    cwd=self.tmp.name, capture_output=True, encoding='utf8', timeout=15)
            self.assertEqual(code, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            if code == 0:
                self.assertEqual(1, len(payload['data']['candidates']))
            else:
                self.assertEqual('needs_input', payload['outcome'])


if __name__ == '__main__':
    unittest.main()
