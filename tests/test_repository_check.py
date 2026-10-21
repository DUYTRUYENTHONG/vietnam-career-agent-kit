import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('public_check',ROOT/'scripts/check_repository.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

class PublicCheckTests(unittest.TestCase):
    def test_private_and_secret_patterns_are_rejected(self):
        self.assertTrue(checker.issues_for(Path('data/cv.txt'),'fictional'))
        self.assertTrue(checker.issues_for(Path('doc.md'),'ghp_'+'A'*40))
        self.assertTrue(checker.issues_for(Path('doc.md'),'person@'+'company.test'))
        self.assertTrue(checker.issues_for(Path('doc.md'),'C:/'+ 'Users/Example/private'))

    def test_fictional_public_text_is_allowed(self):
        self.assertEqual(checker.issues_for(Path('templates/profile.json'),'person@example.invalid'),[])

if __name__=='__main__':unittest.main()
