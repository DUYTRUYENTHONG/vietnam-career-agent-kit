from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from core.workflow import WorkflowError
from scripts.demo_wording import seed


class QualityCorpusTests(unittest.TestCase):
    def test_frozen_cohort_duplicates_closed_unknown_and_mandatory_gaps(self):
        corpus = json.loads((Path(__file__).resolve().parents[1]/'examples/fictional/quality-corpus.json').read_text(encoding='utf8'))
        self.assertEqual(12, len(corpus['cases']))
        self.assertEqual({'data','technical','commercial'}, {c['candidate'] for c in corpus['cases']})
        self.assertEqual(6, sum(c['split']=='held_out' for c in corpus['cases']))
        with tempfile.TemporaryDirectory() as temp:
            for candidate in ['data', 'technical', 'commercial']:
                work, model = seed(Path(temp)/candidate, candidate)
                base, _ = work.job_document(1)
                identities = {}
                for case in [c for c in corpus['cases'] if c['candidate']==candidate]:
                    job = deepcopy(base)
                    identity = case['duplicate_of'] or case['id']
                    job.update(platform_job_id=identity, req_id=identity,
                        url='https://jobs.example.test/'+identity, title=case['title'],
                        raw_jd=case['raw_jd'], liveness=case['liveness'], city=case['city'],
                        document_language=case['language'], work_model=case.get('work_model','hybrid'))
                    job['requirements'][1].update(mandatory=case['mandatory_certificate'], hard=case['mandatory_certificate'])
                    job_id = work.import_job(job).data['job']['id']
                    if case['duplicate_of']:
                        self.assertEqual(identities[case['duplicate_of']], job_id)
                    identities[case['id']] = job_id
                    assessment = work.assess(job_id, {'schema_version':'1.0','rows':[
                        {'requirement_id':'R1','match':'direct','fact_ids':['F1'],'reason':'Exact project skill, with qualifiers.'},
                        {'requirement_id':'R2','match':'missing','fact_ids':[],'reason':'No certification evidence.'}]}).data
                    if case['liveness']=='closed' or case['mandatory_certificate']:
                        self.assertEqual('Ineligible', assessment['classification'])
                    elif case['liveness']=='unverified':
                        self.assertEqual('Needs clarification', assessment['classification'])
                    adapted = {**model, 'job_id':job_id, 'language':case['language']}
                    if assessment['classification']=='Ineligible' or case['liveness']!='active':
                        with self.assertRaises(WorkflowError): work.import_wording(job_id, adapted)
                    # Unknown location/pay remains an explicit fixture uncertainty.
                    # Do not count schema-valid drafts as ready applications.
