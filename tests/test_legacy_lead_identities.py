import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.contracts import ContractError
from core.workflow import Preparation, WorkflowError

ROOT = Path(__file__).resolve().parents[1]


class LegacyLeadIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = self.root / 'older campaign #1.sqlite3'
        with closing(sqlite3.connect(self.ledger)) as db:
            db.executescript('''
                CREATE TABLE jobs(id INTEGER PRIMARY KEY, platform, platform_job_id,
                    employer, employer_key, req_id, title, city_raw, city_norm,
                    url, state, liveness);
                CREATE TABLE submissions(id INTEGER PRIMARY KEY, private_snapshot);
                INSERT INTO submissions VALUES(1, 'fictional snapshot must stay untouched');
                INSERT INTO jobs VALUES(7,'fictional','p7','Example Software',
                    'example software','req7','AI Developer','HCMC','old city key',
                    'https://jobs.example.test/7','submission_uncertain','closed');
            ''')
        self.lead = dict(id='incoming', platform='fictional', platform_job_id='p7',
            employer='Example Software', req_id='req7', title='AI Developer',
            city='Ho Chi Minh City', url='https://jobs.example.test/7')
        self.packet = {'schema_version': '1.0', 'leads': [self.lead]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_legacy_metadata_uses_all_signals_without_history_or_migration(self):
        before = self.ledger.read_bytes()
        result = Preparation.check_legacy_lead_identities(self.packet, self.ledger).data
        candidate = result['leads'][0]['candidates'][0]
        self.assertEqual(7, candidate['id'])
        self.assertEqual('HCMC', candidate['city'])
        self.assertEqual(['same_platform_job_id', 'same_employer_requisition',
            'same_url', 'same_employer_title_city'], candidate['signals'])
        self.assertTrue(candidate['prior_attempt_needs_reconciliation'])
        self.assertFalse(result['deduplication_complete'])
        self.assertFalse(result['external_history_checked'])
        self.assertEqual(0, result['job_records_added'])
        self.assertEqual(before, self.ledger.read_bytes())

    def test_one_read_only_snapshot_for_fifty_partial_leads(self):
        packet = {'schema_version': '1.0', 'leads': [dict(self.lead, id=str(i),
            employer='', platform='', platform_job_id='', req_id='') for i in range(50)]}
        original = copy.deepcopy(packet)
        queries = []
        connect = sqlite3.connect
        def observed(database_uri, **kwargs):
            self.assertTrue(database_uri.endswith('?mode=ro'))
            self.assertTrue(kwargs['uri'])
            db = connect(database_uri, **kwargs)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("INSERT INTO submissions VALUES(2, 'must fail')")
            db.rollback()
            db.set_trace_callback(queries.append)
            return db
        with patch('core.workflow.sqlite3.connect', side_effect=observed) as calls:
            result = Preparation.check_legacy_lead_identities(packet, self.ledger).data
        self.assertEqual(1, calls.call_count)
        self.assertEqual(1, sum(q.startswith('SELECT ') for q in queries))
        self.assertTrue(all('FROM jobs' in q for q in queries if q.startswith('SELECT ')))
        self.assertEqual(50, result['matched_leads'])
        self.assertEqual(original, packet)

    def test_invalid_batch_fails_before_connect_and_missing_file_is_not_created(self):
        invalid = dict(self.packet, leads=[self.lead, self.lead])
        with patch('core.workflow.sqlite3.connect', side_effect=AssertionError('No DB read')):
            with self.assertRaises(ContractError):
                Preparation.check_legacy_lead_identities(invalid, self.ledger)
        missing = self.root / 'missing' / 'applications.sqlite3'
        with self.assertRaises(WorkflowError):
            Preparation.check_legacy_lead_identities(self.packet, missing)
        self.assertFalse(missing.parent.exists())

    def test_explicit_ledger_does_not_read_adjacent_database(self):
        other = self.root / 'workflow.sqlite3'
        with closing(sqlite3.connect(other)) as db:
            db.execute('CREATE TABLE unrelated(secret)')
        result = Preparation.check_legacy_lead_identities(self.packet, self.ledger).data
        self.assertEqual(7, result['leads'][0]['candidates'][0]['id'])
        with self.assertRaises(sqlite3.OperationalError):
            Preparation.check_legacy_lead_identities(self.packet, other)

    def test_cli_needs_no_portable_workspace_and_reports_schema_failure(self):
        packet = self.root / 'leads.json'
        packet.write_text(json.dumps(self.packet), encoding='utf8')
        for ledger, outcome, code in [(self.ledger, 'ok', 0),
                (self.root / 'missing.sqlite3', 'needs_input', 2), (packet, 'failed', 2)]:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/kit.py'),
                'check-legacy-lead-identities', '--ledger', str(ledger), '--file', str(packet)],
                cwd=self.root, capture_output=True, encoding='utf8', timeout=20)
            self.assertEqual(code, result.returncode, result.stdout+result.stderr)
            self.assertEqual(outcome, json.loads(result.stdout)['outcome'])
        self.assertEqual({'older campaign #1.sqlite3', 'leads.json'},
                         {f.name for f in self.root.iterdir()})

    def test_network_or_uri_ledger_is_not_implicitly_opened(self):
        for value in ('file:campaign.sqlite3?mode=rw', 'https://example.test/db',
                      '//example.test/share/db', '\\\\example.test\\share\\db', ''):
            with self.subTest(value=value), patch('core.workflow.sqlite3.connect',
                    side_effect=AssertionError('No network/URI DB access')):
                with self.assertRaises((ContractError, WorkflowError, ValueError)):
                    Preparation.check_legacy_lead_identities(self.packet, value)

    def test_cli_rejects_two_workspace_selections_without_creating_either(self):
        packet = self.root / 'leads.json'
        packet.write_text(json.dumps(self.packet), encoding='utf8')
        before = self.ledger.read_bytes()
        other = self.root / 'new portable workspace'
        result = subprocess.run([sys.executable, str(ROOT/'scripts/kit.py'),
            '--data-dir', str(other), 'check-legacy-lead-identities', '--ledger',
            str(self.ledger), '--file', str(packet)], cwd=self.root,
            capture_output=True, encoding='utf8', timeout=20)
        self.assertEqual(2, result.returncode)
        self.assertEqual('needs_input', json.loads(result.stdout)['outcome'])
        self.assertFalse(other.exists())
        self.assertEqual(before, self.ledger.read_bytes())

    def test_resolved_network_target_fails_before_file_probe(self):
        with patch.object(Path, 'resolve', return_value=Path('//example.test/share/db')), \
                patch.object(Path, 'is_file', side_effect=AssertionError('No network probe')):
            with self.assertRaises(ContractError):
                Preparation.check_legacy_lead_identities(self.packet, 'local-link.sqlite3')
