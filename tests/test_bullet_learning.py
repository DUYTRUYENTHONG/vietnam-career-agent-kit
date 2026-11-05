"""Fictional reviewed bullet exports retain scope and current evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import ModuleType
from unittest.mock import patch

from adapters.local_finetuning import validate_dataset
from core.learning import export_reviewed, check_export
from core.ledger import canonical_hash
from core.workflow import WorkflowError
from scripts.demo_wording import seed, fictional_review


class BulletLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.work, self.model = seed(Path(self.tmp.name)/'private')

    def reviewed(self):
        self.work.import_wording(1,self.model)
        self.work.review_wording(1,fictional_review(self.work.wording_packet(1).data))

    def export(self, path='datasets/bullets'):
        return export_reviewed(self.work,[1],path,task='cv-bullet-wording').data

    def second_job(self, same_employer=False, same_text=False):
        job=json.loads((Path(__file__).resolve().parents[1]/'examples/fictional/job.json').read_text(encoding='utf8'))
        job.update(platform_job_id='bullet-second',req_id='BULLET-SECOND',
            employer=self.work.get_job(1)['employer'] if same_employer else 'Other Fictional Cooperative',
            url='https://jobs.example.invalid/bullet-second',
            requirements=[{'id':'R1','text':'SQL project experience','field':'skill','value':'SQL','mandatory':True,'hard':False},
                          {'id':'R2','text':'Relevant certification preferred','field':'certification','value':'certificate','mandatory':False,'hard':False}])
        self.work.import_job(job)
        self.work.assess(2,{'schema_version':'1.0','rows':[
            {'requirement_id':'R1','match':'direct','fact_ids':['F1'],'reason':'Fictional SQL project.'},
            {'requirement_id':'R2','match':'missing','fact_ids':[],'reason':'No certificate.'}]})
        model=deepcopy(self.model); model['job_id']=2
        if not same_text:
            statement=model['sections'][1]['groups'][0]['statements'][0]
            statement.update(text='Used SQL to query a fictional sales dataset.',transformation='faithful_paraphrase')
        self.work.import_wording(2,model)
        self.work.review_wording(2,fictional_review(self.work.wording_packet(2).data))

    def test_selects_one_mapped_statement_with_its_original_context(self):
        self.reviewed(); before=self.work.db_path.read_bytes()
        result=self.export(); self.assertEqual(1,result['example_count'])
        folder=self.work.inside('datasets/bullets')
        example=json.loads((folder/'examples.jsonl').read_text(encoding='utf8'))
        inputs=json.loads(example['messages'][1]['content'])
        target=json.loads(example['messages'][2]['content'])
        statement=self.model['sections'][1]['groups'][0]['statements'][0]
        self.assertEqual({'language':'en','section_kind':'projects','context_fact_id':'P0','statement':statement},target)
        self.assertEqual({'P0','F1'},{f['id'] for f in inputs['facts']})
        self.assertEqual(['R1'],[r['id'] for r in inputs['requirements']])
        self.assertEqual([{'requirement_id':'R1','match':'direct','fact_ids':['F1']}],inputs['assessed_evidence'])
        self.assertNotIn('statement',inputs); self.assertNotIn('sections',inputs)
        self.assertNotIn('contacts',inputs); self.assertNotIn('reviewer',inputs)
        self.assertEqual('pending',target['statement']['review_status'])
        self.assertEqual('P0',inputs['context_fact_id'])
        self.assertEqual('F1',inputs['statement_fact_id'])
        canonical=json.loads((Path(__file__).resolve().parents[1]/'schemas/cv-content-v2.schema.json').read_text(encoding='utf8'))
        self.assertEqual(canonical['$defs']['statement'],inputs['output_schema']['$defs']['statement'])
        self.assertFalse(result['ready_for_split'])
        self.assertTrue(check_export(self.work,'datasets/bullets').data['current_evidence_checked'])
        self.assertEqual(before,self.work.db_path.read_bytes())

    def test_missing_or_revoked_review_never_exports(self):
        self.work.import_wording(1,self.model)
        with self.assertRaises(WorkflowError):self.export()
        self.assertFalse(self.work.inside('datasets/bullets').exists())
        self.work.review_wording(1,fictional_review(self.work.wording_packet(1).data))
        self.export(); self.work.reject_wording(1,'Fictional correction')
        with self.assertRaises(WorkflowError):check_export(self.work,'datasets/bullets')

    def test_rehashed_target_edit_is_not_a_reviewed_label(self):
        self.reviewed(); self.export(); folder=self.work.inside('datasets/bullets')
        path=folder/'examples.jsonl'; row=json.loads(path.read_text(encoding='utf8'))
        target=json.loads(row['messages'][2]['content'])
        target['statement']['text']='Invented fictional production deployment.'
        row['messages'][2]['content']=json.dumps(target)
        path.write_text(json.dumps(row)+'\n',encoding='utf8')
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
        manifest['files']['examples.jsonl']=hashlib.sha256(path.read_bytes()).hexdigest()
        manifest['manifest_fingerprint']=canonical_hash({k:v for k,v in manifest.items() if k!='manifest_fingerprint'})
        (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf8')
        with self.assertRaises(WorkflowError):check_export(self.work,'datasets/bullets')

    def test_explicit_task_is_required_by_the_local_trainer(self):
        self.reviewed(); self.export()
        self.assertTrue(validate_dataset(self.work,'datasets/bullets','cv-bullet-wording').data['current_evidence_checked'])
        for other in ('cv-wording','cv-review'):
            with self.assertRaises(WorkflowError):validate_dataset(self.work,'datasets/bullets',other)

    def test_bounds_private_output_and_overwrite_are_not_silently_relaxed(self):
        self.reviewed(); self.export()
        with self.assertRaises(WorkflowError):self.export()
        for ids,path in [([], 'datasets/a'),([True],'datasets/b'),([1,1],'datasets/c'),([1],'../outside')]:
            with self.assertRaises((ValueError,WorkflowError)):
                export_reviewed(self.work,ids,path,task='cv-bullet-wording')

    def test_grouping_is_transitive_across_employer_and_normalized_text(self):
        from core.bullet_learning import split_bullets
        rows=[{'example_id':str(i),'group_id':employer,'duplicate_text_hash':text}
              for i,(employer,text) in enumerate([('a','1'),('a','2'),('b','2'),('c','3'),('d','4')])]
        train,evaluation,groups=split_bullets(rows)
        self.assertEqual(3,groups); self.assertTrue(train and evaluation)
        self.assertFalse({x['group_id'] for x in train}&{x['group_id'] for x in evaluation})
        self.assertFalse({x['duplicate_text_hash'] for x in train}&{x['duplicate_text_hash'] for x in evaluation})
        self.assertEqual((train,evaluation,groups),split_bullets(deepcopy(rows)))

    def test_cli_can_export_the_explicit_task_and_check_its_manifest(self):
        self.reviewed()
        result=subprocess.run([sys.executable,'scripts/kit.py','--data-dir',str(self.work.data_dir),
            'learning-export','--job-id','1','--output','datasets/cli','--task','cv-bullet-wording'],capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertEqual(1,json.loads(result.stdout)['data']['example_count'])
        self.assertTrue(check_export(self.work,'datasets/cli',task='cv-bullet-wording').data['current_evidence_checked'])

    def test_two_employers_split_and_report_reused_context_facts(self):
        from adapters.local_finetuning import prepare
        self.reviewed(); self.second_job()
        result=export_reviewed(self.work,[1,2],'datasets/two',task='cv-bullet-wording').data
        self.assertTrue(result['ready_for_split']);self.assertEqual(2,result['example_count'])
        self.assertEqual(2,result['split_overlap']['shared_fact_count'])
        self.assertFalse(result['split_overlap']['semantic_independence_verified'])
        self.assertTrue(check_export(self.work,'datasets/two').data['current_evidence_checked'])
        model=Path(self.tmp.name)/'model';model.mkdir();(model/'config.json').write_text('{}')
        _,target,rows,_=prepare(self.work,'datasets/two',model,'training/bullets',task='cv-bullet-wording')
        self.assertEqual((1,1),(len(rows['train']),len(rows['evaluation'])))
        self.assertFalse(target.exists())  # Preparation loads no weights or SDK.

    def test_same_employer_or_duplicate_text_never_creates_a_false_holdout(self):
        self.reviewed();self.second_job(same_employer=True)
        result=export_reviewed(self.work,[1,2],'datasets/same-employer',task='cv-bullet-wording').data
        self.assertFalse(result['ready_for_split'])
        # A separate fixture tests identical wording across different employers.
        work,model=seed(Path(self.tmp.name)/'other-private')
        self.work,self.model=work,model;self.reviewed();self.second_job(same_text=True)
        result=export_reviewed(work,[1,2],'datasets/same-text',task='cv-bullet-wording').data
        self.assertFalse(result['ready_for_split'])

    def test_unmapped_statements_and_small_limits_fail_before_any_export(self):
        self.model['sections'][1]['groups'][0]['statements'][0]['requirement_ids']=[]
        self.reviewed()
        with self.assertRaisesRegex(WorkflowError,'No reviewed statements'):self.export()
        self.assertFalse(self.work.inside('datasets/bullets').exists())
        self.model['sections'][1]['groups'][0]['statements'][0]['requirement_ids']=['R1']
        self.reviewed()
        for name,value in [('MAX_EXAMPLES',0),('MAX_BYTES',10)]:
            with patch('core.bullet_learning.'+name,value):
                with self.assertRaises(WorkflowError):self.export()
            self.assertFalse(self.work.inside('datasets/bullets').exists())

    def test_changed_source_or_missing_artifact_never_remains_current(self):
        self.reviewed();self.export()
        path=self.work.inside('datasets/bullets/examples.jsonl');raw=path.read_bytes();path.unlink()
        with self.assertRaises(WorkflowError):check_export(self.work,'datasets/bullets')
        path.write_bytes(raw)
        source=self.work.inside('inputs/fictional-cv.md')
        source.write_text(source.read_text(encoding='utf8')+'\nFictional source amendment.',encoding='utf8')
        # Imported evidence is an immutable copy; changing staging input is not a source change.
        self.assertTrue(check_export(self.work,'datasets/bullets').data['current_evidence_checked'])
        source=self.work.inside(self.work.wording_packet(1).data['source_records'][0]['path'])
        source.write_text(source.read_text(encoding='utf8')+'\nChanged canonical fictional bytes.',encoding='utf8')
        with self.assertRaises(WorkflowError):check_export(self.work,'datasets/bullets')

    def test_full_cv_evaluation_and_pair_generation_reject_bullet_task_early(self):
        from core.wording_evaluation import compare
        from adapters.local_pair_generation import run
        self.reviewed();self.export()
        with self.assertRaisesRegex(ValueError,'full-CV'):compare(self.work,'datasets/bullets',{})
        with self.assertRaisesRegex(ValueError,'full-CV'):
            run(self.work,'datasets/bullets','missing-model','training/missing','evaluations/not-created')
        self.assertFalse(self.work.inside('evaluations/not-created').exists())

    def test_mcp_uses_the_same_current_review_and_export_path(self):
        class FakeMCP:
            def __init__(self,*a,**k):self.tools={}
            def tool(self,**kw):
                def register(f):self.tools[f.__name__]=(f,kw['annotations']);return f
                return register
            def resource(self,*a):return lambda f:f
        module=ModuleType('mcp.server.fastmcp');module.FastMCP=FakeMCP
        with patch.dict(sys.modules,{'mcp':ModuleType('mcp'),'mcp.server':ModuleType('mcp.server'),'mcp.server.fastmcp':module}):
            from adapters.career_mcp import make_career_server
            server=make_career_server(self.work)
            export,annotation=server.tools['learning_export']
            self.assertFalse(annotation['readOnlyHint'])
            self.assertNotEqual('ok',export([1],'datasets/mcp','cv-bullet-wording')['outcome'])
            self.reviewed()
            self.assertEqual('ok',export([1],'datasets/mcp','cv-bullet-wording')['outcome'])
            check,annotation=server.tools['learning_check'];self.assertTrue(annotation['readOnlyHint'])
            self.assertEqual('ok',check('datasets/mcp')['outcome'])
