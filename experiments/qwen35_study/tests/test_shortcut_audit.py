import unittest

from experiments.qwen35_study.shortcut_audit import fit, predict


class ShortcutAudit(unittest.TestCase):
    def test_requirement_collision_retains_both_labels(self):
        model = fit([('Use SQL', 'direct'), ('Use SQL', 'unknown')])
        self.assertEqual(model[3]['use sql'], {'direct': 1, 'unknown': 1})

    def test_unknown_words_back_off_to_training_prior(self):
        model = fit([('SQL', 'direct'), ('Python', 'unknown'), ('Python', 'unknown')])
        self.assertEqual(predict(model, 'unseen_word'), 'unknown')
        self.assertEqual(predict(model, 'SQL SQL SQL'), 'direct')

    def test_empty_training_fails(self):
        with self.assertRaisesRegex(ValueError, 'Empty'):
            fit([])
