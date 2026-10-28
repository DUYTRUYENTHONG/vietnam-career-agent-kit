"""Catch workflow syntax failures locally before GitHub can schedule QA."""
from pathlib import Path
import unittest

import yaml


class WorkflowSyntaxTests(unittest.TestCase):
    def test_checked_in_workflows_parse_and_run_steps_are_strings(self):
        root = Path(__file__).resolve().parents[1]
        paths = list((root/'.github/workflows').glob('*.yml'))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(workflow=path.name):
                workflow = yaml.safe_load(path.read_text(encoding='utf8'))
                self.assertIsInstance(workflow['jobs'], dict)
                for job in workflow['jobs'].values():
                    for step in job.get('steps', []):
                        if 'run' in step:
                            self.assertIsInstance(step['run'], str)
