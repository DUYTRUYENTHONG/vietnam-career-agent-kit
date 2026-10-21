"""Fictional rolling KPI arithmetic and the real engine's frozen fit provenance."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_execution as fixtures
from core.contracts import ContractError
from core.ledger import canonical_hash
from core.tracking import throughput
from core.workflow import WorkflowError


class LedgerDouble:
    def __init__(self, rows):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA user_version=3')
        self.db.execute('CREATE TABLE execution_submissions(job_id,recorded_utc,snapshot_json,snapshot_sha256)')
        for job_id,stamp,fit in rows:
            snapshot={} if fit is None else {'fit_classification':fit}
            self.db.execute('INSERT INTO execution_submissions VALUES(?,?,?,?)',
                            (job_id,stamp,json.dumps(snapshot),canonical_hash(snapshot)))
        self.db.commit()

    @contextmanager
    def _db(self):
        try:yield self.db
        finally:self.db.rollback()


class ThroughputTests(unittest.TestCase):
    now=datetime(2026,1,1,12,tzinfo=timezone.utc)

    def measure(self, rows, target=100, minutes=60):
        work=LedgerDouble(rows)
        self.addCleanup(work.db.close)
        with patch('core.tracking.utc_now',return_value=self.now.isoformat()):
            return throughput(work,target,minutes).data

    def test_only_windowed_confirmations_with_frozen_qualifying_fit_count(self):
        now=self.now
        rows=[(1,now.isoformat(),'Strong fit'),
              (2,(now-timedelta(minutes=59)).isoformat(),'Plausible fit'),
              (3,(now-timedelta(minutes=60)).isoformat(),'Strong fit'),
              (4,(now+timedelta(seconds=1)).isoformat(),'Strong fit'),
              (5,now.isoformat(),None),(6,now.isoformat(),'Stretch')]
        data=self.measure(rows,target=3)
        self.assertEqual(2,data['qualifying_confirmations'])
        self.assertEqual(1,data['fit_unrecorded_confirmations'])
        self.assertEqual(1,data['other_fit_confirmations'])
        self.assertFalse(data['target_met'])
        self.assertEqual(1,data['remaining'])
        self.assertEqual(2,data['observed_per_hour'])

    def test_kpi_requires_100_distinct_confirmed_rows_not_extrapolation(self):
        rows=[(n,self.now.isoformat(),'Strong fit') for n in range(100)]
        self.assertTrue(self.measure(rows)['target_met'])
        self.assertFalse(self.measure(rows[:99])['target_met'])
        self.assertEqual(0,self.measure([])['observed_per_hour'])
        data=self.measure(rows[:50],target=100,minutes=30)
        self.assertEqual(100,data['observed_per_hour'])
        self.assertFalse(data['target_met'])

    def test_timezone_offsets_are_normalized_and_ambiguous_timestamps_block(self):
        self.assertEqual(1,self.measure([(1,'2026-01-01T19:00:00+07:00','Strong fit')])['qualifying_confirmations'])
        for stamp in ['2026-01-01T12:00:00','invalid']:
            with self.assertRaises(WorkflowError):self.measure([(1,stamp,'Strong fit')])

    def test_duplicate_rows_bad_hash_and_invalid_parameters_block(self):
        row=(1,self.now.isoformat(),'Strong fit')
        with self.assertRaises(WorkflowError):self.measure([row,row])
        work=LedgerDouble([row]);self.addCleanup(work.db.close)
        work.db.execute("UPDATE execution_submissions SET snapshot_sha256='invalid'");work.db.commit()
        with patch('core.tracking.utc_now',return_value=self.now.isoformat()):
            with self.assertRaises(WorkflowError):throughput(work,100)
        for target,minutes in [(True,60),(0,60),(100,0),(100,True),(100,1441)]:
            with self.assertRaises(ContractError):self.measure([],target,minutes)

    def test_older_pre_execution_schema_returns_needs_input(self):
        work=LedgerDouble([]);self.addCleanup(work.db.close)
        work.db.execute('PRAGMA user_version=2')
        with self.assertRaises(WorkflowError) as error:
            throughput(work,100)
        self.assertEqual('needs_input',error.exception.outcome)


class ThroughputEngineTests(unittest.TestCase):
    setUp=fixtures.ExecutionTests.setUp
    tearDown=fixtures.ExecutionTests.tearDown
    plan=fixtures.ExecutionTests.plan
    approve=fixtures.ExecutionTests.approve
    start=fixtures.ExecutionTests.start
    receipt=fixtures.ExecutionTests.receipt
    step=fixtures.ExecutionTests.step
    until_submit=fixtures.ExecutionTests.until_submit

    def test_attempt_and_prepared_form_do_not_count_and_confirmation_keeps_fit(self):
        run=self.start()
        self.until_submit(run)
        self.assertEqual(0,self.work.throughput(100).data['qualifying_confirmations'])
        verify=self.work.next_action(run).data['request']
        self.work.record_action(run,self.receipt(verify))
        data=self.work.throughput(100).data
        self.assertEqual(1,data['qualifying_confirmations'])
        self.assertFalse(data['target_met'])
        self.assertEqual(99,data['remaining'])
        with patch.object(self.work,'hash_file',side_effect=AssertionError('KPI must not reread files')):
            self.work.throughput(100)
        cli=Path(__file__).resolve().parents[1]/'scripts/kit.py'
        result=subprocess.run([sys.executable,str(cli),'--data-dir',str(self.root),
                               'throughput','--target','100','--window-minutes','60'],
                              capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        data=json.loads(result.stdout)['data']
        self.assertEqual(1,data['qualifying_confirmations'])
        self.assertEqual(99,data['remaining'])
        self.assertFalse(data['target_met'])
