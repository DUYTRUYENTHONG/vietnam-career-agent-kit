"""Fictional post-confirmation tab cleanup, never a new submit path."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_execution as execution_fixtures
from core.execution import Executor,run_with_bridge
from core.workflow import WorkflowError


class CleanupTests(unittest.TestCase):
    setUp=execution_fixtures.ExecutionTests.setUp
    tearDown=execution_fixtures.ExecutionTests.tearDown
    plan=execution_fixtures.ExecutionTests.plan
    approve=execution_fixtures.ExecutionTests.approve
    start=execution_fixtures.ExecutionTests.start
    receipt=execution_fixtures.ExecutionTests.receipt
    step=execution_fixtures.ExecutionTests.step

    def finish(self,run):
        for _ in range(5):self.step(run)
        request=self.work.next_action(run).data['request']
        return self.work.record_action(run,self.receipt(request))

    def ack(self,item,status='closed'):
        return {'schema_version':'1.0','request_id':item['request_id'],
                'bridge_id':item['bridge_id'],'binding_id':item['binding_id'],'status':status,
                'agent_owned':True,'cleanup_requested':True}

    def test_unknown_or_unsubmitted_application_never_requests_tab_closure(self):
        run=self.start()
        self.assertEqual(self.work.cleanup_execution(run).data['requests'],[])
        for _ in range(5):self.step(run)
        request=self.work.next_action(run).data['request'];receipt=self.receipt(request)
        receipt['confirmed']=False;self.work.record_action(run,receipt)
        self.assertEqual(self.work.cleanup_execution(run).data['requests'],[])
        self.assertEqual(self.work.get_job(1)['state'],'submission_uncertain')

    def test_saved_confirmation_emits_exact_binding_cleanup_even_after_revocation(self):
        run=self.start();result=self.finish(run)
        item=result.data['cleanup']['requests'][0]
        self.assertEqual(self.work.get_job(1)['state'],'confirmed_submitted')
        self.assertEqual(item['action'],'close_application_tab')
        self.assertEqual(item['binding_id'],'fictional-tab')
        self.assertEqual(item['job_id'],1)
        self.assertTrue(item['requires_agent_owned'])
        self.assertTrue(item['requires_cleanup_request'])
        self.assertTrue((self.root/item['screenshot']['path']).is_file())
        self.work.revoke_manifest(self.fingerprint,'Fictional expiry after receipt')
        self.assertEqual(self.work.cleanup_execution(run).data['requests'][0],item)

    def test_wrong_binding_unowned_unrequested_and_wrong_coordinator_are_blocked(self):
        run=self.start();self.finish(run)
        item=self.work.cleanup_execution(run).data['requests'][0]
        for change in [{'bridge_id':'another-bridge'},{'binding_id':'another-tab'},{'agent_owned':False},{'cleanup_requested':False}]:
            with self.subTest(change=change):
                with self.assertRaises(WorkflowError):self.work.record_cleanup(run,{**self.ack(item),**change})
        with self.assertRaises(WorkflowError):Executor(self.root,actor='other-owner').record_cleanup(run,self.ack(item))
        self.assertEqual(len(self.work.cleanup_execution(run).data['requests']),1)

    def test_cleanup_ack_is_idempotent_and_never_changes_application_count(self):
        run=self.start();self.finish(run)
        item=self.work.cleanup_execution(run).data['requests'][0];receipt=self.ack(item)
        self.assertTrue(self.work.record_cleanup(run,receipt).data['cleanup_recorded'])
        self.assertTrue(self.work.record_cleanup(run,receipt).data['already_recorded'])
        self.assertEqual(self.work.cleanup_execution(run).data['requests'],[])
        self.assertEqual(self.work.tracker().data['observed_submissions'],1)
        with self.work._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM execution_actions WHERE action='cleanup'").fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],1)

    def test_failed_tab_close_stays_pending_without_resubmitting(self):
        run=self.start();self.finish(run)
        item=self.work.cleanup_execution(run).data['requests'][0]
        result=self.work.record_cleanup(run,{**self.ack(item,'failed'),'reason':'Host could not close this tab'})
        self.assertFalse(result.data['tab_closed'])
        row=self.work.tracker().data['jobs'][0]
        self.assertIsNone(row['blocker'])
        self.assertEqual(row['cleanup_blocker'],'Host could not close this tab')
        self.assertEqual(len(self.work.cleanup_execution(run).data['requests']),1)
        self.work.record_cleanup(run,self.ack(item,'already_absent'))
        self.assertEqual(self.work.get_job(1)['state'],'confirmed_submitted')
        self.assertEqual(self.work.cleanup_execution(run).data['requests'],[])

    def test_missing_saved_screenshot_blocks_closure_but_preserves_confirmation(self):
        run=self.start();self.finish(run)
        item=self.work.cleanup_execution(run).data['requests'][0]
        (self.root/item['screenshot']['path']).unlink()
        pending=self.work.cleanup_execution(run).data
        self.assertEqual(pending['requests'],[])
        self.assertEqual(pending['blocked'][0]['job_id'],1)
        with self.assertRaises(WorkflowError):self.work.record_cleanup(run,self.ack(item))
        self.assertEqual(self.work.get_job(1)['state'],'confirmed_submitted')

    def test_real_cli_records_cleanup_after_success(self):
        run=self.start();self.finish(run)
        cli=Path(__file__).resolve().parents[1]/'scripts/kit.py'
        def invoke(*args):
            result=subprocess.run([sys.executable,str(cli),'--data-dir',str(self.root),
                *args],capture_output=True,encoding='utf8',timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return json.loads(result.stdout)['data']
        item=invoke('cleanup-execution','--run-id',run)['requests'][0]
        proof=self.root/'cleanup-receipt.json';proof.write_text(json.dumps(self.ack(item)),encoding='utf8')
        invoke('record-cleanup','--run-id',run,'--receipt',str(proof))
        self.assertEqual(invoke('cleanup-execution','--run-id',run)['requests'],[])

    def test_explicit_bridge_cleanup_runs_only_after_canonical_confirmation(self):
        run=self.start();test=self;closed=[]
        class Bridge:
            def perform(self,request):return test.receipt(request)
            def close_application_tab(self,request):
                test.assertEqual(test.work.get_job(1)['state'],'confirmed_submitted')
                test.assertTrue((test.root/request['screenshot']['path']).is_file())
                closed.append(request['binding_id'])
                return test.ack(request)
        result=run_with_bridge(self.work,run,Bridge())
        self.assertEqual(result.data['state'],'completed')
        self.assertEqual(closed,['fictional-tab'])
        self.assertEqual(result.data['cleanup']['requests'],[])

    def test_terminal_resume_with_explicit_cleanup_bridge_closes_remaining_tab(self):
        run=self.start();self.finish(run);self.work.next_action(run)
        test=self;closed=[]
        class Bridge:
            def perform(self,request):raise AssertionError('Completed run must not issue application actions')
            def close_application_tab(self,request):
                closed.append(request['binding_id']);return test.ack(request)
        result=run_with_bridge(self.work,run,Bridge())
        self.assertEqual(result.data['state'],'completed')
        self.assertEqual(closed,['fictional-tab'])
        self.assertEqual(result.data['cleanup']['requests'],[])

    def test_cleanup_bridge_failure_is_reported_after_read_only_recovery(self):
        run=self.start()
        for _ in range(5):self.step(run)
        verify=self.work.next_action(run).data['request'];receipt=self.receipt(verify)
        receipt['confirmed']=False;self.work.record_action(run,receipt)
        self.work.recover_execution(run);test=self
        class Bridge:
            def perform(self,request):
                test.assertEqual(request['action'],'verify');return test.receipt(request)
            def close_application_tab(self,request):raise RuntimeError('Fictional host interruption')
        result=run_with_bridge(self.work,run,Bridge())
        self.assertEqual(result.data['state'],'recovered')
        self.assertTrue(any('cleanup failed' in issue for issue in result.issues))
        self.assertEqual(len(result.data['cleanup']['requests']),1)
        self.assertEqual(self.work.tracker().data['observed_submissions'],1)

    def reused_binding(self):
        import copy
        from test_documents import fake_render
        self.work=Executor(self.root);self.work.init()
        fixture=Path(__file__).resolve().parents[1]/'examples/fictional'
        load=lambda name:json.loads((fixture/name).read_text(encoding='utf8'))
        job=load('job.json');job.update(platform_job_id='FICT-SECOND',req_id='FICT-SECOND')
        second=self.work.import_job(job).data['job']['id']
        self.work.assess(second,load('matrix.json'));self.work.prepare(second,load('plan.json'))
        with patch('core.documents.render_files',side_effect=fake_render):render=self.work.render(second).data
        review={'schema_version':'1.0','render_fingerprint':render['fingerprint'],
            'reviewed_pages':[1],'checks':dict.fromkeys(['content','layout','glyphs','language'],True)}
        path=self.root/'second-review.json';path.write_text(json.dumps(review),encoding='utf8')
        self.work.review_documents(render['render_id'],path)
        plan=self.plan();plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30};plan['submission_limit']=2
        entry=copy.deepcopy(plan['entries'][0]);entry.update(job_id=second,render_id=render['render_id'],destination='https://apply.example.test/form/FICT-SECOND')
        plan['entries'].append(entry)
        result=self.work.create_manifest(plan).data;self.approve(result)
        run=self.work.start_execution(result['fingerprint'],'fictional-browser',30).data['run_id']
        self.entry=result['manifest']['entries'][0];old=self.finish(run).data['cleanup']['requests'][0]
        self.entry=result['manifest']['entries'][1]
        request=self.work.next_action(run).data['request'];self.work.record_action(run,self.receipt(request))
        self.assertEqual(self.work.next_action(run).data['request']['action'],'fill')
        return run,old

    def test_review_reused_binding_suppresses_old_cleanup_and_rejects_stale_ack(self):
        run,old=self.reused_binding()
        self.assertNotIn(old['request_id'],[r['request_id'] for r in self.work.cleanup_execution(run).data['requests']])
        with self.assertRaises(WorkflowError):self.work.record_cleanup(run,self.ack(old))
        self.assertNotEqual(self.work.get_job(2)['state'],'confirmed_submitted')
        with self.work._db() as db:
            row=db.execute('SELECT job_id,action FROM execution_actions WHERE run_id=? AND receipt IS NULL',(run,)).fetchone()
        self.assertEqual(tuple(row),(2,'fill'))

    def test_review_bridge_revalidates_stale_cleanup_before_closing(self):
        from core.cleanup import through_bridge
        run,old=self.reused_binding();called=[];test=self
        class Bridge:
            def close_application_tab(self,request):called.append(request);return test.ack(request)
        issues=through_bridge(self.work,run,Bridge(),[old],set())
        self.assertEqual(called,[])
        self.assertTrue(issues)

    def test_review_successful_cleanup_is_not_an_application_tracker_blocker(self):
        run=self.start();self.finish(run)
        self.work.record_cleanup(run,self.ack(self.work.cleanup_execution(run).data['requests'][0]))
        row=self.work.tracker().data['jobs'][0]
        self.assertIsNone(row['blocker'])
        self.assertEqual(row['latest_action'],'verify')
        self.assertEqual(row['cleanup_status'],'closed')
        self.assertIsNone(row['cleanup_blocker'])
