"""Retrieval is local, confirmed, bounded, current and candidate-specific."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import json
import subprocess
import sys

from core.career_memory import retrieve, email_context, evaluate
from core.execution import Executor
from core.workflow import WorkflowError
from scripts.demo_slice1 import demo


class CareerMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        demo(self.base/'private')
        self.work = Executor(self.base/'private')

    def test_confirmed_quotes_are_cited_and_pending_python_is_not_promoted(self):
        result = retrieve(self.work, 'SQL', limit=1)
        self.assertEqual('ok', result.outcome)
        self.assertEqual(1, len(result.data['facts']))
        fact = result.data['facts'][0]
        self.assertIn('SQL', fact['quote'])
        self.assertEqual(64, len(fact['source_sha256']))
        self.assertFalse(result.data['generation_performed'])
        self.assertIn('host_tokens', result.data['performance']['unavailable'])
        self.assertEqual([], retrieve(self.work, 'Python').data['facts'])

    def test_budget_preserves_whole_qualifiers_and_query_cannot_execute_sql(self):
        self.assertEqual([], retrieve(self.work, 'SQL', max_chars=1).data['facts'])
        result = retrieve(self.work, 'SQL"; DROP TABLE candidate_profile; --')
        self.assertEqual('ok', result.outcome)
        self.assertTrue(self.work.confirmed_profile())
        for query, options in [('', {}), ('SQL', {'limit': True}), ('SQL', {'max_chars': 0})]:
            with self.assertRaises(ValueError): retrieve(self.work, query, **options)

    def test_other_candidate_and_tampered_sources_cannot_reuse_a_context(self):
        retrieve(self.work, 'SQL')
        other = Executor(self.base/'other'); other.init()
        with self.assertRaises(WorkflowError): retrieve(other, 'SQL')
        source = self.work.confirmed_profile()['sources'][0]
        self.work.inside(source['path']).write_text('Changed fictional evidence', encoding='utf8')
        with self.assertRaises(WorkflowError): retrieve(self.work, 'SQL')

    def test_professional_email_context_is_preparation_without_sending(self):
        result = email_context(self.work, 1, language='vi')
        self.assertEqual('ok', result.outcome)
        self.assertTrue(result.data['review_required'])
        self.assertFalse(result.data['sent'])
        self.assertFalse(result.data['authority_granted'])
        self.assertIn('Vietnamese', result.data['instructions'])
        with self.assertRaises(ValueError): email_context(self.work, 1, language='unknown')

    def test_gold_retrieval_metrics_separate_negatives_and_reject_unknown_ids(self):
        fact_id = retrieve(self.work, 'SQL', limit=1).data['facts'][0]['id']
        packet = {'schema_version': '1.0', 'limit': 1, 'cases': [
            {'id': 'sql-positive', 'query': 'SQL', 'expected_fact_ids': [fact_id]},
            {'id': 'python-negative', 'query': 'Python', 'expected_fact_ids': []}]}
        result = evaluate(self.work, packet).data
        self.assertEqual(1, result['positive_query_count'])
        self.assertEqual(1, result['negative_query_count'])
        self.assertEqual(1, result['positive_metrics']['recall_at_k'])
        self.assertEqual(1, result['positive_metrics']['reciprocal_rank'])
        self.assertEqual(0, result['negative_false_positives'])
        self.assertEqual(1, result['baseline']['positive_metrics']['recall_at_k'])
        packet['cases'][0]['expected_fact_ids'] = ['not-an-existing-fact']
        with self.assertRaises(ValueError): evaluate(self.work, packet)

    def test_missing_fts5_and_future_workspace_have_explicit_handoffs(self):
        connection = MagicMock()
        connection.execute.side_effect = sqlite3.OperationalError('no such module: fts5')
        original = sqlite3.connect
        def connect(path, *args, **kwargs):
            return connection if path == ':memory:' else original(path, *args, **kwargs)
        with patch('core.career_memory.sqlite3.connect', side_effect=connect):
            self.assertEqual('manual_required', retrieve(self.work, 'SQL').outcome)
        connection.close.assert_called_once()
        with self.work._db() as db: db.execute('pragma user_version=99')
        with self.assertRaises(WorkflowError): retrieve(self.work, 'SQL')

    def test_multilingual_volume_benchmark_uses_actual_profile_and_source_checks(self):
        from scripts.benchmark_memory import benchmark
        result = benchmark(100, 2)
        self.assertEqual(0, result['provider_calls'])
        self.assertIsNone(result['model_tokens'])
        self.assertEqual(1, result['evaluation']['positive_metrics']['recall_at_k'])
        self.assertLess(result['evaluation']['baseline']['positive_metrics']['recall_at_k'], 1)

    def test_cli_context_and_evaluation_use_selected_private_workspace(self):
        cli = Path(__file__).resolve().parents[1]/'scripts/kit.py'
        args = [sys.executable, str(cli), '--data-dir', str(self.work.data_dir)]
        result = subprocess.run(args+['career-context', '--query', 'SQL', '--limit', '1'],
                                capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, result.returncode, result.stdout+result.stderr)
        fact_id = json.loads(result.stdout)['data']['facts'][0]['id']
        packet = {'schema_version': '1.0', 'limit': 1,
                  'cases': [{'id': 'sql', 'query': 'SQL', 'expected_fact_ids': [fact_id]}]}
        self.work.atomic_text('gold.json', json.dumps(packet))
        result = subprocess.run(args+['career-evaluate', '--file', str(self.work.inside('gold.json'))],
                                capture_output=True, encoding='utf8', timeout=15)
        self.assertEqual(0, result.returncode, result.stdout+result.stderr)
