"""Explicit optional integration suite; real local converter, fictional data only."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.documents import Documents
from core.rendering import build_docx, render_files, verify_pdf
from core.workflow import WorkflowError
from scripts.demo_slice1 import demo


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)

    def tearDown(self):self.tmp.cleanup()

    def cli(self,workspace,*args,code=0):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/kit.py'),'--data-dir',str(workspace),*args],
            capture_output=True,encoding='utf8',timeout=120,cwd=self.root)
        self.assertEqual(code,result.returncode,result.stdout+result.stderr)
        return json.loads(result.stdout)['data']

    def export_qa(self,name,path,record):
        target=os.environ.get('CAREER_KIT_QA_DIR')
        if target:
            out=Path(target)/name
            if out.exists():self.fail('QA export refuses to overwrite existing files')
            shutil.copytree(path,out)
            (out/'render-report.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')

    def test_two_real_rendered_fictional_users_and_complete_cli_approval_cycle(self):
        soffice=os.environ['CAREER_KIT_SOFFICE']
        for candidate in ['a','b']:
            with self.subTest(candidate=candidate):
                private=self.root/candidate
                if candidate=='b':
                    result=subprocess.run([sys.executable,str(ROOT/'scripts/demo_slice2.py'),
                        '--candidate','b','--data-dir',str(private),'--soffice',soffice],
                        capture_output=True,encoding='utf8',timeout=120,cwd=self.root)
                    self.assertEqual(0,result.returncode,result.stdout+result.stderr)
                    rendered=json.loads(result.stdout)['data']['render']
                    template=json.loads((private/'document-review.json').read_text(encoding='utf8'))
                    self.assertFalse(any(template['checks'].values()))
                else:
                    demo(private,candidate)
                    self.cli(private,'init')
                    rendered=self.cli(private,'render','--job-id','1','--soffice',soffice)
                self.assertGreaterEqual(rendered['page_count'],1)
                self.export_qa('candidate-'+candidate,private/rendered['files']['pdf']['path'].rsplit('/',1)[0],rendered)
                # This assertion is a fictional test input, not a claim of human visual review.
                review={'schema_version':'1.0','render_fingerprint':rendered['fingerprint'],
                    'reviewed_pages':list(range(1,rendered['page_count']+1)),
                    'checks':dict.fromkeys(['content','layout','glyphs','language'],True)}
                review_file=private/'review.json';review_file.write_text(json.dumps(review),encoding='utf8')
                self.cli(private,'review-documents','--render-id',rendered['render_id'],'--review',str(review_file))
                now=datetime.now(timezone.utc)
                plan={'schema_version':'1.0','campaign_id':'fictional-cli','mode':'ASSIST',
                    'expires_utc':(now+timedelta(hours=1)).isoformat(),'submission_limit':0,
                    'entries':[{'job_id':1,'render_id':rendered['render_id'],'format':'pdf',
                        'destination':'https://apply.example.test/fictional','operations':['fill','upload'],
                        'answers':{},'required_answers':[],'consents':[],
                        'policy':{'permission':'permitted','source':'https://apply.example.test/policy',
                            'checked_utc':now.isoformat(),'allowed_operations':['fill','upload']}}]}
                scope=private/'scope.json';scope.write_text(json.dumps(plan),encoding='utf8')
                manifest=self.cli(private,'create-manifest','--plan',str(scope))
                proof=private/'approval.txt';proof.write_text('APPROVE MANIFEST '+manifest['fingerprint'],encoding='utf8')
                self.cli(private,'approve-manifest','--fingerprint',manifest['fingerprint'],'--confirmation',str(proof))
                self.assertFalse(self.cli(private,'check-manifest','--fingerprint',manifest['fingerprint'])['execution_enabled'])
                report=self.cli(private,'report','--format','md','--output','reports/rendered.md')
                self.assertIn(manifest['fingerprint'],(private/report['path']).read_text(encoding='utf8'))
                self.assertEqual(2,len(self.cli(private,'handoff','--job-id','1',code=2)['documents']))
                self.cli(private,'reject-documents','--render-id',rendered['render_id'],'--reason','Fictional rejection test')
                self.cli(private,'check-manifest','--fingerprint',manifest['fingerprint'],code=2)

    def test_long_vietnamese_name_multiline_literal_markup_and_multiple_pages(self):
        content={'name':'Nguyễn Thị Minh Anh Thảo '*6,'headline':'Vị trí ứng tuyển Chuyên viên phân tích quy trình và dữ liệu',
            'contacts':['fictional@example.invalid'],'section':'Kinh nghiệm và năng lực được chọn',
            'claims':[f'{n}. Đã ghi nhận <yêu cầu> & thử nghiệm quy trình trong dự án lớp học.\n'+
                'Phối hợp nhóm để kiểm tra dữ liệu và mô tả giới hạn của nguyên mẫu. '*2 for n in range(32)]}
        result=render_files(content,self.root,os.environ['CAREER_KIT_SOFFICE'])
        self.assertGreater(result['page_count'],1)
        self.assertLessEqual(result['page_count'],10)
        self.export_qa('long-vietnamese',self.root,result)

    def test_missing_converter_and_conversion_timeout_fail_closed(self):
        private=self.root/'private';demo(private)
        work=Documents(private);work.init()
        with self.assertRaises(WorkflowError) as absent:work.render(1,self.root/'missing-converter')
        self.assertEqual('manual_required',absent.exception.outcome)
        with patch('core.rendering.subprocess.run',side_effect=[
                subprocess.CompletedProcess('fixture',0,stdout='Fictional converter'),
                subprocess.TimeoutExpired('fixture',90)]):
            with self.assertRaises(WorkflowError) as timed:work.render(1,Path(sys.executable))
        self.assertEqual('failed',timed.exception.outcome)
        with work._db() as db:self.assertEqual(0,db.execute('SELECT count(*) FROM document_sets').fetchone()[0])

    def test_corrupted_pdf_is_not_accepted_as_verified_content(self):
        content={'name':'Fictional Candidate','headline':'Target role Analyst','contacts':[],
            'section':'Capabilities','claims':['Used SQL in a classroom project.']}
        build_docx(content,self.root/'literal.docx')
        # A different, valid PDF must fail the source-content check.
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(width=595,height=842)
        with (self.root/'wrong.pdf').open('wb') as stream:writer.write(stream)
        with self.assertRaises(WorkflowError):verify_pdf(content,self.root/'wrong.pdf')
