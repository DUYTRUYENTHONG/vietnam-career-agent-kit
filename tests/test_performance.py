"""Observed usage stays source-bound, immutable, scoped and honest about gaps."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from core.execution import Executor
from core.ledger import utc_now
from core.performance import record, report, export, render
from core.workflow import WorkflowError


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Executor(Path(self.tmp.name) / 'private')
        self.work.init()
        self.proof = self.work.data_dir / 'usage-export.json'
        self.proof.write_text('{"scope":"fictional host usage export"}', encoding='utf8')

    def event(self, identifier='call-1', **changes):
        value = {'schema_version': '1.0', 'event_id': identifier, 'task_id': 'task-1',
            'workload_id': 'fictional-tailoring-en', 'phase': 'generation',
            'provider_id': 'fictional-host', 'model_id': 'example/model-a', 'effort': 'low',
            'status': 'success', 'accepted': True, 'observed_utc': utc_now(), 'duration_ms': 10,
            'usage': {'kind': 'per_call', 'input_tokens': 100, 'output_tokens': 20,
                      'cached_input_tokens': 40, 'reasoning_tokens': 5},
            'cost': {'amount': '0.01', 'currency': 'USD'},
            'source': {'kind': 'host_export', 'path': 'usage-export.json',
                       'sha256': hashlib.sha256(self.proof.read_bytes()).hexdigest()}}
        value.update(changes)
        return value

    def test_partial_usage_and_currencies_are_not_inferred_or_double_counted(self):
        record(self.work, self.event())
        record(self.work, self.event('call-2', duration_ms=30, status='failed', accepted=False,
            usage={'kind': 'per_call', **{k: None for k in self.event()['usage'] if k != 'kind'}}, cost=None))
        record(self.work, self.event('call-3', model_id='example/model-b',
            cost={'amount': '0.05', 'currency': 'EUR'}))
        result = report(self.work).data
        self.assertEqual(3, result['record_count'])
        a, b = result['groups']
        self.assertEqual(100, a['known_tokens']['input_tokens'])
        self.assertEqual(20, a['known_tokens']['output_tokens'])
        self.assertEqual({'known': 1, 'missing': 1}, a['token_coverage']['input_tokens'])
        self.assertEqual(20, a['duration_ms']['p50'])
        self.assertEqual(30, a['duration_ms']['p95'])
        self.assertEqual(1, a['accepted_observations'])
        self.assertEqual({'USD': '0.01'}, a['known_charges'])
        self.assertEqual(1, a['missing_charge_observations'])
        self.assertEqual({'EUR': '0.05'}, b['known_charges'])

    def test_agent_turns_never_mix_with_model_calls_for_the_same_workload(self):
        legacy = self.event()
        record(self.work, legacy)
        with self.work._db() as db:
            self.assertEqual(1, db.execute('select version from performance_meta').fetchone()[0])
        turn = self.event('turn-1', measurement_scope='agent_turn', duration_ms=60000,
            accepted=False, usage={'kind': 'per_turn', 'input_tokens': None,
                'output_tokens': None, 'cached_input_tokens': None, 'reasoning_tokens': None},
            cost=None)
        record(self.work, turn)
        result = report(self.work).data
        groups = {g['measurement_scope']: g for g in result['groups']}
        self.assertEqual({'model_call', 'agent_turn'}, set(groups))
        self.assertEqual(10, groups['model_call']['duration_ms']['p50'])
        self.assertEqual(60000, groups['agent_turn']['duration_ms']['p50'])
        self.assertIsNone(groups['agent_turn']['known_tokens']['input_tokens'])
        self.assertEqual(0, groups['agent_turn']['accepted_observations'])
        self.assertTrue(record(self.work, legacy).data['reused'])
        with self.work._db() as db:
            self.assertEqual(2, db.execute('select version from performance_meta').fetchone()[0])
        self.assertIn('agent_turn', render(result, 'md'))
        self.assertIn('measurement_scope', render(result, 'csv').splitlines()[0])
        self.assertNotIn('missing calls', render(result, 'md'))

    def test_invalid_scope_or_mismatched_usage_unit_is_rejected_before_storage(self):
        for scope, kind in [('agent_turn', 'per_call'), ('model_call', 'per_turn'),
                            ('campaign', 'per_turn'), (None, 'per_call')]:
            event = self.event(measurement_scope=scope)
            event['usage']['kind'] = kind
            with self.assertRaises(ValueError): record(self.work, event)
        with self.work._db() as db:
            self.assertIsNone(db.execute("select name from sqlite_master where name='performance_observations'").fetchone())

    def test_real_cli_imports_host_turn_with_unknown_tokens(self):
        event = self.event('host-turn', measurement_scope='agent_turn', accepted=False,
            duration_ms=12500, usage={'kind': 'per_turn', 'input_tokens': None,
                'output_tokens': None, 'cached_input_tokens': None, 'reasoning_tokens': None}, cost=None)
        event_path = self.work.data_dir / 'turn.json'
        event_path.write_text(json.dumps(event), encoding='utf8')
        cli = Path(__file__).resolve().parents[1] / 'scripts/kit.py'
        args = [sys.executable, str(cli), '--data-dir', str(self.work.data_dir)]
        imported = subprocess.run(args+['performance-record', '--file', str(event_path)], capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, imported.returncode, imported.stdout+imported.stderr)
        group = report(self.work).data['groups'][0]
        self.assertEqual('agent_turn', group['measurement_scope'])
        self.assertEqual({'known': 0, 'missing': 1}, group['token_coverage']['output_tokens'])

    def test_reimport_is_idempotent_and_a_changed_event_or_source_is_blocked(self):
        event = self.event()
        record(self.work, event)
        self.assertTrue(record(self.work, event).data['reused'])
        with self.assertRaises(WorkflowError): record(self.work, {**event, 'duration_ms': 11})
        self.proof.write_text('{"changed":true}', encoding='utf8')
        with self.assertRaises(WorkflowError): record(self.work, event)
        self.assertEqual(1, report(self.work).data['record_count'])
        with self.work._db() as db:
            self.assertEqual(6, db.execute('pragma user_version').fetchone()[0])
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('delete from performance_observations')

    def test_invalid_telemetry_has_no_feature_table_side_effect(self):
        invalid = [self.event(duration_ms=-1), self.event(duration_ms=float('nan')),
                   self.event(status='failed'), self.event(extra='unexpected')]
        for key, value in [('input_tokens', True), ('cached_input_tokens', 101), ('reasoning_tokens', 21), ('kind', 'cumulative')]:
            event = self.event(); event['usage'][key] = value; invalid.append(event)
        for event in invalid:
            with self.assertRaises(ValueError): record(self.work, event)
        with self.work._db() as db:
            self.assertIsNone(db.execute("select name from sqlite_master where name='performance_observations'").fetchone())

    def test_cross_workspace_proof_and_future_feature_version_are_blocked(self):
        other = Executor(Path(self.tmp.name) / 'other'); other.init()
        self.assertEqual(0, report(other).data['record_count'])
        event = self.event(); event['source']['path'] = str(self.proof)
        with self.assertRaises(ValueError): record(other, event)
        record(self.work, self.event())
        self.assertEqual(0, report(other).data['record_count'])
        with self.work._db() as db: db.execute('update performance_meta set version=99')
        with self.assertRaises(WorkflowError): report(self.work)
        with self.assertRaises(WorkflowError): record(self.work, self.event('call-2'))

    def test_real_cli_and_exports_cannot_replace_evidence_or_ledger(self):
        event_path = self.work.data_dir / 'observation.json'
        event_path.write_text(json.dumps(self.event()), encoding='utf8')
        cli = Path(__file__).resolve().parents[1] / 'scripts/kit.py'
        args = [sys.executable, str(cli), '--data-dir', str(self.work.data_dir)]
        imported = subprocess.run(args+['performance-record', '--file', str(event_path)], capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, imported.returncode, imported.stdout+imported.stderr)
        rendered = subprocess.run(args+['performance-report', '--format', 'md', '--output', 'reports/performance/run-1.md'], capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, rendered.returncode, rendered.stdout+rendered.stderr)
        self.assertIn('example/model-a', (self.work.data_dir/'reports/performance/run-1.md').read_text(encoding='utf8'))
        with self.assertRaises(FileExistsError): export(self.work, 'reports/performance/run-1.md', 'md')
        for path in ('workflow.sqlite3', 'usage-export.json', '../escape.json'):
            with self.assertRaises(WorkflowError): export(self.work, path, 'json')
        csv = export(self.work, 'reports/performance/run-1.csv', 'csv')
        self.assertEqual(1, csv.data['record_count'])
