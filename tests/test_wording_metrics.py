"""Fictional recorded measurements; no models, credentials or candidate data."""
import unittest

from core.wording_evaluation import _observed_metrics_summary as observed_metrics_summary


def row(input_tokens=10, output_tokens=20, generation_ms=100, loading=False):
    return {'metrics': {'input_tokens': input_tokens, 'output_tokens': output_tokens,
                        'generation_ms': generation_ms, 'load_time_included': loading}}


class WordingMetricsTests(unittest.TestCase):
    def test_complete_cohort_uses_total_tokens_over_total_time(self):
        result = observed_metrics_summary([row(10, 100, 100), row(30, 100, 900)])
        self.assertEqual(2, result['examples'])
        self.assertEqual(40, result['input_tokens_total'])
        self.assertEqual(200, result['output_tokens_total'])
        self.assertEqual(1000, result['generation_ms_total'])
        self.assertEqual(200, result['generation_output_tokens_per_second'])
        self.assertEqual('generation_only', result['timing_scope'])

    def test_missing_values_do_not_become_zero_or_partial_totals(self):
        result = observed_metrics_summary([row(), row(None, 0, None)])
        self.assertEqual(1, result['input_tokens_observed_examples'])
        self.assertEqual(2, result['output_tokens_observed_examples'])
        self.assertEqual(1, result['generation_ms_observed_examples'])
        self.assertIsNone(result['input_tokens_total'])
        self.assertEqual(20, result['output_tokens_total'])
        self.assertIsNone(result['generation_ms_total'])
        self.assertIsNone(result['generation_output_tokens_per_second'])
        self.assertEqual('incomplete', result['timing_scope'])
        unknown = observed_metrics_summary([{'metrics': None}])
        self.assertIsNone(unknown['output_tokens_total'])
        self.assertEqual(0, unknown['output_tokens_observed_examples'])

    def test_loading_and_mixed_scopes_do_not_report_generation_throughput(self):
        for inputs, scope in [([row(loading=True)], 'includes_model_loading'),
                              ([row(), row(loading=True)], 'mixed')]:
            with self.subTest(scope=scope):
                result = observed_metrics_summary(inputs)
                self.assertEqual(scope, result['timing_scope'])
                self.assertIsNotNone(result['generation_ms_total'])
                self.assertIsNone(result['generation_output_tokens_per_second'])

    def test_observed_zero_is_distinct_from_unknown_and_zero_time_has_no_rate(self):
        result = observed_metrics_summary([row(0, 0, 0)])
        self.assertEqual(0, result['input_tokens_total'])
        self.assertEqual(0, result['output_tokens_total'])
        self.assertEqual(0, result['generation_ms_total'])
        self.assertIsNone(result['generation_output_tokens_per_second'])
        self.assertEqual(0, observed_metrics_summary([row(0, 0, 5)])['generation_output_tokens_per_second'])

    def test_finite_rows_cannot_produce_nonfinite_aggregate_or_rate(self):
        for inputs in ([row(generation_ms=1e308), row(generation_ms=1e308)],
                       [row(output_tokens=10**308), row(output_tokens=10**308)],
                       [row(output_tokens=10**308, generation_ms=1e-300)]):
            with self.subTest(inputs=inputs):
                with self.assertRaisesRegex(ValueError, 'finite'):
                    observed_metrics_summary(inputs)

    def test_large_finite_rate_does_not_overflow_only_because_of_unit_conversion(self):
        result = observed_metrics_summary([row(output_tokens=10**308, generation_ms=1e308)])
        self.assertEqual(1000, result['generation_output_tokens_per_second'])


if __name__ == '__main__':
    unittest.main()
