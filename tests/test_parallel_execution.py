import base64
import copy
import json
from pathlib import Path
import sqlite3
import threading
import unittest
from unittest.mock import patch

import test_manifests as fixtures
from test_documents import fake_render
from core.execution import Executor
from core.parallel_execution import ParallelExecutor, run_parallel_with_bridge
from core.workflow import WorkflowError
from core.contracts import ContractError
from core.ledger import Kit


class ParallelExecutionTests(unittest.TestCase):
    setUp = fixtures.ManifestTests.setUp
    tearDown = fixtures.ManifestTests.tearDown
    plan = fixtures.ManifestTests.plan
    approve = fixtures.ManifestTests.approve

    def start(self, count=2, limit=None, workers=10):
        self.work=ParallelExecutor(self.root);self.work.init()
        fixture=Path(__file__).resolve().parents[1]/'examples/fictional'
        load=lambda name:json.loads((fixture/name).read_text(encoding='utf8'))
        plan=self.plan()
        plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30}
        for index in range(2,count+1):
            job=load('job.json');job.update(platform_job_id=f'FICT-{index}',req_id=f'FICT-{index}')
            job_id=self.work.import_job(job).data['job']['id']
            self.work.assess(job_id,load('matrix.json'));self.work.prepare(job_id,load('plan.json'))
            with patch('core.documents.render_files',side_effect=fake_render):render=self.work.render(job_id).data
            review={'schema_version':'1.0','render_fingerprint':render['fingerprint'],
                'reviewed_pages':[1],'checks':dict.fromkeys(['content','layout','glyphs','language'],True)}
            path=self.root/f'review-{index}.json';path.write_text(json.dumps(review),encoding='utf8')
            self.work.review_documents(render['render_id'],path)
            entry=copy.deepcopy(plan['entries'][0]);entry.update(job_id=job_id,render_id=render['render_id'],
                destination=f'https://apply.example.test/form/FICT-{index}')
            plan['entries'].append(entry)
        plan['submission_limit']=limit if limit is not None else count
        result=self.work.create_manifest(plan).data;self.approve(result)
        self.fingerprint=result['fingerprint']
        self.entries={e['job_id']:e for e in result['manifest']['entries']}
        (self.root/'confirmation.png').write_bytes(base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
        return self.work.start_parallel_execution(self.fingerprint,'fictional-browser',30,workers).data['run_id']

    def receipt(self, request):
        e=self.entries[request['job_id']]
        result={'schema_version':'1.0','request_id':request['request_id'],
            'binding_id':f"fictional-tab-{request['job_id']}",'url':e['destination'],
            'employer':e['employer'],'requisition':e['requisition'],'status':'ok'}
        if request['action'] in {'inspect','fill','upload','review'}:
            result['form']={'fields':['salary'],'required_fields':['salary'],
                'consents':[{'id':'privacy-v1','text':'Fictional retention policy','required':True}],
                'upload_extensions':['.pdf'],'blockers':[]}
        if request['action']=='upload':result['document_sha256']=e['document_sha256']
        if request['action']=='review':result.update(values={'salary':'Negotiable'},
            consents=e['consents'],document_sha256=e['document_sha256'])
        if request['action']=='verify':result.update(confirmed=True,
            confirmation_text='Fictional application submitted',screenshot='confirmation.png')
        return result

    def test_ten_actual_concurrent_submissions_one_ledger_writer(self):
        run=self.start(10)
        barriers={action:threading.Barrier(10,timeout=30) for action in ['inspect','submit']}
        lock=threading.Lock();active=0;peak=0;seen=[];writer_threads=[]
        test=self;original_db=Kit._db
        def db(work):
            writer_threads.append(threading.get_ident())
            return original_db(work)
        class Bridge:
            def perform(self,request):
                nonlocal active,peak
                with lock:active+=1;peak=max(peak,active);seen.append((request['job_id'],request['action']))
                try:
                    if request['action'] in barriers:barriers[request['action']].wait()
                    return test.receipt(request)
                finally:
                    with lock:active-=1
        with patch.object(Kit,'_db',db):result=run_parallel_with_bridge(self.work,run,Bridge())
        self.assertEqual(result.data['state'],'completed',result.data)
        self.assertEqual(result.data['worker_errors'],[])
        self.assertEqual(peak,10)
        self.assertEqual(set(writer_threads),{threading.get_ident()})
        self.assertEqual(len(seen),60)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],10)
            self.assertEqual(db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0],10)
        for job in self.entries:
            self.assertEqual([action for ident,action in seen if ident==job],['inspect','fill','upload','review','submit','verify'])

    def test_out_of_order_receipts_lane_bindings_and_legacy_isolation(self):
        run=self.start()
        first=self.work.next_parallel_action(run,1).data['request']
        second=self.work.next_parallel_action(run,2).data['request']
        with self.assertRaises(WorkflowError):Executor(self.root).next_action(run)
        with self.assertRaises(WorkflowError):self.work.next_parallel_action(run,1)
        self.work.record_parallel_action(run,self.receipt(second))
        bad=self.receipt(first);bad['binding_id']='fictional-tab-2'
        with self.assertRaises(WorkflowError):self.work.record_parallel_action(run,bad)
        self.work.record_parallel_action(run,self.receipt(first))
        with self.assertRaises(WorkflowError):self.work.record_parallel_action(run,self.receipt(first))
        self.assertEqual(self.work.next_parallel_action(run,1).data['request']['binding_id'],'fictional-tab-1')

    def test_unknown_submit_is_never_retried_other_lane_completes(self):
        run=self.start();test=self;calls=[]
        class Bridge:
            def perform(self,request):
                calls.append((request['job_id'],request['action']))
                if request['job_id']==1 and request['action']=='submit':raise ConnectionError('accepted then lost')
                return test.receipt(request)
        result=run_parallel_with_bridge(self.work,run,Bridge())
        self.assertEqual(result.data['state'],'submission_unknown')
        states={item['job_id']:item['state'] for item in result.data['lanes']}
        self.assertEqual(states,{1:'submission_unknown',2:'completed'})
        self.assertEqual([item['job_id'] for item in self.work.parallel_cleanup(run).data['requests']],[2])
        self.work.revoke_manifest(self.fingerprint,'Revoked after possible submit')
        self.work.recover_parallel_execution(run,1)
        request=self.work.next_parallel_action(run,1).data['request']
        self.assertEqual(request['action'],'verify')
        self.work.record_parallel_action(run,self.receipt(request))
        self.assertEqual(calls.count((1,'submit')),1)
        self.assertEqual(self.work.parallel_status(run).data['state'],'completed')

    def test_budget_revocation_pending_restart_and_schema_migration(self):
        run=self.start(2,limit=1)
        self.assertEqual(self.work.parallel_status(run).data['lanes'][1]['state'],'completed_limit')
        request=self.work.next_parallel_action(run,1).data['request']
        with self.assertRaises(WorkflowError):run_parallel_with_bridge(self.work,run,object())
        self.work.revoke_manifest(self.fingerprint,'Revoked before browser dispatch')
        with self.assertRaises(WorkflowError):self.work.check_parallel_action(run,request['request_id'])
        self.work.init()  # idempotent schema 6 initialization with a pending action
        with self.work._db() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],6)
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],0)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='execution_one_pending'").fetchone())
        with self.assertRaises(ContractError):self.work.start_parallel_execution(self.fingerprint,'fictional-browser',30,11)

    def test_manual_dispatch_honors_worker_cap_and_schema5_requires_migration(self):
        run=self.start(2,workers=1)
        request=self.work.next_parallel_action(run,1).data['request']
        with self.assertRaises(WorkflowError):self.work.next_parallel_action(run,2)
        with self.work._db() as db:
            db.execute('DROP INDEX execution_one_pending_per_job')
            db.execute('CREATE UNIQUE INDEX execution_one_pending ON execution_actions(run_id) WHERE receipt IS NULL')
            db.execute('PRAGMA user_version=5')
        self.work.init()
        with self.work._db() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],6)
            self.assertEqual(db.execute('SELECT id FROM execution_actions WHERE receipt IS NULL').fetchone()[0],request['request_id'])
        self.work.record_parallel_action(run,self.receipt(request))
        self.assertEqual(self.work.next_parallel_action(run,2).data['request']['action'],'inspect')

    def test_parallel_start_rolls_back_if_schema_is_not_migrated(self):
        run=self.start(1)
        self.work.stop_parallel_execution(run,'Fictional migration test')
        plan=self.plan();plan['campaign_id']='migration-scope'
        plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30}
        scope=self.work.create_manifest(plan).data;self.approve(scope)
        with self.work._db() as db:db.execute('PRAGMA user_version=5')
        with self.assertRaises(WorkflowError):self.work.start_parallel_execution(scope['fingerprint'],'fictional-browser',30)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_runs').fetchone()[0],1)

    def test_cleanup_closes_only_confirmed_owned_bindings_and_records_receipts(self):
        run=self.start(2);test=self;closed=[]
        self.assertEqual(self.work.parallel_cleanup(run).data['requests'],[])
        class Bridge:
            def perform(self,request):return test.receipt(request)
            def close_application_tab(self,request):
                test.assertEqual(test.work.get_job(request['job_id'])['state'],'confirmed_submitted')
                test.assertEqual(request['binding_id'],f"fictional-tab-{request['job_id']}")
                closed.append(request['job_id'])
                return {'schema_version':'1.0','request_id':request['request_id'],
                    'bridge_id':request['bridge_id'],'binding_id':request['binding_id'],
                    'status':'closed','agent_owned':True,'cleanup_requested':True}
        result=run_parallel_with_bridge(self.work,run,Bridge())
        self.assertEqual(result.data['state'],'completed')
        self.assertEqual(sorted(closed),[1,2])
        self.assertEqual(result.data['cleanup']['requests'],[])
        with self.work._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM execution_actions WHERE action='cleanup'").fetchone()[0],2)
            self.assertEqual(db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0],2)

    def test_restart_finishes_saved_confirmation_cleanup_once(self):
        run=self.start(1);test=self;closed=[]
        # Simulate process interruption after confirmation is committed but
        # before the bridge receives its cleanup request.
        for _ in range(6):
            request=self.work.next_parallel_action(run,1).data['request']
            self.work.record_parallel_action(run,self.receipt(request))
        self.assertEqual(len(self.work.parallel_cleanup(run).data['requests']),1)
        class Bridge:
            def perform(self,request):
                raise AssertionError('Completed application must not be replayed')
            def close_application_tab(self,request):
                test.assertEqual(test.work.get_job(request['job_id'])['state'],'confirmed_submitted')
                closed.append(request['request_id'])
                return {'schema_version':'1.0','request_id':request['request_id'],
                    'bridge_id':request['bridge_id'],'binding_id':request['binding_id'],
                    'status':'closed','agent_owned':True,'cleanup_requested':True}
        first=run_parallel_with_bridge(self.work,run,Bridge())
        self.assertEqual(first.data['cleanup']['requests'],[])
        second=run_parallel_with_bridge(self.work,run,Bridge())
        self.assertEqual(second.data['cleanup']['requests'],[])
        self.assertEqual(len(closed),1)


if __name__=='__main__':unittest.main()
