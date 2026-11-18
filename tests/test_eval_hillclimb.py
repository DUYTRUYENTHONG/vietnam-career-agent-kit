"""Deterministic fictional study-state controls; not model-performance evidence."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from core import eval_hillclimb as h
from core.tailor_benchmark import ARMS, binding


class HillclimbTests(unittest.TestCase):
    def setUp(self):
        self.plan = {'schema_version': '1.0', 'development_cohort_sha256': 'a'*64,
            'test_cohort_sha256': 'b'*64, 'development_groups': ['dev-a', 'dev-b'],
            'test_groups': ['test-a'], 'starting_variant_sha256': 'c'*64,
            'allowed_levers': ['prompt'], 'max_rounds': 3, 'max_free_seconds': 100,
            'prior_free_seconds': 50, 'cumulative_cap_seconds': 150, 'stop_after_non_improving': 2}
        self.proposal = {'parent_variant_sha256': 'c'*64, 'variant_sha256': 'd'*64,
            'lever': 'prompt', 'hypothesis': 'Preserve prototype scope.',
            'changed_files': ['prompt-v1.txt'], 'free_seconds': 20}
        self.report = {'kind': 'tailor_benchmark_comparison', 'cohort_sha256': 'a'*64,
            'comparison': 'prompt', 'all_outputs_human_reviewed': True,
            'candidate_condition': 'base_evidence', 'baseline_system_sha256': 'c'*64,
            'candidate_system_sha256': 'd'*64, 'candidate_adapter_sha256': None,
            'primary_quality_delta': 0.4, 'paired_cluster_bootstrap_95_interval': [0.1, 0.7],
            'candidate_experiment_gate_met': False,
            'arms': {k: {'invalid_or_missing': 0, 'factuality_failures': 0,
                'scope_failures': 0, 'qualifier_failures': 0, 'passed': 8} for k in ARMS[:2]}}

    def test_development_gain_is_not_test_or_promotion(self):
        r = h.record_round(self.plan, [], self.proposal, self.report)
        self.assertEqual(r['decision'], 'keep_candidate_for_final_test')
        self.assertFalse(r['test_consumed']); self.assertFalse(r['promotion_performed'])

    def test_test_scores_cannot_drive_hillclimb(self):
        self.report['cohort_sha256'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'never the test'):
            h.record_round(self.plan, [], self.proposal, self.report)

    def test_unsafe_gain_rejected_and_noise_keeps_parent(self):
        self.report['arms']['base_evidence']['qualifier_failures'] = 1
        self.assertEqual(h.record_round(self.plan, [], self.proposal, self.report)['decision'], 'reject_regression')
        self.report['arms']['base_evidence']['qualifier_failures'] = 0
        self.report['paired_cluster_bootstrap_95_interval'] = [-0.1, 0.7]
        self.assertEqual(h.record_round(self.plan, [], self.proposal, self.report)['decision'], 'inconclusive_keep_parent')
        self.report['paired_cluster_bootstrap_95_interval'] = [0.1, 0.7]
        self.report['arms']['base_evidence']['passed'] = 7
        self.assertEqual(h.record_round(self.plan, [], self.proposal, self.report)['decision'], 'reject_regression')

    def test_budget_and_family_overlap_fail(self):
        self.proposal['free_seconds'] = 101
        with self.assertRaisesRegex(ValueError, 'budget'):
            h.record_round(self.plan, [], self.proposal, self.report)
        self.plan['test_groups'] = ['dev-a']
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            h.validate_plan(self.plan)

    def test_stop_after_non_improvement_and_preserve_charges(self):
        self.report['primary_quality_delta'] = 0
        x = h.record_round(self.plan, [], self.proposal, self.report)
        y = h.record_round(self.plan, [x], self.proposal, self.report)
        self.assertEqual(y['cumulative_free_seconds'], 90)
        with self.assertRaisesRegex(ValueError, 'stop reached'):
            h.record_round(self.plan, [x, y], self.proposal, self.report)

    def test_mutated_parent_and_unreviewed_scores_rejected(self):
        self.proposal['parent_variant_sha256'] = 'e'*64
        with self.assertRaisesRegex(ValueError, 'current development winner'):
            h.record_round(self.plan, [], self.proposal, self.report)
        self.proposal['parent_variant_sha256'] = 'c'*64
        self.report['all_outputs_human_reviewed'] = False
        with self.assertRaisesRegex(ValueError, 'human'):
            h.record_round(self.plan, [], self.proposal, self.report)

    def test_final_requires_selected_winner_on_same_test(self):
        r = h.record_round(self.plan, [], self.proposal, self.report)
        final = deepcopy(self.report); final['cohort_sha256'] = 'b'*64
        self.assertTrue(h.final_test(self.plan, [r], final)['test_consumed'])
        final['candidate_system_sha256'] = 'e'*64
        with self.assertRaisesRegex(ValueError, 'different selected'):
            h.final_test(self.plan, [r], final)

    def test_history_cannot_reset_spent_time(self):
        self.report['primary_quality_delta'] = 0
        r = h.record_round(self.plan, [], self.proposal, self.report)
        r['free_seconds'] = -20
        with self.assertRaisesRegex(ValueError, 'spent time'):
            h.record_round(self.plan, [r], self.proposal, self.report)

    def test_cli_final_consumes_test_once_and_closes_study(self):
        from scripts.hillclimb_eval import main
        from core.tailor_benchmark import json_bytes
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            root = Path(directory)
            for name, value in [('plan', self.plan), ('proposal', self.proposal), ('dev', self.report)]:
                (root/(name+'.json')).write_bytes(json_bytes(value))
            args = ['--root', directory, '--study', 'study']
            self.assertEqual(main(args+['init', '--plan', 'plan.json']), 0)
            self.assertEqual(main(args+['record', '--proposal', 'proposal.json', '--report', 'dev.json']), 0)
            final = deepcopy(self.report); final['cohort_sha256'] = 'b'*64
            (root/'test.json').write_bytes(json_bytes(final))
            self.assertEqual(main(args+['final', '--report', 'test.json']), 0)
            original = (root/'study/final_test.json').read_bytes()
            self.assertEqual(main(args+['final', '--report', 'test.json']), 1)
            self.assertEqual(main(args+['record', '--proposal', 'proposal.json', '--report', 'dev.json']), 1)
            self.assertEqual((root/'study/final_test.json').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
