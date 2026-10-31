"""Fictional evidence gaps stay separate from skills, CV facts and authority."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from core import career_growth as growth
from core.execution import Executor
from core.workflow import WorkflowError
from scripts.demo_slice1 import demo

ROOT = Path(__file__).resolve().parents[1]


class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Executor(Path(self.tmp.name)/'private')
        demo(self.work.data_dir)
        self.add_job('fictional-growth-1', 'Embeddings')

    def add_job(self, key, value):
        job = json.loads((ROOT/'examples/fictional/job.json').read_text())
        job.update(platform_job_id=key, req_id=key, title='Fictional Junior AI Engineer',
                   url='https://jobs.example.invalid/'+key)
        job['requirements'] += [
            {'id':'R3','text':value+' project practice','field':'skill','value':value,'mandatory':True,'hard':False},
            {'id':'R4','text':'Work authorization must be clarified','field':'work_authorization','value':'local','mandatory':True,'hard':True}]
        jid = self.work.import_job(job).data['job']['id']
        matrix = json.loads((ROOT/'examples/fictional/matrix.json').read_text())
        matrix['rows'][1].update(match='partial', reason='Classroom work only; professional use unestablished.')
        matrix['rows'] += [dict(requirement_id='R3',match='missing',fact_ids=[],reason='No reviewed practice evidence.'),
                           dict(requirement_id='R4',match='unknown',fact_ids=[],reason='Candidate has not answered.')]
        self.work.assess(jid, matrix)
        return jid, matrix

    def proposal(self, jid=2):
        context = growth.gap_context(self.work,[jid]).data
        return {'schema_version':'1.0','job_ids':[jid],'context_fingerprint':context['context_fingerprint'],
                'author':'fictional-author','actions':[
                    {'id':'A'+str(i),'gap_id':g['id'],'kind':'clarify' if g['route']=='clarify' else 'build',
                     'objective':'Future task for '+g['value'],'steps':['Do not claim completion.'],
                     'acceptance_checks':['Collect source-backed, candidate-reviewed evidence.'],'resources':[]}
                    for i,g in enumerate(context['gaps'],1)]}

    def reviewed(self,jid=2):
        plan = growth.import_plan(self.work,self.proposal(jid)).data
        review = {'schema_version':'1.0','plan_fingerprint':plan['plan_fingerprint'],
                  'reviewer':'fictional-reviewer','independent':True,'decision':'approved',
                  'findings':[{'action_id':a['id'],'grounded':True,'feasible':True,'future_only':True,
                               'no_cv_promotion':True,'reason':'Fictional review; proposed work is not a fact.'}
                              for a in self.proposal(jid)['actions']]}
        growth.review_plan(self.work,plan['plan_fingerprint'],review)
        return plan['plan_fingerprint']

    def test_context_collects_gaps_but_not_proven_absence_or_new_facts(self):
        before = self.work.confirmed_profile()['fingerprint']
        a = growth.gap_context(self.work,[2]).data
        self.assertEqual(a,growth.gap_context(self.work,[2]).data)
        self.assertEqual(3,len(a['gaps']))
        unknown = next(g for g in a['gaps'] if g['value']=='local')
        self.assertEqual('clarify',unknown['route'])
        self.assertEqual('unknown',unknown['occurrences'][0]['match'])
        partial = next(g for g in a['gaps'] if g['value']=='requirements')
        self.assertIn('Classroom',partial['occurrences'][0]['reason'])
        self.assertFalse(a['authority_granted'])
        self.assertFalse(a['knowledge_absence_verified'])
        self.assertEqual(before,self.work.confirmed_profile()['fingerprint'])
        self.assertEqual('sqlite-fts5-bm25',a['related_evidence']['backend'])

    def test_stale_reassessment_and_source_changes_invalidate_plan(self):
        plan = growth.import_plan(self.work,self.proposal()).data
        _,matrix = self.add_job('fictional-growth-1','Embeddings')
        matrix['rows'][1]['reason']='A different current limitation.'
        self.work.assess(2,matrix)
        with self.assertRaises(WorkflowError): growth.check_plan(self.work,plan['plan_fingerprint'])
        source=self.work.confirmed_profile()['sources'][0]
        self.work.inside(source['path']).write_text('changed fictional source',encoding='utf8')
        with self.assertRaises(WorkflowError): growth.gap_context(self.work,[2])

    def test_unknown_and_eligibility_cannot_be_courses_or_invented_completion(self):
        packet=self.proposal()
        context=growth.gap_context(self.work,[2]).data
        gap=next(g for g in context['gaps'] if g['route']=='clarify')
        action=next(a for a in packet['actions'] if a['gap_id']==gap['id'])
        action['kind']='build'
        with self.assertRaises(ValueError): growth.import_plan(self.work,packet)
        packet=self.proposal();packet['completed']=True
        with self.assertRaises(ValueError): growth.import_plan(self.work,packet)
        for bad in ([True],[2,2],[],[999],list(range(1,102))):
            with self.assertRaises((ValueError,WorkflowError,KeyError)): growth.gap_context(self.work,bad)

    def test_unreviewed_plan_cannot_export_and_reviewer_must_differ(self):
        proposal=self.proposal();plan=growth.import_plan(self.work,proposal).data
        with self.assertRaises(WorkflowError): growth.export_reviewed(self.work,[plan['plan_fingerprint']],'datasets/no-review')
        review={'schema_version':'1.0','plan_fingerprint':plan['plan_fingerprint'],
                'reviewer':'fictional-author','independent':True,'decision':'approved','findings':[]}
        with self.assertRaises(ValueError): growth.review_plan(self.work,plan['plan_fingerprint'],review)
        self.assertFalse(self.work.inside('datasets/no-review').exists())

    def test_reviewed_export_split_and_tampering_and_trainer_task(self):
        one=self.reviewed()
        second,_=self.add_job('fictional-growth-2','Vector search')
        two=self.reviewed(second)
        result=growth.export_reviewed(self.work,[one,two],'datasets/growth').data
        self.assertTrue(result['ready_for_split'])
        self.assertFalse(result['training_performed'])
        self.assertEqual('career-growth',growth.check_export(self.work,'datasets/growth').data['task'])
        from adapters.local_finetuning import prepare
        model=Path(self.tmp.name)/'local-model';model.mkdir();(model/'config.json').write_text('{}')
        _,target,rows,_=prepare(self.work,'datasets/growth',model,'training/growth',task='career-growth')
        self.assertFalse(target.exists())
        self.assertEqual(1,len(rows['train']))
        with self.assertRaises(WorkflowError): prepare(self.work,'datasets/growth',model,'training/wrong')
        path=self.work.inside('datasets/growth/train.jsonl');path.write_text('{}\n')
        with self.assertRaises(ValueError): growth.check_export(self.work,'datasets/growth')

    def test_evidence_is_only_a_proposal_and_cannot_escape_workspace(self):
        fingerprint=self.reviewed();before=self.work.confirmed_profile()['fingerprint']
        artifact=self.work.atomic_text('projects/fictional-demo.md','Fictional implementation notes; no actual person.')
        result=growth.record_evidence(self.work,fingerprint,'A1',str(artifact),'Candidate review required.').data
        self.assertFalse(result['cv_eligible'])
        self.assertEqual('submitted_for_candidate_review',result['status'])
        self.assertEqual(before,self.work.confirmed_profile()['fingerprint'])
        with self.assertRaises(ValueError): growth.record_evidence(self.work,fingerprint,'A1','../escape','test')
        with self.assertRaises(ValueError): growth.record_evidence(self.work,fingerprint,'unknown',str(artifact),'test')

    def test_capture_is_idempotent_and_does_not_change_job_or_profile(self):
        before=self.work.get_job(2)
        one=growth.capture(self.work,[2]).data
        two=growth.capture(self.work,[2]).data
        self.assertEqual(one,two)
        self.assertEqual(before,self.work.get_job(2))
        self.assertTrue(self.work.inside(one['path']).is_file())
        other=Executor(Path(self.tmp.name)/'other');demo(other.data_dir,candidate='b')
        with self.assertRaises((ValueError,WorkflowError,OSError)):
            growth.check_plan(other,self.reviewed())

    def test_closed_or_submitted_jobs_can_still_inform_learning(self):
        with self.work._db() as db:
            db.execute("UPDATE jobs SET state='confirmed_submitted' WHERE id=2")
        self.assertEqual(3,len(growth.gap_context(self.work,[2]).data['gaps']))

    def test_missing_work_permit_is_clarification_not_a_project(self):
        source=json.loads((ROOT/'examples/fictional/job.json').read_text())
        source.update(platform_job_id='work-permit',req_id='work-permit')
        source['requirements']=[{'id':'R1','text':'Valid work permit','field':'work_permit',
                                 'value':'required','mandatory':True,'hard':True}]
        jid=self.work.import_job(source).data['job']['id']
        self.work.assess(jid,{'schema_version':'1.0','rows':[{
            'requirement_id':'R1','match':'missing','fact_ids':[],'reason':'No confirmed eligibility answer.'}]})
        context=growth.gap_context(self.work,[jid]).data
        self.assertEqual('clarify',context['gaps'][0]['route'])
        for field in ['work permit','remote_eligibility','licence','employment-type']:
            self.assertEqual('condition',growth._category(field))

    def test_oversized_plan_is_refused_before_it_becomes_unreadable(self):
        packet=self.proposal();action=next(a for a in packet['actions'] if a['kind']=='build')
        packet['actions']=[]
        for i in range(13):
            copy=deepcopy(action);copy['id']='L'+str(i)
            copy['steps']=[str(n)+'x'*3990 for n in range(20)]
            copy['acceptance_checks']=[str(n)+'y'*3990 for n in range(20)]
            packet['actions'].append(copy)
        with self.assertRaisesRegex(WorkflowError,'2 MB'):
            growth.import_plan(self.work,packet)
        self.assertFalse(self.work.inside('reports/growth/plans').exists())

    def test_oversized_tampered_export_uses_a_bounded_read(self):
        one=self.reviewed();jid,_=self.add_job('other-growth','Vector search');two=self.reviewed(jid)
        growth.export_reviewed(self.work,[one,two],'datasets/size-check')
        path=self.work.inside('datasets/size-check/train.jsonl')
        with path.open('wb') as stream: stream.seek(21_000_000);stream.write(b'x')
        with self.assertRaisesRegex(WorkflowError,'bounded read'):
            growth.check_export(self.work,'datasets/size-check')

    def test_overlapping_job_groups_cannot_leak_across_split(self):
        examples=[{'example_id':str(i),'output_hash':str(i),
                   'provenance':{'job_groups':jobs}} for i,jobs in enumerate([['a'],['a','b'],['b'],['c']])]
        train,evaluation,count=growth._split(examples)
        self.assertEqual(2,count)
        left={j for e in train for j in e['provenance']['job_groups']}
        right={j for e in evaluation for j in e['provenance']['job_groups']}
        self.assertFalse(left&right)


if __name__=='__main__': unittest.main()
