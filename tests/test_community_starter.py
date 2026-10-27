"""CV-first onboarding stays private, inert, finite and resumable."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.execution import Executor
from core.starter import start_campaign
from core.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]


class CommunityStarterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.cv = self.base / 'fictional-cv.md'
        self.cv.write_text('Fictional candidate. Used SQL in a classroom project.\n', encoding='utf8')
        self.work = Executor(self.base / 'private')

    def test_default_goal_is_100_without_confirming_facts_or_approvals(self):
        result = start_campaign(self.work, self.cv)
        self.assertEqual('ok', result.outcome)
        config = json.loads((self.work.data_dir / 'starter/intake.json').read_text(encoding='utf8'))
        self.assertEqual(100, config['goal']['target_confirmed'])
        self.assertEqual(['Strong fit', 'Plausible fit'], config['goal']['qualifying_fit'])
        self.assertEqual(hashlib.sha256(self.cv.read_bytes()).hexdigest(), config['cv']['sha256'])
        self.assertFalse(config['cv']['imported_as_evidence'])
        self.assertTrue(all(v is None for v in config['required_information'].values()))
        with self.work._db() as db:
            for table in ('jobs', 'candidate_profile', 'approvals', 'execution_submissions'):
                self.assertEqual(0, db.execute('SELECT count(*) FROM '+table).fetchone()[0])

    def test_resume_preserves_user_edits_and_rejects_changed_source_or_target(self):
        start_campaign(self.work, self.cv, target=12)
        note = self.work.data_dir / 'starter/GOAL.md'
        note.write_text('My private checkpoint', encoding='utf8')
        self.assertTrue(start_campaign(self.work, self.cv, target=12).data['reused'])
        self.assertEqual('My private checkpoint', note.read_text(encoding='utf8'))
        with self.assertRaises(WorkflowError):
            start_campaign(self.work, self.cv, target=100)
        self.cv.write_text('Different fictional evidence', encoding='utf8')
        with self.assertRaises(WorkflowError):
            start_campaign(self.work, self.cv, target=12)

    def test_bad_target_or_format_has_no_workspace_side_effect(self):
        for target in (0, -1, True, 10001):
            with self.assertRaises(ValueError):
                start_campaign(self.work, self.cv, target=target)
        unknown = self.base / 'not-a-cv.exe'
        unknown.write_bytes(b'not executed')
        with self.assertRaises(ValueError):
            start_campaign(self.work, unknown)
        self.assertFalse(self.work.data_dir.exists())

    def test_real_cli_from_another_directory_and_separate_user(self):
        other = self.base / 'other-private'
        command = [sys.executable, str(ROOT / 'scripts/kit.py'), '--data-dir', str(other),
                   'start-campaign', '--cv', str(self.cv), '--language', 'vi']
        result = subprocess.run(command, cwd=self.base, capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, result.returncode, result.stderr+result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(100, payload['data']['target_confirmed'])
        self.assertFalse(self.work.data_dir.exists())
        self.assertTrue((other / 'workflow.sqlite3').is_file())
        self.assertTrue((other / 'starter/GOAL.md').is_file())
