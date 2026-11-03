import copy
import json
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.contracts import ContractError
from core.workflow import Preparation, WorkflowError

ROOT = Path(__file__).resolve().parents[1]


class LeadIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.work = Preparation(self.base/'private', ROOT)
        self.work.init()
        self.job = self.work.add_job(platform='fictional', platform_job_id='post-1',
            employer='Example Software', req_id='req-1', title='AI Developer', city='HCMC',
            url='https://jobs.example.test/post-1', raw_jd='Fictional role only.')
        self.lead = {key:self.job[key] for key in
                     ('platform','platform_job_id','employer','req_id','title','city','url')}
        self.lead['id'] = 'lead-1'

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, *leads):
        return {'schema_version':'1.0','leads':list(leads or (self.lead,))}

    def test_reports_all_recorded_signals_without_import_or_artifact_access(self):
        with self.work._db() as db:
            db.execute("UPDATE jobs SET state='submission_uncertain',liveness='closed' WHERE id=?", (self.job['id'],))
        before = self.work.db_path.read_bytes()
        with patch.object(self.work, 'hash_file', side_effect=AssertionError('No artifact read')):
            result = self.work.check_lead_identities(self.packet()).data
        self.assertEqual(before, self.work.db_path.read_bytes())
        match = result['leads'][0]['candidates'][0]
        self.assertEqual(['same_platform_job_id','same_employer_requisition','same_url',
                          'same_employer_title_city'], match['signals'])
        self.assertTrue(match['prior_attempt_needs_reconciliation'])
        self.assertEqual('closed', match['liveness'])
        self.assertEqual(1, result['matched_leads'])
        self.assertFalse(result['deduplication_complete'])
        self.assertFalse(result['external_history_checked'])
        self.assertEqual(0, result['job_records_added'])

    def test_partial_identities_order_and_unmatched_are_not_clearance(self):
        title_hint = dict(self.lead, id='hint', platform='', platform_job_id='', req_id='',
                          city='Ho Chi Minh City', title=' AI   DEVELOPER ',url='https://jobs.example.test/other')
        unmatched = dict(title_hint, id='unknown', employer='Other Company')
        result = self.work.check_lead_identities(self.packet(unmatched,title_hint)).data
        self.assertEqual(['unknown','hint'], [r['id'] for r in result['leads']])
        self.assertEqual([], result['leads'][0]['candidates'])
        self.assertEqual(['same_employer_title_city'], result['leads'][1]['candidates'][0]['signals'])
        self.assertEqual(1, result['unmatched_leads'])
        self.assertFalse(result['deduplication_complete'])

    def test_requisition_does_not_cross_employer_but_exact_url_is_a_hint(self):
        other = dict(self.lead, id='other', employer='Other Company', platform='other',
                     platform_job_id='different', title='Different',city='Hanoi',url='https://jobs.example.test/other')
        self.assertEqual([], self.work.check_lead_identities(self.packet(other)).data['leads'][0]['candidates'])
        other['url'] = self.lead['url']
        result = self.work.check_lead_identities(self.packet(other)).data
        self.assertEqual(['same_url'], result['leads'][0]['candidates'][0]['signals'])

    def test_invalid_whole_batches_fail_before_reading_tracker(self):
        invalid = [self.packet(), self.packet(), self.packet(), self.packet(), self.packet(), self.packet()]
        invalid[0]['leads'] = []
        invalid[1]['leads'] = [self.lead]*51
        invalid[2]['leads'] = [self.lead, self.lead]
        invalid[3]['leads'][0] = dict(self.lead, url='https://fixture@jobs.example.invalid/job')
        invalid[4]['leads'][0] = dict(self.lead, private_cv='not accepted')
        invalid[5]['schema_version'] = '9.0'
        before = self.work.db_path.read_bytes()
        for index,value in enumerate(invalid):
            with self.subTest(case=index), patch('core.workflow.sqlite3.connect',
                    side_effect=AssertionError('Invalid input must not open the tracker')), self.assertRaises((ContractError, ValueError)):
                self.work.check_lead_identities(copy.deepcopy(value))
        self.assertEqual(before, self.work.db_path.read_bytes())

    def test_fifty_leads_use_one_read_only_select_and_preserve_input(self):
        packet = self.packet(*(dict(self.lead,id=f'lead-{i}') for i in range(50)))
        original = copy.deepcopy(packet)
        connect = sqlite3.connect
        queries = []
        def observed(*args, **kwargs):
            self.assertTrue(args[0].endswith('?mode=ro'))
            self.assertTrue(kwargs['uri'])
            connection = connect(*args, **kwargs)
            connection.set_trace_callback(queries.append)
            return connection
        with patch('core.workflow.sqlite3.connect',side_effect=observed) as calls:
            result = self.work.check_lead_identities(packet).data
        self.assertEqual(1,calls.call_count)
        self.assertEqual(1,sum(q.startswith('SELECT ') for q in queries))
        self.assertEqual(50,result['matched_leads'])
        self.assertEqual(original,packet)

    def test_missing_or_other_workspace_is_not_created_or_read(self):
        missing = Preparation(self.base/'missing',ROOT)
        with self.assertRaises(WorkflowError):
            missing.check_lead_identities(self.packet())
        self.assertFalse(missing.data_dir.exists())
        other = Preparation(self.base/'other',ROOT)
        other.init()
        self.assertEqual([], other.check_lead_identities(self.packet()).data['leads'][0]['candidates'])

    def test_real_cli_exposes_read_only_batch_and_structured_rejection(self):
        path=self.base/'leads.json'
        for value,code in [(self.packet(),0),({'schema_version':'1.0','leads':[]},2)]:
            path.write_text(json.dumps(value),encoding='utf8')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/kit.py'),'--data-dir',
                str(self.work.data_dir),'check-lead-identities','--file',str(path)],
                cwd=self.tmp.name,capture_output=True,encoding='utf8',timeout=15)
            self.assertEqual(code,result.returncode,result.stdout+result.stderr)
            payload=json.loads(result.stdout)
            if code==0:
                self.assertEqual(1,payload['data']['matched_leads'])
                self.assertEqual(0,payload['data']['external_actions'])
            else:
                self.assertEqual('needs_input',payload['outcome'])
