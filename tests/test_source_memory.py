"""Read-only legacy source packets never initialize or modify an application ledger."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

from core.source_memory import source_context


class SourceMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'data').mkdir()
        self.source = self.root/'project.txt'
        self.source.write_text('Fictional AI-assisted lexical API project.', encoding='utf8')
        self.fact = {'fact_id': 'F1', 'exact_claim': 'Fictional AI-assisted LLM API project; lexical retrieval.',
                     'approval_state': 'approved_fact_only_not_disclosure', 'conflict': None,
                     'source_path': str(self.source), 'locator': 'line 1',
                     'source_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest()}
        self.write([self.fact])

    def write(self, facts):
        (self.root/'data/source-facts.json').write_text(json.dumps(facts), encoding='utf8')

    def test_citations_and_no_persistent_writes(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = source_context(self.root, 'LLM API').data
        self.assertEqual(['F1'], [f['id'] for f in result['facts']])
        self.assertFalse(result['authority_granted'])
        self.assertEqual(0, result['model_api_calls'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_stale_or_escaping_sources_fail_closed(self):
        self.source.write_text('changed', encoding='utf8')
        with self.assertRaises((ValueError, OSError)): source_context(self.root, 'API')
        self.fact['source_path'] = str(self.root.parent/'outside.txt')
        self.write([self.fact])
        with self.assertRaises((ValueError, OSError)): source_context(self.root, 'API')

    def test_pending_conflicts_and_unhashed_facts_are_excluded(self):
        pending = dict(self.fact, fact_id='F2', approval_state='pending')
        conflict = dict(self.fact, fact_id='F3', conflict='unresolved')
        unhashed = dict(self.fact, fact_id='F4'); unhashed.pop('source_sha256')
        self.write([self.fact, pending, conflict, unhashed])
        data = source_context(self.root, 'API').data
        self.assertEqual(3, data['excluded_fact_count'])
        self.assertEqual(['F1'], [f['id'] for f in data['facts']])

    def test_literal_query_whole_fact_budget_and_duplicate_identity(self):
        self.assertEqual([], source_context(self.root, 'API', max_chars=1).data['facts'])
        self.assertEqual('F1', source_context(self.root, 'API" OR * --').data['facts'][0]['id'])
        self.write([self.fact, self.fact])
        with self.assertRaises(ValueError): source_context(self.root, 'API')
        self.write([self.fact])
        for query in ('', 'x'*1001):
            with self.assertRaises(ValueError): source_context(self.root, query)
        for limit in (True, 0, 11):
            with self.assertRaises(ValueError): source_context(self.root, 'API', limit=limit)

    def test_cli_needs_no_initialized_database_and_missing_workspace_stays_missing(self):
        script = Path(__file__).resolve().parents[1]/'scripts/source_memory.py'
        result = subprocess.run([sys.executable, str(script), '--data-dir', str(self.root),
                                 '--query', 'LLM'], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('F1', json.loads(result.stdout)['data']['facts'][0]['id'])
        missing = self.root/'absent'
        result = subprocess.run([sys.executable, str(script), '--data-dir', str(missing),
                                 '--query', 'LLM'], capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual('needs_input', json.loads(result.stdout)['outcome'])
        self.assertFalse(missing.exists())

    def test_existing_outside_source_and_malformed_or_oversized_corpus(self):
        with tempfile.TemporaryDirectory() as outside:
            other = Path(outside)/'evidence.txt'; other.write_bytes(self.source.read_bytes())
            self.write([dict(self.fact, source_path=str(other))])
            with self.assertRaises(ValueError): source_context(self.root, 'API')
        for packet in ({'facts': []}, [self.fact]*2001, ['not a fact'],
                       [dict(self.fact, exact_claim='x'*20001)]):
            self.write(packet)
            with self.assertRaises(ValueError): source_context(self.root, 'API')
        (self.root/'data/source-facts.json').write_text(' '*2000001, encoding='utf8')
        with self.assertRaises(ValueError): source_context(self.root, 'API')
