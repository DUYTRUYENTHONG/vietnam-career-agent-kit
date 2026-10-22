import unittest
from core.metrics import Trace


class TraceTests(unittest.TestCase):
    def test_monotonic_durations_failed_stage_and_unknown_are_explicit(self):
        ticks = iter([100, 1_000_100, 2_000_100, 4_000_100])
        trace = Trace(clock=lambda: next(ticks))
        with trace.stage('validation'): pass
        with self.assertRaises(ValueError):
            with trace.stage('review'): raise ValueError('fixture')
        report = trace.report(render_count=0)
        self.assertEqual([1.0, 2.0], [s['duration_ms'] for s in report['stages']])
        self.assertEqual('failed', report['stages'][1]['status'])
        self.assertIn('host_tokens', report['unavailable'])
        self.assertNotIn('host_tokens', report['observed'])
