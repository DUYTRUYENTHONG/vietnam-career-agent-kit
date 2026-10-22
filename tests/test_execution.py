import copy
import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import test_manifests as manifest_fixtures
from core.execution import Executor
from core.execution import run_with_bridge
from core.workflow import WorkflowError


class ExecutionTests(unittest.TestCase):
    setUp = manifest_fixtures.ManifestTests.setUp
    tearDown = manifest_fixtures.ManifestTests.tearDown
    plan = manifest_fixtures.ManifestTests.plan
    approve = manifest_fixtures.ManifestTests.approve

    def start(self, mode='APPROVED_BATCH'):
        self.work = Executor(self.root)
        self.work.init()
        plan = self.plan()
        plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30}
        if mode == 'ASSIST':
            plan.update(mode=mode, submission_limit=0)
            plan['entries'][0]['operations'] = ['fill', 'upload']
        result = self.work.create_manifest(plan).data
        self.approve(result)
        self.entry = result['manifest']['entries'][0]
        self.fingerprint = result['fingerprint']
        return self.work.start_execution(self.fingerprint, 'fictional-browser', 30).data['run_id']

    def receipt(self, action):
        e = self.entry
        result = {'schema_version':'1.0', 'request_id':action['request_id'],
                  'binding_id':'fictional-tab', 'url':e['destination'],
                  'employer':e['employer'], 'requisition':e['requisition'], 'status':'ok'}
        if action['action'] in {'inspect','fill','upload','review'}:
            result['form']={'fields':['salary'], 'required_fields':['salary'],
                'consents':[{'id':'privacy-v1','text':'Fictional retention policy','required':True}],
                'upload_extensions':['.pdf'], 'blockers':[]}
        if action['action'] == 'review':
            result.update(values={'salary':'Negotiable'},
                consents=[{'id':'privacy-v1','text':'Fictional retention policy','choice':True}],
                document_sha256=e['document_sha256'])
        if action['action'] == 'upload':
            result['document_sha256']=e['document_sha256']
        if action['action'] == 'verify':
            # A tiny real PNG for private evidence validation; never a real application.
            import base64
            image=self.root/'confirmation.png'
            image.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
            result.update(confirmed=True, confirmation_text='Fictional application submitted',
                          screenshot='confirmation.png')
        return result

    def step(self, run):
        action=self.work.next_action(run).data['request']
        self.work.record_action(run,self.receipt(action))
        return action

    def until_submit(self, run):
        for expected in ['inspect','fill','upload','review']:
            self.assertEqual(self.step(run)['action'],expected)
        return self.work.next_action(run).data['request']

    def test_attempt_is_durable_before_submit_and_submit_is_never_reissued(self):
        run=self.start();request=self.until_submit(run)
        self.assertEqual(request['action'],'submit')
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],1)
        recovery=self.work.next_action(run).data['request']
        self.assertEqual(recovery['action'],'verify')
        self.assertEqual(recovery['attempt_id'],request['attempt_id'])
        self.work.record_action(run,self.receipt(recovery))
        self.assertEqual(self.work.get_job(1)['state'],'confirmed_submitted')
        self.assertEqual(self.work.next_action(run).data['state'],'completed')

    def test_assist_stops_without_attempt_or_submit(self):
        run=self.start('ASSIST')
        for expected in ['inspect','fill','upload','review']:
            self.assertEqual(self.step(run)['action'],expected)
        self.assertEqual(self.work.next_action(run).data['state'],'assisted')
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],0)

    def test_new_required_field_blocks_before_any_disclosure(self):
        run=self.start();action=self.work.next_action(run).data['request']
        receipt=self.receipt(action);receipt['form']['required_fields'].append('unconfirmed_answer')
        with self.assertRaises(WorkflowError):self.work.record_action(run,receipt)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],0)

    def test_page_redirect_or_wrong_employer_is_rejected(self):
        for field,value in [('url','https://other.example.test/'),('employer','Different employer')]:
            with self.subTest(field=field):
                run=self.start();action=self.work.next_action(run).data['request']
                receipt=self.receipt(action);receipt[field]=value
                with self.assertRaises(WorkflowError):self.work.record_action(run,receipt)
                self.work.stop_execution(run,'Fictional test reset')

    def test_revocation_blocks_fill_but_not_read_only_confirmation_recovery(self):
        run=self.start();self.step(run)
        self.work.revoke_manifest(self.fingerprint,'Candidate revoked')
        with self.assertRaises(WorkflowError):self.work.next_action(run)

    def test_single_active_coordinator_and_receipt_replay_are_blocked(self):
        run=self.start()
        with self.assertRaises(WorkflowError):
            self.work.start_execution(self.fingerprint,'second-browser',30)
        action=self.work.next_action(run).data['request'];receipt=self.receipt(action)
        self.work.record_action(run,receipt)
        with self.assertRaises(WorkflowError):self.work.record_action(run,receipt)

    def test_failed_confirmation_stops_and_cannot_retry_job(self):
        run=self.start();self.until_submit(run)
        verify=self.work.next_action(run).data['request']
        receipt=self.receipt(verify);receipt['confirmed']=False
        self.work.record_action(run,receipt)
        self.assertEqual(self.work.get_job(1)['state'],'submission_uncertain')
        self.assertEqual(self.work.next_action(run).outcome,'submission_unknown')
        with self.assertRaises(WorkflowError):self.work.start_execution(self.fingerprint,'new-browser',30)

    def test_preparation_only_approval_cannot_be_silently_upgraded(self):
        self.work=Executor(self.root);self.work.init()
        result=self.work.create_manifest(self.plan()).data;self.approve(result)
        with self.assertRaises(WorkflowError):
            self.work.start_execution(result['fingerprint'],'fictional-browser',30)

    def test_additive_schema_upgrade_preserves_existing_review_and_never_downgrades(self):
        before=self.work.current_render(self.render['render_id'])
        with self.work._db() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
        self.work=Executor(self.root);self.work.init();self.work.init()
        manifest_fixtures.Campaign(self.root).init()
        with self.work._db() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
        after=self.work.current_render(self.render['render_id'])
        self.assertEqual(before,after)

    def test_real_cli_execution_loop_and_accurate_markdown_report(self):
        import subprocess
        import sys
        from pathlib import Path
        self.work=Executor(self.root);self.work.init()
        plan=self.plan();plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30}
        result=self.work.create_manifest(plan).data;self.approve(result);self.entry=result['manifest']['entries'][0]
        def cli(*args):
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/kit.py'),
                '--data-dir',str(self.root),*args],capture_output=True,encoding='utf8',timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return json.loads(result.stdout)['data']
        run=cli('start-execution','--fingerprint',result['fingerprint'],'--bridge-id','fictional-browser','--runtime-minutes','30')['run_id']
        for phase in ['inspect','fill','upload','review','submit','verify']:
            request=cli('next-action','--run-id',run)['request'];self.assertEqual(request['action'],phase)
            cli('check-action','--run-id',run,'--request-id',request['request_id'])
            receipt=self.root/'receipt.json';receipt.write_text(json.dumps(self.receipt(request)),encoding='utf8')
            cli('record-action','--run-id',run,'--receipt',str(receipt))
        self.assertEqual(cli('next-action','--run-id',run)['state'],'completed')
        self.assertEqual(len(cli('execution-status','--run-id',run)['actions']),6)
        report=cli('report','--format','md','--output','reports/executed.md')
        text=(self.root/report['path']).read_text(encoding='utf8')
        self.assertIn('Host-observed confirmed applications: 1',text)
        self.assertNotIn('no application performed',text)

    def test_bridge_and_runtime_are_bound_to_the_reviewed_manifest(self):
        run=self.start();self.work.stop_execution(run,'Fictional stop')
        for bridge,minutes in [('other-browser',30),('fictional-browser',60),('fictional-browser',True)]:
            with self.subTest(bridge=bridge,minutes=minutes):
                with self.assertRaises(WorkflowError):self.work.start_execution(self.fingerprint,bridge,minutes)

    def test_runtime_expiry_and_document_tampering_block_next_disclosure(self):
        run=self.start();self.step(run)
        with patch('core.execution.now_utc',return_value=datetime.now(timezone.utc)+timedelta(hours=1)):
            with self.assertRaises(WorkflowError):self.work.next_action(run)
        (self.root/self.entry['document']['path']).write_bytes(b'changed after approval')
        with self.assertRaises(WorkflowError):self.work.next_action(run)

    def test_new_consent_or_challenge_is_not_accepted_by_automation(self):
        run=self.start();request=self.work.next_action(run).data['request']
        for change in ['consent','challenge']:
            receipt=self.receipt(request)
            if change=='consent':receipt['form']['consents'].append({'id':'legal-contract','text':'New agreement','required':True})
            else:receipt['form']['blockers']=['captcha']
            with self.assertRaises(WorkflowError):self.work.record_action(run,receipt)

    def test_visible_review_changes_prevent_submit(self):
        run=self.start()
        for unused in range(3):self.step(run)
        request=self.work.next_action(run).data['request']
        receipt=self.receipt(request);receipt['values']['salary']='Different value'
        with self.assertRaises(WorkflowError):self.work.record_action(run,receipt)
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],0)

    def test_every_pre_submit_receipt_requires_fresh_unchanged_form(self):
        from core.contracts import ContractError
        run=self.start()
        for phase in ['inspect','fill','upload','review']:
            request=self.work.next_action(run).data['request']
            self.assertEqual(request['action'],phase)
            for change in ['missing','captcha','required','removed','consent']:
                with self.subTest(phase=phase,change=change):
                    receipt=self.receipt(request)
                    if change=='missing':del receipt['form']
                    elif change=='captcha':receipt['form']['blockers']=['captcha']
                    elif change=='required':receipt['form']['required_fields'].append('unknown')
                    elif change=='removed':receipt['form'].update(fields=[],required_fields=[])
                    else:receipt['form']['consents'][0]['text']='Changed terms'
                    with self.assertRaises((WorkflowError,ContractError)):self.work.record_action(run,receipt)
            self.work.record_action(run,self.receipt(request))
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],0)

    def test_issued_action_is_rechecked_after_revocation_and_report_is_accurate(self):
        run=self.start();request=self.work.next_action(run).data['request']
        self.assertTrue(self.work.check_action(run,request['request_id']).data['current'])
        self.work.revoke_manifest(self.fingerprint,'Revoked while action pending')
        with self.assertRaises(WorkflowError):self.work.check_action(run,request['request_id'])
        self.work.stop_execution(run,'Stop fictional scope')
        # New independent workspace: reporting after a complete host loop.
        self.tearDown();self.setUp();run=self.start()
        test=self
        class Bridge:
            def perform(self,request):return test.receipt(request)
        run_with_bridge(self.work,run,Bridge())
        resumed=self.work.resume()
        self.assertEqual(resumed.data['mode'],'EXECUTION')
        self.assertEqual(resumed.data['observed_submissions'],1)
        self.assertEqual(resumed.data['external_actions'],3)
        self.assertNotIn('chưa gửi',resumed.message)

    def test_confirmation_recovery_survives_revocation_and_expiry(self):
        run=self.start();self.until_submit(run)
        self.work.revoke_manifest(self.fingerprint,'Candidate revoked after possible click')
        with patch('core.execution.now_utc',return_value=datetime.now(timezone.utc)+timedelta(days=2)):
            request=self.work.next_action(run).data['request']
            self.assertEqual(request['action'],'verify')
            self.work.record_action(run,self.receipt(request))
        self.assertEqual(self.work.get_job(1)['state'],'confirmed_submitted')

    def test_uncertain_run_can_only_recover_read_only_and_evidence_is_immutable(self):
        run=self.start();self.until_submit(run)
        request=self.work.next_action(run).data['request']
        receipt=self.receipt(request);receipt['confirmed']=False
        self.work.record_action(run,receipt)
        self.work.recover_execution(run)
        request=self.work.next_action(run).data['request']
        self.assertEqual(request['action'],'verify')
        self.work.record_action(run,self.receipt(request))
        self.assertEqual(self.work.next_action(run).data['state'],'recovered')
        with self.work._db() as db:
            for table in ['execution_attempts','execution_submissions','execution_actions']:
                with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM '+table)

    def test_bridge_exception_after_submit_never_automatically_retries(self):
        run=self.start();calls=[];test=self
        class Bridge:
            def perform(self,request):
                calls.append(request['action'])
                if request['action']=='submit':raise ConnectionError('Fictional interruption')
                return test.receipt(request)
        with self.assertRaises(ConnectionError):run_with_bridge(self.work,run,Bridge())
        self.assertEqual(calls,['inspect','fill','upload','review','submit'])
        self.assertEqual(self.work.next_action(run).data['request']['action'],'verify')

    def test_two_coordinators_racing_cannot_start_two_runs(self):
        from concurrent.futures import ThreadPoolExecutor
        run=self.start();self.work.stop_execution(run,'Create next fictional scope')
        plan=self.plan();plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30}
        result=self.work.create_manifest(plan).data;self.approve(result)
        def start():
            try:
                return Executor(self.root).start_execution(result['fingerprint'],'fictional-browser',30).data['run_id']
            except WorkflowError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda unused:start(),range(2)))
        self.assertEqual(sum(x is not None for x in results),1)

    def test_multiple_entries_are_sequential_and_budget_prevents_extra_disclosure(self):
        from pathlib import Path
        from test_documents import fake_render
        for limit in [1,2]:
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
            plan=self.plan();plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30}
            plan['submission_limit']=limit
            entry=copy.deepcopy(plan['entries'][0]);entry.update(job_id=second,render_id=render['render_id'],destination='https://apply.example.test/form/FICT-SECOND')
            plan['entries'].append(entry)
            result=self.work.create_manifest(plan).data;self.approve(result)
            run=self.work.start_execution(result['fingerprint'],'fictional-browser',30).data['run_id']
            seen=[]
            while True:
                out=self.work.next_action(run)
                if 'request' not in out.data:break
                request=out.data['request'];seen.append((request['job_id'],request['action']))
                self.entry=next(e for e in result['manifest']['entries'] if e['job_id']==request['job_id'])
                self.work.record_action(run,self.receipt(request))
            self.assertEqual(sum(a=='submit' for j,a in seen),limit)
            self.assertEqual(len(seen),6*limit)
            if limit==1:
                self.assertEqual(out.data['state'],'completed_limit')
                # Keep this test's next independent fixture on a fresh private ledger.
                self.tearDown();self.setUp()
            else:self.assertEqual(out.data['state'],'completed')
