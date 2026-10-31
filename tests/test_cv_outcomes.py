"""Fictional source-bound feedback never becomes submission or model authority."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

import test_execution as fixtures
from core import cv_outcomes
from core.ledger import canonical_hash, utc_now
from core.workflow import WorkflowError


class CVOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ExecutionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        run = self.fixture.start()
        self.fixture.until_submit(run)
        self.fixture.step(run)  # read-only verification, not another submit
        self.work = self.fixture.work
        with self.work._db() as db:
            self.sub = dict(db.execute('SELECT * FROM execution_submissions').fetchone())
        self.snapshot = json.loads(self.sub['snapshot_json'])
        self.proof = self.work.data_dir/'employer-message.txt'
        self.proof.write_text('Fictional employer invited the applicant to an interview.',encoding='utf8')

    def event(self, event_id='reply-1', kind='interview_invited', **changes):
        value = {'schema_version':'1.0','event_id':event_id,'job_id':1,
            'submission_id':self.sub['id'],'submission_sha256':self.sub['snapshot_sha256'],
            'document_sha256':self.snapshot['document']['sha256'],'kind':kind,
            'received_utc':utc_now(),'observed_utc':utc_now(),'retracts_event_id':None,
            'source':{'kind':'employer_message','path':'employer-message.txt',
                      'sha256':hashlib.sha256(self.proof.read_bytes()).hexdigest()}}
        return {**value,**changes}

    def seed_confirmation(self, job_id, document_sha256):
        """Extra frozen fictional rows test aggregation, not another live execution."""
        with self.work._db() as db:
            job=dict(db.execute('SELECT * FROM jobs WHERE id=1').fetchone())
            job.update(id=job_id,platform_job_id='FICT-'+str(job_id),req_id='FICT-'+str(job_id))
            db.execute('INSERT INTO jobs ('+','.join(job)+') VALUES ('+','.join('?' for _ in job)+')',tuple(job.values()))
            attempt=dict(db.execute('SELECT * FROM execution_attempts LIMIT 1').fetchone())
            payload=json.loads(attempt['snapshot_json']);payload['entry']['job_id']=job_id
            payload['document']['sha256']=payload['entry']['document_sha256']=document_sha256
            attempt.update(id='fictional-attempt-'+str(job_id),job_id=job_id,snapshot_json=json.dumps(payload),snapshot_sha256=canonical_hash(payload))
            db.execute('INSERT INTO execution_attempts ('+','.join(attempt)+') VALUES ('+','.join('?' for _ in attempt)+')',tuple(attempt.values()))
            sub=dict(self.sub);frozen=json.loads(sub['snapshot_json'])
            frozen['entry']['job_id']=job_id;frozen['document']['sha256']=frozen['entry']['document_sha256']=document_sha256
            sub.update(id='fictional-confirmation-'+str(job_id),job_id=job_id,attempt_id=attempt['id'],snapshot_json=json.dumps(frozen),snapshot_sha256=canonical_hash(frozen))
            db.execute('INSERT INTO execution_submissions ('+','.join(sub)+') VALUES ('+','.join('?' for _ in sub)+')',tuple(sub.values()))
        return sub

    def test_confirmed_hash_binding_and_idempotency_do_not_change_submission(self):
        event = self.event()
        result = cv_outcomes.record(self.work,event)
        self.assertFalse(result.data['reused'])
        self.assertTrue(cv_outcomes.record(self.work,event).data['reused'])
        with self.assertRaises(WorkflowError):
            cv_outcomes.record(self.work,{**event,'kind':'rejected'})
        with self.work._db() as db:
            self.assertEqual(1,db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0])
            self.assertEqual(self.sub['snapshot_sha256'],db.execute('SELECT snapshot_sha256 FROM execution_submissions').fetchone()[0])
            self.assertEqual(6,db.execute('PRAGMA user_version').fetchone()[0])
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM cv_outcome_events')

    def test_acknowledgment_is_not_a_positive_screening_and_recent_cohort_is_separate(self):
        cv_outcomes.record(self.work,self.event(kind='acknowledged'))
        recent=cv_outcomes.report(self.work).data
        self.assertEqual(1,recent['recent_submissions'])
        group=cv_outcomes.report(self.work,min_age_days=0).data['cv_groups'][0]
        self.assertEqual(1,group['eligible_applications'])
        self.assertEqual(1,group['outcome_counts']['acknowledged'])
        self.assertEqual(0,group['outcome_counts']['screening_passed'])
        self.assertEqual(0,group['outcome_counts']['interview_invited'])

    def test_two_interview_messages_count_one_application_and_no_inferred_prior_stage(self):
        cv_outcomes.record(self.work,self.event())
        cv_outcomes.record(self.work,self.event('reply-2'))
        group=cv_outcomes.report(self.work,min_age_days=0).data['cv_groups'][0]
        self.assertEqual(1,group['outcome_counts']['interview_invited'])
        self.assertEqual(0,group['outcome_counts']['shortlisted'])
        self.assertEqual(1.0,group['outcome_rates']['interview_invited'])

    def test_cohort_denominators_group_exact_cv_and_do_not_rank_models(self):
        self.seed_confirmation(2,self.snapshot['document']['sha256'])
        other=self.seed_confirmation(3,'f'*64)
        cv_outcomes.record(self.work,self.event())
        report=cv_outcomes.report(self.work,min_age_days=0).data
        self.assertEqual(3,report['eligible_submissions'])
        self.assertEqual(self.sub['snapshot_sha256'],report['applications'][0]['submission_sha256'])
        groups={g['document_sha256']:g for g in report['cv_groups']}
        self.assertEqual(2,groups[self.snapshot['document']['sha256']]['eligible_applications'])
        self.assertEqual(.5,groups[self.snapshot['document']['sha256']]['outcome_rates']['interview_invited'])
        self.assertEqual(1,groups['f'*64]['no_recorded_response'])
        self.assertNotIn('winner',report)
        with self.assertRaises(ValueError):
            cv_outcomes.record(self.work,self.event('cross-retract','retract',job_id=3,
                submission_id=other['id'],submission_sha256=other['snapshot_sha256'],
                document_sha256='f'*64,retracts_event_id='reply-1'))

    def test_unsupported_feature_and_legacy_schema_never_reset_or_initialize(self):
        cv_outcomes.record(self.work,self.event())
        with self.work._db() as db:db.execute('UPDATE cv_outcome_meta SET version=99')
        with self.assertRaises(WorkflowError):cv_outcomes.report(self.work)
        with self.assertRaises(WorkflowError):cv_outcomes.record(self.work,self.event('reply-2'))
        with self.work._db() as db:
            self.assertEqual(1,db.execute('SELECT count(*) FROM cv_outcome_events').fetchone()[0])
            db.execute('PRAGMA user_version=0')
        with self.assertRaises(WorkflowError):cv_outcomes.report(self.work)
        with self.work._db() as db:self.assertEqual(0,db.execute('PRAGMA user_version').fetchone()[0])

    def test_retraction_corrects_one_same_application_event_without_rewriting(self):
        event=self.event();cv_outcomes.record(self.work,event)
        cv_outcomes.record(self.work,self.event('correction-1','retract',retracts_event_id='reply-1'))
        group=cv_outcomes.report(self.work,min_age_days=0).data['cv_groups'][0]
        self.assertEqual(0,group['outcome_counts']['interview_invited'])
        self.assertEqual(1,group['no_recorded_response'])
        self.assertEqual(2,cv_outcomes.report(self.work,min_age_days=0).data['event_count'])
        with self.assertRaises(ValueError):
            cv_outcomes.record(self.work,self.event('correction-2','retract',retracts_event_id='correction-1'))

    def test_wrong_job_snapshot_cv_or_unknown_fields_are_rejected_before_import(self):
        for change in [{'job_id':99},{'submission_id':'missing'},{'submission_sha256':'0'*64},
                       {'document_sha256':'0'*64},{'kind':'no_response'},{'extra':'bad'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                cv_outcomes.record(self.work,self.event(**change))
        with self.work._db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='cv_outcome_events'").fetchone())

    def test_future_or_pre_attempt_times_and_outside_or_oversized_proof_are_rejected(self):
        future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        bad=[self.event(observed_utc=future),self.event(received_utc='2000-01-01T00:00:00Z'),
             self.event(observed_utc='2020-01-01T00:00:00'),self.event(retracts_event_id='missing')]
        outside=self.event();outside['source']['path']='../outside.txt';bad.append(outside)
        for event in bad:
            with self.assertRaises(ValueError):cv_outcomes.record(self.work,event)
        self.proof.write_bytes(b'x'*262145)
        with self.assertRaises(ValueError):cv_outcomes.record(self.work,self.event())

    def test_accepted_timestamps_cannot_make_an_unreportable_large_event(self):
        event=self.event()
        for key in ('received_utc','observed_utc'):
            event[key]=event[key][:-6]+'0'*20_000+'+00:00'
        with self.assertRaises(ValueError):cv_outcomes.record(self.work,event)
        event=self.event();event['source']['path']='😀'*4096
        with self.assertRaises(ValueError):cv_outcomes.record(self.work,event)
        with self.work._db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='cv_outcome_events'").fetchone())

    def test_missing_changed_source_is_unverified_not_rejection_and_asof_has_no_hindsight(self):
        event=self.event();cv_outcomes.record(self.work,event)
        before=cv_outcomes.report(self.work,min_age_days=0,as_of=self.sub['recorded_utc']).data
        self.assertEqual(0,before['event_count'])
        self.proof.write_text('changed',encoding='utf8')
        current=cv_outcomes.report(self.work,min_age_days=0).data
        self.assertEqual(1,current['unverified_events'])
        self.assertEqual(0,current['cv_groups'][0]['outcome_counts']['interview_invited'])
        self.assertEqual(0,current['cv_groups'][0]['outcome_counts']['rejected'])

    def test_historical_cv_identity_survives_current_file_change_and_filters_are_explicit(self):
        cv_outcomes.record(self.work,self.event())
        self.work.inside(self.snapshot['document']['path']).write_bytes(b'current draft changed')
        group=cv_outcomes.report(self.work,min_age_days=0,job_ids=[1]).data['cv_groups'][0]
        self.assertEqual(self.snapshot['document']['sha256'],group['document_sha256'])
        self.assertEqual([],cv_outcomes.report(self.work,min_age_days=0,job_ids=[99]).data['cv_groups'])
        for kwargs in [{'min_age_days':True},{'min_age_days':-1},{'job_ids':[True]},{'job_ids':[1,1]}]:
            with self.assertRaises(ValueError):cv_outcomes.report(self.work,**kwargs)

    def test_real_cli_record_report_and_malformed_request_are_explicit(self):
        packet=self.work.data_dir/'reply.json';packet.write_text(json.dumps(self.event()),encoding='utf8')
        cli=Path(__file__).resolve().parents[1]/'scripts/kit.py'
        args=[sys.executable,str(cli),'--data-dir',str(self.work.data_dir)]
        recorded=subprocess.run(args+['outcome-record','--file',str(packet)],capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(0,recorded.returncode,recorded.stdout+recorded.stderr)
        result=subprocess.run(args+['outcome-report','--min-age-days','0','--job-id','1'],capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertEqual(1,json.loads(result.stdout)['data']['eligible_submissions'])
        packet.write_text('{"unexpected":true}',encoding='utf8')
        invalid=subprocess.run(args+['outcome-record','--file',str(packet)],capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(2,invalid.returncode,invalid.stdout+invalid.stderr)
        self.assertEqual('needs_input',json.loads(invalid.stdout)['outcome'])
        with self.work._db() as db:
            self.assertEqual(1,db.execute('SELECT count(*) FROM cv_outcome_events').fetchone()[0])
