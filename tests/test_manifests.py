import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.manifests import Campaign
from core.workflow import WorkflowError
from core.contracts import ContractError
from scripts.demo_slice1 import demo
from test_documents import fake_render


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'private'
        demo(self.root);self.work=Campaign(self.root);self.work.init()
        with patch('core.documents.render_files',side_effect=fake_render):self.render=self.work.render(1).data
        review={'schema_version':'1.0','render_fingerprint':self.render['fingerprint'],
            'reviewed_pages':[1],'checks':dict.fromkeys(['content','layout','glyphs','language'],True)}
        file=self.root/'review.json';file.write_text(json.dumps(review),encoding='utf8')
        self.work.review_documents(self.render['render_id'],file)

    def tearDown(self):self.tmp.cleanup()

    def plan(self):
        now=datetime.now(timezone.utc)
        return {'schema_version':'1.0','campaign_id':'fictional-campaign','mode':'APPROVED_BATCH',
            'expires_utc':(now+timedelta(hours=2)).isoformat(),'submission_limit':1,
            'entries':[{'job_id':1,'render_id':self.render['render_id'],'format':'pdf',
                'destination':'https://apply.example.test/form/FICT-1','operations':['fill','upload','submit'],
                'answers':{'salary':{'value':'Negotiable','source':'candidate_confirmed','fact_ids':[],'kind':'ordinary'}},
                'required_answers':['salary'],'consents':[{'id':'privacy-v1','text':'Fictional retention policy','choice':True}],
                'policy':{'permission':'permitted','source':'https://apply.example.test/policy',
                    'checked_utc':now.isoformat(),'allowed_operations':['fill','upload','submit']}}]}

    def approve(self,result):
        file=self.root/'approval.txt';file.write_text('APPROVE MANIFEST '+result['fingerprint'],encoding='utf8')
        return self.work.approve_manifest(result['fingerprint'],file)

    def test_exact_expiring_manifest_requires_approval_and_never_enables_execution(self):
        result=self.work.create_manifest(self.plan()).data
        with self.assertRaises(WorkflowError):self.work.check_manifest(result['fingerprint'])
        approved=self.approve(result)
        self.assertTrue(approved.data['approved'])
        self.assertFalse(approved.data['execution_enabled'])
        entry=result['manifest']['entries'][0]
        intent={key:entry[key] for key in ['job_id','destination','document_sha256','answers_sha256','consents_sha256']}
        intent['action']='upload'
        self.assertTrue(self.work.check_manifest(result['fingerprint'],intent).data['approved'])
        for key in ['destination','document_sha256','answers_sha256','consents_sha256']:
            bad={**intent,key:'different'}
            with self.assertRaises(WorkflowError):self.work.check_manifest(result['fingerprint'],bad)
        self.work.revoke_manifest(result['fingerprint'],'Candidate revoked')
        with self.assertRaises(WorkflowError):self.work.check_manifest(result['fingerprint'])

    def test_expired_unknown_salary_manual_policy_and_assist_submit_are_blocked(self):
        invalid=[]
        p=self.plan();p['expires_utc']='2020-01-01T00:00:00Z';invalid.append(p)
        p=self.plan();p['entries'][0]['answers']['salary']['value']=None;invalid.append(p)
        p=self.plan();p['entries'][0]['policy']['permission']='manual';invalid.append(p)
        p=self.plan();p['mode']='ASSIST';p['submission_limit']=0;invalid.append(p)
        p=self.plan();p['entries'][0]['policy']['source']='https://different.example.test/policy';invalid.append(p)
        p=self.plan();p['entries'].append(copy.deepcopy(p['entries'][0]));invalid.append(p)
        p=self.plan();p['submission_limit']=True;invalid.append(p)
        p=self.plan();p['entries'][0]['answers']['salary']['kind']='legal';invalid.append(p)
        for plan in invalid:
            with self.subTest(plan=plan):
                with self.assertRaises((WorkflowError,ContractError)):self.work.create_manifest(plan)

    def test_current_files_profile_job_review_and_expiry_are_rechecked(self):
        result=self.work.create_manifest(self.plan()).data;self.approve(result)
        with patch('core.manifests.now_utc',return_value=datetime.now(timezone.utc)+timedelta(days=2)):
            with self.assertRaises(WorkflowError):self.work.check_manifest(result['fingerprint'])
        (self.root/self.render['files']['pdf']['path']).write_bytes(b'changed')
        with self.assertRaises(WorkflowError):self.work.check_manifest(result['fingerprint'])

    def test_approval_proof_cannot_be_guessed_or_read_from_outside_workspace(self):
        result=self.work.create_manifest(self.plan()).data
        proof=self.root/'approval.txt';proof.write_text('yes',encoding='utf8')
        with self.assertRaises(WorkflowError):self.work.approve_manifest(result['fingerprint'],proof)
        outside=Path(self.tmp.name)/'outside.txt'
        outside.write_text('APPROVE MANIFEST '+result['fingerprint'],encoding='utf8')
        with self.assertRaises(WorkflowError):self.work.approve_manifest(result['fingerprint'],outside)

    def test_material_answer_and_consent_changes_require_new_manifest_and_new_approval(self):
        plan=self.plan();first=self.work.create_manifest(plan).data;self.approve(first)
        plan['entries'][0]['answers']['salary']['value']='Different confirmed answer'
        second=self.work.create_manifest(plan).data
        self.assertNotEqual(first['fingerprint'],second['fingerprint'])
        with self.assertRaises(WorkflowError):self.work.check_manifest(first['fingerprint'])
        with self.assertRaises(WorkflowError):self.work.check_manifest(second['fingerprint'])
        plan['entries'][0]['consents'][0]['choice']=False
        third=self.work.create_manifest(plan).data
        self.assertNotEqual(second['fingerprint'],third['fingerprint'])

    def test_rejected_document_review_invalidates_approval_and_resume_reports_it(self):
        result=self.work.create_manifest(self.plan()).data;self.approve(result)
        self.work.reject_documents(self.render['render_id'],'Fictional layout issue found')
        with self.assertRaises(WorkflowError):self.work.check_manifest(result['fingerprint'])
        self.assertFalse(self.work.resume().data['manifests'][0]['approved'])
