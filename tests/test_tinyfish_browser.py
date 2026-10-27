"""Fictional transport/driver tests; no browser account or paid API."""
import copy
import json
import unittest
from datetime import timedelta
from unittest.mock import patch

import test_parallel_execution as fixtures
from adapters.tinyfish_browser import TinyFishBrowserBridge, BrowserHTTP, preview, destination
from adapters.tinyfish_forms import validate_form
from core.contracts import ContractError
from core.manifests import now_utc
from core.parallel_execution import run_parallel_with_bridge
from core.workflow import WorkflowError


def form(entry):
    return {'schema_version':'1.0','destination':entry['destination'],
        'identity':{key:{'selector':'#'+key,'text':entry[key]} for key in ['employer','requisition']},
        'fields':{'salary':{'selector':'#salary','kind':'text'}},
        'consents':[{'id':'privacy-v1','selector':'#privacy','text_selector':'#privacy-label',
                     'text':'Fictional retention policy','required':True}],
        'upload_selector':'#cv','submit_selector':'#submit','confirmation_selector':'#confirmation',
        'confirmation_text':'Fictional application submitted','blocker_selectors':['#new-terms']}


class BrowserTests(unittest.TestCase):
    setUp=fixtures.ParallelExecutionTests.setUp
    tearDown=fixtures.ParallelExecutionTests.tearDown
    start=fixtures.ParallelExecutionTests.start
    receipt=fixtures.ParallelExecutionTests.receipt
    plan=fixtures.ParallelExecutionTests.plan
    approve=fixtures.ParallelExecutionTests.approve

    def setup_browser(self,count=2):
        run=self.start(count,workers=count,bridge_id='tinyfish-browser')
        forms={str(job):form(entry) for job,entry in self.entries.items()}
        scope={'schema_version':'1.0','provider':'tinyfish-browser','manifest_fingerprint':self.fingerprint,
               'expires_utc':(now_utc()+timedelta(minutes=20)).isoformat(),'max_sessions':count}
        return run,forms,scope

    def bridge(self,run,forms,scope,driver=None):
        test=self;self.transport_calls=[]
        def transport(method,session_id=None,payload=None):
            test.transport_calls.append((method,session_id,payload))
            if method=='POST':
                number=sum(c[0]=='POST' for c in test.transport_calls)
                return {'session_id':f'fixture-{number}','cdp_url':f'wss://fixture.tinyfish.io/cdp/{number}'}
        class Driver:
            def perform(self,session,plan,request,guard):
                guard();result=test.receipt(request)
                for key in ['schema_version','request_id','binding_id']:result.pop(key)
                return result
        return TinyFishBrowserBridge(self.work,run,forms,scope,preview(self.work,run,forms,scope).data['fingerprint'],
                                     transport=transport,driver=driver or Driver())

    def test_two_isolated_sessions_full_protocol_close_after_confirmation(self):
        run,forms,scope=self.setup_browser()
        bridge=self.bridge(run,forms,scope)
        with patch('adapters.tinyfish_browser.public_host'):
            result=run_parallel_with_bridge(self.work,run,bridge)
        self.assertEqual(result.data['state'],'completed',result.json())
        self.assertEqual(len([c for c in self.transport_calls if c[0]=='POST']),2)
        self.assertEqual(len([c for c in self.transport_calls if c[0]=='DELETE']),2)
        self.assertTrue(all(s['closed'] for s in bridge.sessions.values()))
        self.assertEqual(len({s['binding_id'] for s in bridge.sessions.values()}),2)
        for path in bridge.root.glob('*.json'):
            self.assertNotIn('wss://',path.read_text())
        with self.work._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0],2)

    def test_preview_offline_and_scope_mismatch_no_network(self):
        run,forms,scope=self.setup_browser(1)
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
            self.assertEqual(preview(self.work,run,forms,scope).data['network_calls'],0)
            with self.assertRaises(WorkflowError):TinyFishBrowserBridge(self.work,run,forms,scope,'wrong')
        changed=copy.deepcopy(forms);changed['1']['destination']='https://other.example.test/'
        with self.assertRaises(ContractError):preview(self.work,run,changed,scope)

    def test_cli_preview_and_live_without_exact_scope_never_calls_provider(self):
        from scripts.kit import parser,execute
        run,forms,scope=self.setup_browser(1)
        forms_path=self.root/'forms.json';forms_path.write_text(json.dumps(forms),encoding='utf8')
        scope_path=self.root/'scope.json';scope_path.write_text(json.dumps(scope),encoding='utf8')
        args=['--data-dir',str(self.root),'tinyfish-browser','--run-id',run,
              '--forms',str(forms_path),'--cloud-scope',str(scope_path)]
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
            self.assertEqual(execute(parser().parse_args(args)).data['network_calls'],0)
            with self.assertRaises(WorkflowError):execute(parser().parse_args(args+['--live']))

    def test_revoked_authority_stops_before_session_creation(self):
        run,forms,scope=self.setup_browser(1);bridge=self.bridge(run,forms,scope)
        request=self.work.next_parallel_action(run,1).data['request']
        self.work.revoke_manifest(self.fingerprint,'Fictional revoked scope')
        with self.assertRaises(WorkflowError):bridge.perform(request)
        self.assertEqual(self.transport_calls,[])

    def test_replay_and_restart_do_not_allocate_replacement(self):
        run,forms,scope=self.setup_browser(1);bridge=self.bridge(run,forms,scope)
        request=self.work.next_parallel_action(run,1).data['request']
        with patch('adapters.tinyfish_browser.public_host'):
            bridge.perform(request)
            with self.assertRaises(WorkflowError):bridge.perform(request)
        with self.assertRaises(WorkflowError):self.bridge(run,forms,scope)

    def test_driver_cannot_override_receipt_identity(self):
        class BadDriver:
            def perform(self,*args):return {'request_id':'another-request'}
        run,forms,scope=self.setup_browser(1);bridge=self.bridge(run,forms,scope,BadDriver())
        request=self.work.next_parallel_action(run,1).data['request']
        with patch('adapters.tinyfish_browser.public_host'):
            with self.assertRaises(WorkflowError):bridge.perform(request)

    def test_private_and_manual_destinations_rejected(self):
        for url in ['https://localhost/','https://127.0.0.1/','https://169.254.169.254/',
                    'https://linkedin.com/jobs','http://example.com','https://example.com:123/']:
            with self.assertRaises(ContractError):destination(url)

    def test_form_plan_rejects_unknown_keys_and_duplicate_controls(self):
        run,forms,scope=self.setup_browser(1)
        bad=copy.deepcopy(forms['1']);bad['auto_approve']=True
        with self.assertRaises(ContractError):validate_form(bad)
        bad=copy.deepcopy(forms['1']);bad['upload_selector']=bad['submit_selector']
        with self.assertRaises(ContractError):validate_form(bad)

    def test_transport_secret_redaction_and_no_retry(self):
        with patch('adapters.tinyfish_browser.build_opener') as opener:
            opener.return_value.open.side_effect=RuntimeError('secret-value')
            with self.assertRaises(WorkflowError) as error:BrowserHTTP('secret-value')('POST',payload={})
            self.assertNotIn('secret-value',str(error.exception))
            self.assertEqual(opener.return_value.open.call_count,1)
            args,kwargs=opener.return_value.open.call_args
            self.assertEqual(args[0].full_url,'https://api.browser.tinyfish.ai')
            self.assertEqual(kwargs['timeout'],60)
