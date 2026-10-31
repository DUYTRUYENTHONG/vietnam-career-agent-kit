"""Fictional model inputs must describe the same job in both representations."""
from pathlib import Path
import tempfile
import unittest

from scripts.demo_wording import seed


class DemoWordingTests(unittest.TestCase):
    def test_each_role_has_consistent_raw_and_structured_requirements(self):
        roles = {'data': 'SQL', 'technical': 'Python', 'commercial': 'onboarding'}
        for role, skill in roles.items():
            with self.subTest(role=role), tempfile.TemporaryDirectory() as tmp:
                work, _ = seed(Path(tmp)/'private', candidate=role)
                job, _ = work.job_document(1)
                self.assertIn(skill+' project experience required', job['raw_jd'])
                self.assertIn('relevant certification preferred', job['raw_jd'])
                self.assertNotIn('requirements documentation preferred', job['raw_jd'])
                self.assertEqual(skill, job['requirements'][0]['value'])
                self.assertEqual('certification', job['requirements'][1]['field'])
                if role != 'data':
                    self.assertNotIn('SQL', job['raw_jd'])
                self.assertIn('FICTIONAL LOCAL DEMONSTRATION ONLY', job['raw_jd'])
                self.assertIn('No real application destination exists', job['raw_jd'])


if __name__ == '__main__':
    unittest.main()
