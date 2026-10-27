from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

from core.execution import Executor
from core.workflow import WorkflowError
from core.contracts import ContractError
import test_manifests as manifest_fixtures
import test_execution as execution_fixtures


class AuthorizationTests(unittest.TestCase):
    tearDown = manifest_fixtures.ManifestTests.tearDown
    plan = manifest_fixtures.ManifestTests.plan
    receipt = execution_fixtures.ExecutionTests.receipt
    step = execution_fixtures.ExecutionTests.step
    until_submit = execution_fixtures.ExecutionTests.until_submit

    def setUp(self):
        manifest_fixtures.ManifestTests.setUp(self)
        self.work = Executor(self.root)
        self.work.init()

    def scope(self):
        entry = self.plan()['entries'][0]
        return {'schema_version':'1.0', 'authorization_id':'fictional-standing',
            'expires_utc':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
            'submission_limit':2, 'bridge_id':'fictional-browser', 'runtime_minutes':30,
            'targets':[{'employer':self.work.get_job(1)['employer'],
                'destination_prefix':'https://apply.example.test/form/',
                'operations':entry['operations'], 'answers':entry['answers'],
                'consents':entry['consents']}]}

    def authorize(self, scope=None):
        result = self.work.create_authorization(scope or self.scope()).data
        proof = self.root/'standing-proof.txt'
        proof.write_text('APPROVE AUTHORIZATION '+result['fingerprint'],encoding='utf8')
        self.work.approve_authorization(result['fingerprint'],proof)
        return result['fingerprint']

    def manifest(self, change=None):
        plan=self.plan()
        plan['execution']={'bridge_id':'fictional-browser','runtime_minutes':30}
        if change:change(plan)
        result=self.work.create_manifest(plan).data
        self.entry=result['manifest']['entries'][0]
        self.fingerprint=result['fingerprint']
        return self.fingerprint

    def test_approved_scope_derives_exact_manifest_and_completes_without_second_proof(self):
        grant=self.authorize();fingerprint=self.manifest()
        result=self.work.authorize_manifest(fingerprint,grant)
        self.assertEqual(result.data['approval_basis'],'standing_authorization')
        run=self.work.start_execution(fingerprint,'fictional-browser',30).data['run_id']
        for phase in ['inspect','fill','upload','review','submit','verify']:
            self.assertEqual(self.step(run)['action'],phase)
        self.assertEqual(self.work.next_action(run).data['state'],'completed')
        self.assertEqual(self.work.tracker().data['observed_submissions'],1)

    def test_creation_alone_and_arbitrary_yes_do_not_authorize(self):
        grant=self.work.create_authorization(self.scope()).data['fingerprint']
        child=self.manifest()
        with self.assertRaises(WorkflowError):self.work.authorize_manifest(child,grant)
        proof=self.root/'proof.txt';proof.write_text('always approve',encoding='utf8')
        with self.assertRaises(WorkflowError):self.work.approve_authorization(grant,proof)

    def test_assist_cannot_bypass_global_budget_with_zero_allocations(self):
        grant=self.authorize()
        child=self.manifest(lambda p:(p.update(mode='ASSIST',submission_limit=0),p['entries'][0].update(operations=['fill','upload'])))
        with self.assertRaises(WorkflowError):self.work.authorize_manifest(child,grant)

    def test_scope_creation_is_idempotent_without_reapproving_or_reviving_revocation(self):
        scope=self.scope();grant=self.authorize(scope)
        self.assertTrue(self.work.create_authorization(scope).data['approved'])
        self.work.revoke_authorization(grant,'Fictional stop')
        self.assertFalse(self.work.create_authorization(scope).data['approved'])
        proof=self.root/'standing-proof.txt'
        with self.assertRaises(WorkflowError):self.work.approve_authorization(grant,proof)

    def test_new_recipient_answer_consent_or_bridge_is_outside_scope(self):
        grant=self.authorize()
        changes=[lambda p:p['entries'][0].update(destination='https://other.example.test/form/1',policy={**p['entries'][0]['policy'],'source':'https://other.example.test/terms'}),
            lambda p:p['entries'][0]['answers']['salary'].update(value='New answer'),
            lambda p:p['entries'][0]['consents'][0].update(text='New terms'),
            lambda p:p['execution'].update(bridge_id='different-browser')]
        for change in changes:
            with self.subTest(change=change):
                child=self.manifest(change)
                with self.assertRaises(WorkflowError):self.work.authorize_manifest(child,grant)

    def test_allocation_is_global_idempotent_and_never_refunded_by_revocation(self):
        scope=self.scope();scope['submission_limit']=1;grant=self.authorize(scope)
        child=self.manifest();self.work.authorize_manifest(child,grant)
        self.work.authorize_manifest(child,grant)
        self.work.revoke_manifest(child,'Fictional cancellation')
        other=self.manifest(lambda p:p.update(expires_utc=(datetime.now(timezone.utc)+timedelta(hours=3)).isoformat()))
        with self.assertRaises(WorkflowError):self.work.authorize_manifest(other,grant)

    def test_revocation_blocks_an_already_issued_submit_but_allows_read_only_recovery(self):
        grant=self.authorize();child=self.manifest();self.work.authorize_manifest(child,grant)
        run=self.work.start_execution(child,'fictional-browser',30).data['run_id']
        submit=self.until_submit(run)
        self.work.revoke_authorization(grant,'Candidate revoked standing scope')
        with self.assertRaises(WorkflowError):self.work.check_action(run,submit['request_id'])
        recovery=self.work.next_action(run).data['request']
        self.assertEqual(recovery['action'],'verify')

    def test_expiry_and_review_file_tampering_block(self):
        grant=self.authorize();child=self.manifest();self.work.authorize_manifest(child,grant)
        with patch('core.authorization.now_utc',return_value=datetime.now(timezone.utc)+timedelta(days=2)):
            with self.assertRaises(WorkflowError):self.work.check_manifest(child)
        exported=self.root/'authorizations'/f'{grant}.json'
        exported.write_text('{}',encoding='utf8')
        with self.assertRaises(WorkflowError):self.work.check_manifest(child)

    def test_stretch_fit_is_not_auto_approved(self):
        grant=self.authorize();child=self.manifest()
        original=self.work.current_draft
        with patch.object(self.work,'current_draft',side_effect=lambda j:{**original(j),'classification':'Stretch'}):
            with self.assertRaises(WorkflowError):self.work.authorize_manifest(child,grant)

    def test_unsafe_prefixes_are_rejected(self):
        for prefix in ['https://apply.example.test/form','https://*.example.test/',
                       'https://apply.example.test/form/../','https://apply.example.test/form/%2f/']:
            with self.subTest(prefix=prefix):
                scope=self.scope();scope['targets'][0]['destination_prefix']=prefix
                with self.assertRaises((ContractError,WorkflowError,ValueError)):
                    self.work.create_authorization(scope)

    def test_profile_drift_and_different_owner_invalidate_delegation(self):
        grant=self.authorize();child=self.manifest();self.work.authorize_manifest(child,grant)
        with self.assertRaises(WorkflowError):Executor(self.root,actor='other-owner').check_manifest(child)
        profile=self.work.inspect_profile().data['profile']
        profile['preferences']['availability']='Changed fictional start'
        self.work.import_profile(profile)
        with self.assertRaises(WorkflowError):self.work.check_manifest(child)

    def test_standing_scope_does_not_clear_host_action_time_blockers(self):
        grant=self.authorize();child=self.manifest();self.work.authorize_manifest(child,grant)
        run=self.work.start_execution(child,'fictional-browser',30).data['run_id']
        action=self.work.next_action(run).data['request'];receipt=self.receipt(action)
        receipt['form']['blockers']=['host_action_time_confirmation_required']
        with self.assertRaises(WorkflowError):self.work.record_action(run,receipt)

    def test_path_query_and_encoded_traversal_do_not_expand_a_recipient(self):
        grant=self.authorize()
        for url in ['https://apply.example.test/formevil/FICT-1',
                    'https://apply.example.test/form/FICT-1?company=Other',
                    'https://apply.example.test/form/%2e%2e/other']:
            with self.subTest(url=url):
                child=self.manifest(lambda p:p['entries'][0].update(destination=url))
                with self.assertRaises((WorkflowError,ContractError)):
                    self.work.authorize_manifest(child,grant)

    def test_two_coordinators_cannot_allocate_the_same_last_slot(self):
        from concurrent.futures import ThreadPoolExecutor
        scope=self.scope();scope['submission_limit']=1;grant=self.authorize(scope)
        children=[self.manifest(),self.manifest(lambda p:p.update(expires_utc=(datetime.now(timezone.utc)+timedelta(hours=3)).isoformat()))]
        def allocate(child):
            try:Executor(self.root).authorize_manifest(child,grant);return True
            except WorkflowError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(allocate,children))
        self.assertEqual(outcomes.count(True),1)
        self.assertEqual(self.work.check_authorization(grant).data['remaining_unallocated'],0)

    def test_real_cli_standing_authorization_and_revocation(self):
        import subprocess,sys
        from pathlib import Path
        def cli(*args,code=0):
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/kit.py'),
                '--data-dir',str(self.root),*args],capture_output=True,encoding='utf8',timeout=15)
            self.assertEqual(result.returncode,code,result.stdout+result.stderr)
            return json.loads(result.stdout)['data']
        plan=self.root/'standing-plan.json';plan.write_text(json.dumps(self.scope()),encoding='utf8')
        grant=cli('create-authorization','--plan',str(plan))['fingerprint']
        proof=self.root/'proof.txt';proof.write_text('APPROVE AUTHORIZATION '+grant,encoding='utf8')
        cli('approve-authorization','--fingerprint',grant,'--confirmation',str(proof))
        child=self.manifest();cli('authorize-manifest','--fingerprint',child,'--authorization',grant)
        self.assertEqual(cli('check-authorization','--fingerprint',grant)['allocated_submissions'],1)
        cli('revoke-authorization','--fingerprint',grant,'--reason','Fictional stop')
        cli('check-manifest','--fingerprint',child,code=2)

    def test_expiry_during_profile_validation_blocks_the_authority_check(self):
        grant=self.authorize()
        now=datetime.now(timezone.utc)
        with patch('core.authorization.now_utc',side_effect=[now,now+timedelta(days=2)]):
            with self.assertRaises(WorkflowError):self.work.check_authorization(grant)

    def test_future_workspace_schema_is_rejected_before_creating_authority(self):
        with self.work._db() as db:db.execute('PRAGMA user_version=999')
        with self.assertRaises(WorkflowError):self.work.create_authorization(self.scope())
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM campaign_authorizations').fetchone()[0],0)

    def test_latest_assessment_downgrade_blocks_an_issued_action_despite_old_reviewed_draft(self):
        from pathlib import Path
        grant=self.authorize();child=self.manifest();self.work.authorize_manifest(child,grant)
        run=self.work.start_execution(child,'fictional-browser',30).data['run_id']
        action=self.work.next_action(run).data['request']
        matrix=json.loads((Path(__file__).resolve().parents[1]/'examples/fictional/matrix.json').read_text(encoding='utf8'))
        matrix['rows'][0].update(match='partial',reason='Updated review: project evidence only partially covers the requirement')
        self.assertEqual(self.work.assess(1,matrix).data['classification'],'Stretch')
        with self.assertRaises(WorkflowError):self.work.check_action(run,action['request_id'])
        with self.assertRaises(WorkflowError):self.work.authorize_manifest(child,grant)
