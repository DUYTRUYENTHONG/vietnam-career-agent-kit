"""Fictional source-bound review labels; no real candidate or model calls."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from adapters.local_finetuning import validate_dataset
from core.learning import export_reviewed, check_export
from core.ledger import canonical_hash
from core.workflow import WorkflowError
from scripts.demo_wording import seed, fictional_review


class ReviewLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.work,self.model=seed(Path(self.temp.name)/'private')
        self.work.import_wording(1,self.model)
        self.review=fictional_review(self.work.wording_packet(1).data)
        self.review['rubric_sha256']=self.work.wording_packet(1).data['review_rubric_sha256']
        self.work.review_wording(1,self.review)

    def test_current_scores_export_as_one_private_review_not_six_independent_rows(self):
        before=self.work.db_path.read_bytes()
        result=export_reviewed(self.work,[1],'datasets/grade',task='cv-review').data
        self.assertEqual(1,result['example_count']);self.assertFalse(result['ready_for_split'])
        example=json.loads(self.work.inside('datasets/grade/examples.jsonl').read_text(encoding='utf8'))
        inputs=json.loads(example['messages'][1]['content'])
        target=json.loads(example['messages'][2]['content'])
        self.assertEqual({'editorial':self.review['editorial']},target)
        self.assertNotIn('editorial',inputs)
        self.assertNotIn('contacts',inputs)
        self.assertNotIn('reviewer',inputs)
        self.assertIn('cv_sections',inputs);self.assertIn('rubric',inputs)
        self.assertEqual(set(self.review['editorial']),set(inputs['output_schema']['properties']['editorial']['required']))
        self.assertNotIn('data@example.invalid',str(inputs))
        self.assertTrue(check_export(self.work,'datasets/grade').data['current_evidence_checked'])
        self.assertEqual(before,self.work.db_path.read_bytes())

    def test_label_or_review_tampering_cannot_become_current_training_data(self):
        export_reviewed(self.work,[1],'datasets/grade',task='cv-review')
        path=self.work.inside('datasets/grade/examples.jsonl')
        row=json.loads(path.read_text(encoding='utf8'))
        target=json.loads(row['messages'][2]['content']);target['editorial']['relevance']['score']=3
        row['messages'][2]['content']=json.dumps(target)
        path.write_text(json.dumps(row)+'\n',encoding='utf8')
        manifest_path=self.work.inside('datasets/grade/manifest.json')
        manifest=json.loads(manifest_path.read_text(encoding='utf8'))
        import hashlib
        manifest['files']['examples.jsonl']=hashlib.sha256(path.read_bytes()).hexdigest()
        manifest['manifest_fingerprint']=canonical_hash({k:v for k,v in manifest.items() if k!='manifest_fingerprint'})
        manifest_path.write_text(json.dumps(manifest),encoding='utf8')
        with self.assertRaises(WorkflowError):check_export(self.work,'datasets/grade')

    def test_changed_actual_review_invalidates_export(self):
        export_reviewed(self.work,[1],'datasets/grade',task='cv-review')
        corrected=deepcopy(self.review)
        corrected['editorial']['concision']['score']=1
        self.work.review_wording(1,corrected)
        with self.assertRaises(WorkflowError):check_export(self.work,'datasets/grade')

    def test_edited_review_file_is_not_a_new_recorded_review(self):
        draft=self.work.current_draft(1)
        path=self.work.inside(draft['files']['wording_review']['path'])
        edited=json.loads(path.read_text(encoding='utf8'))
        edited['editorial']['specificity']['score']=3
        path.write_text(json.dumps(edited),encoding='utf8')
        with self.assertRaises(WorkflowError):
            export_reviewed(self.work,[1],'datasets/edited-review',task='cv-review')
        self.assertFalse(self.work.inside('datasets/edited-review').exists())

    def test_changed_rubric_invalidates_its_old_grading_export(self):
        export_reviewed(self.work,[1],'datasets/grade',task='cv-review')
        rubric=self.work.atomic_text('inputs/changed-rubric.md','Fictional changed rubric.')
        with patch('core.tailoring.RUBRIC_PATH',rubric):
            with self.assertRaises(WorkflowError):check_export(self.work,'datasets/grade')

    def test_unbound_legacy_grades_cannot_be_silently_relabelled(self):
        legacy=deepcopy(self.review);legacy.pop('rubric_sha256')
        self.work.review_wording(1,legacy)
        export_reviewed(self.work,[1],'datasets/legacy-wording')
        with self.assertRaises(WorkflowError):
            export_reviewed(self.work,[1],'datasets/unbound-grades',task='cv-review')
        self.assertFalse(self.work.inside('datasets/unbound-grades').exists())

    def test_invalid_rubric_digest_cannot_be_recorded(self):
        for digest in (True,123,'not-a-digest','a'*63):
            invalid=deepcopy(self.review);invalid['rubric_sha256']=digest
            with self.assertRaises(ValueError):self.work.review_wording(1,invalid)

    def test_explicit_trainer_task_never_confuses_review_and_wording(self):
        export_reviewed(self.work,[1],'datasets/grade',task='cv-review')
        export_reviewed(self.work,[1],'datasets/wording')
        self.assertFalse(validate_dataset(self.work,'datasets/grade','cv-review').data['ready_for_split'])
        for directory,task in [('datasets/grade','cv-wording'),('datasets/wording','cv-review')]:
            with self.assertRaises(WorkflowError):validate_dataset(self.work,directory,task)

    def test_same_job_dimensions_stay_together_and_duplicate_reviews_do_not_make_a_split(self):
        job,_=self.work.job_document(1);job=deepcopy(job)
        job.update(req_id=job['req_id']+'-2',platform_job_id=job['platform_job_id']+'-2',url=job['url']+'/2')
        self.work.import_job(job)
        self.work.assess(2,{'schema_version':'1.0','rows':self.work.wording_packet(1).data['assessment']['rows']})
        model=deepcopy(self.model);model['job_id']=2
        self.work.import_wording(2,model)
        review=fictional_review(self.work.wording_packet(2).data)
        review['rubric_sha256']=self.work.wording_packet(2).data['review_rubric_sha256']
        self.work.review_wording(2,review)
        result=export_reviewed(self.work,[1,2],'datasets/duplicates',task='cv-review').data
        self.assertFalse(result['ready_for_split'])
        review['editorial']['relevance']['rationale']='A different fictional vacancy review, still only a fixture.'
        self.work.review_wording(2,review)
        result=export_reviewed(self.work,[1,2],'datasets/disjoint',task='cv-review').data
        self.assertTrue(result['ready_for_split'])
        checked=check_export(self.work,'datasets/disjoint').data
        self.assertEqual(2,checked['example_count'])
        self.assertGreater(checked['split_overlap']['shared_fact_count'],0)

    def test_real_cli_has_an_explicit_review_task(self):
        cli=Path(__file__).resolve().parents[1]/'scripts/kit.py'
        result=subprocess.run([sys.executable,str(cli),'--data-dir',str(self.work.data_dir),
            'learning-export','--job-id','1','--output','datasets/cli-grade','--task','cv-review'],
            capture_output=True,text=True,encoding='utf8',timeout=30)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertTrue(check_export(self.work,'datasets/cli-grade').data['current_evidence_checked'])
