import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'examples/fictional'


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.data=Path(self.tmp.name)/'private'

    def tearDown(self):self.tmp.cleanup()

    def run_cli(self,*args,code=0):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/kit.py'),'--data-dir',str(self.data),*args],
            cwd=self.tmp.name,capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(code,result.returncode,result.stderr+result.stdout)
        payload=json.loads(result.stdout)
        self.assertEqual('1.0',payload['schema_version'])
        self.assertIn(payload['outcome'],{'ok','blocked','needs_input','manual_required','failed','submission_unknown'})
        self.assertNotIn('Traceback',result.stderr)
        return payload

    def test_real_cli_walkthrough_and_resume_from_another_working_directory(self):
        self.run_cli('doctor','--runtime','generic')
        self.run_cli('init','--language','vi')
        self.run_cli('import-cv','--source-id','CV1','--file',str(FIX/'cv-a.md'))
        result=self.run_cli('import-profile','--file',str(FIX/'profile-a.json'),code=2)
        fingerprint=result['data']['fingerprint']
        proof=self.data/'profile-review.txt';proof.write_text('CONFIRM PROFILE '+fingerprint,encoding='utf8')
        self.run_cli('confirm-profile','--fingerprint',fingerprint,'--confirmation',str(proof))
        job=self.run_cli('import-jd','--file',str(FIX/'job.json'))['data']['job']['id']
        self.run_cli('assess','--job-id',str(job),'--matrix',str(FIX/'matrix.json'))
        draft=self.run_cli('prepare','--job-id',str(job),'--plan',str(FIX/'plan.json'))
        self.assertTrue((self.data/draft['data']['files']['cv']['path']).exists())
        resumed=self.run_cli('resume')
        self.assertEqual(1,resumed['data']['summary']['jobs'])
        self.run_cli('handoff','--job-id',str(job),code=2)
        report=self.run_cli('report','--format','md','--output','reports/checkpoint.md')
        self.assertTrue((self.data/report['data']['path']).exists())

    def test_actionable_structured_errors_and_missing_browser_grok_fallback(self):
        self.run_cli('import-profile','--file',str(FIX/'profile-a.json'),code=2)
        self.run_cli('init')
        bad=self.data/'bad.json';bad.write_text('{bad',encoding='utf8')
        self.run_cli('import-profile','--file',str(bad),code=2)
        doctor=self.run_cli('doctor','--runtime','grok')
        self.assertEqual('Unsupported',doctor['data']['native_compatibility'])
        self.assertFalse(doctor['data']['browser_execution'])
        self.run_cli('prepare','--job-id','invalid','--plan',str(FIX/'plan.json'),code=2)

    def test_report_cannot_overwrite_tracker_or_evidence(self):
        self.run_cli('init')
        for target in ['workflow.sqlite3','evidence/source.txt','../other-person/report.md']:
            result=self.run_cli('report','--output',target,code=2)
            self.assertEqual('blocked',result['outcome'])
        self.assertEqual(0,self.run_cli('status')['data']['jobs'])
