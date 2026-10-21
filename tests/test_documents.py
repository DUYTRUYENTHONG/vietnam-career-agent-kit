import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.documents import Documents
from core.workflow import WorkflowError
from scripts.demo_slice1 import demo


def fake_render(content, directory, soffice=None):
    for name in ['cv.docx','cv.pdf','page-001.png']:
        (directory/name).write_bytes(('FICTIONAL UNIT TEST '+name).encode())
    return {'page_count':1,'renderer':{'test_double':True}}


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/'private'
        demo(self.root)
        self.work=Documents(self.root);self.work.init()
        self.render_patch=patch('core.documents.render_files',side_effect=fake_render)
        self.render_patch.start();self.addCleanup(self.render_patch.stop)

    def tearDown(self):self.tmp.cleanup()

    def rendered(self):return self.work.render(1).data

    def test_content_validation_reads_only_the_selected_job(self):
        fixture=Path(__file__).resolve().parents[1]/'examples/fictional'
        job=json.loads((fixture/'job.json').read_text(encoding='utf8'))
        job.update(platform_job_id='fictional-other',req_id='FICT-OTHER',url='https://jobs.example.test/other')
        other=self.work.import_job(job).data['job']['id']
        self.work.assess(other,json.loads((fixture/'matrix.json').read_text(encoding='utf8')))
        draft=self.work.prepare(other,json.loads((fixture/'plan.json').read_text(encoding='utf8'))).data
        (self.root/draft['files']['cv']['path']).write_bytes(b'Unrelated stale draft')
        with patch.object(self.work, 'job_document', wraps=self.work.job_document) as reads:
            self.work.content_model(1)
        self.assertEqual([1, 1], [call.args[0] for call in reads.call_args_list])
        self.assertTrue(self.work.job_checkpoint(other)['draft_stale'])
        self.assertEqual('manual_required',self.work.handoff(1).outcome)

    def review(self, result):
        review={'schema_version':'1.0','render_fingerprint':result['fingerprint'],
            'reviewed_pages':[1],'checks':{'content':True,'layout':True,'glyphs':True,'language':True}}
        path=self.root/'review.json';path.write_text(json.dumps(review),encoding='utf8')
        return self.work.review_documents(result['render_id'],path)

    def test_render_uses_canonical_quotes_and_requires_every_page_review(self):
        result=self.rendered()
        model=json.loads((self.root/result['files']['content']['path']).read_text(encoding='utf8'))
        self.assertIn('Nguyễn',model['name'])
        self.assertNotIn('Python',str(model['claims']))
        self.assertFalse(self.work.current_render(result['render_id'])['reviewed'])
        self.assertTrue(self.review(result).data['reviewed'])
        self.assertEqual({'docx','pdf'},set(self.work.handoff(1).data['documents']))
        self.assertNotIn('source_map',self.work.handoff(1).data['documents'])

    def test_artifact_and_preview_tampering_invalidate_review(self):
        for key in ['docx','pdf','content','page']:
            with self.subTest(key=key):
                result=self.rendered();self.review(result)
                file=result['pages'][0] if key=='page' else result['files'][key]
                (self.root/file['path']).write_bytes(b'changed')
                with self.assertRaises(WorkflowError):self.work.current_render(result['render_id'])

    def test_review_missing_page_wrong_fingerprint_or_unchecked_gate_is_rejected(self):
        result=self.rendered()
        for changes in [{'reviewed_pages':[]},{'render_fingerprint':'0'*64},
                        {'checks':{'content':True,'layout':False,'glyphs':True,'language':True}}]:
            raw={'schema_version':'1.0','render_fingerprint':result['fingerprint'],'reviewed_pages':[1],
                 'checks':{'content':True,'layout':True,'glyphs':True,'language':True},**changes}
            file=self.root/'review.json';file.write_text(json.dumps(raw),encoding='utf8')
            with self.assertRaises(WorkflowError):self.work.review_documents(result['render_id'],file)

    def test_renderer_failure_does_not_register_partial_artifacts(self):
        for error in [WorkflowError('failed','fictional converter timeout'),RuntimeError('fictional native library failure')]:
            with patch('core.documents.render_files',side_effect=error):
                with self.assertRaises(WorkflowError) as failure:self.work.render(1)
                self.assertEqual('failed',failure.exception.outcome)
        with self.work._db() as db:
            self.assertEqual(0,db.execute('SELECT count(*) FROM document_sets').fetchone()[0])
        self.assertEqual('review_required',self.work.get_job(1)['state'])

    def test_changed_draft_or_profile_cannot_reuse_old_render(self):
        result=self.rendered();self.review(result)
        draft=self.work.resume().data['jobs'][0]['draft']
        (self.root/draft['files']['cv']['path']).write_text('unsupported experience',encoding='utf8')
        with self.assertRaises(WorkflowError):self.work.current_render(result['render_id'])
