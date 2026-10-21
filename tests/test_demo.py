import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from demo_slice1 import demo
from core.workflow import Preparation, WorkflowError


class DemoTests(unittest.TestCase):
    def test_two_complete_fictional_users_share_code_but_not_facts_jobs_or_files(self):
        with tempfile.TemporaryDirectory() as temp:
            a=Path(temp)/'a';b=Path(temp)/'b'
            first=demo(a,'a');second=demo(b,'b')
            wa,wb=Preparation(a),Preparation(b)
            pa,pb=wa.inspect_profile(),wb.inspect_profile()
            self.assertNotEqual(pa.data['profile']['candidate_id'],pb.data['profile']['candidate_id'])
            ca=(a/first['data']['draft']['files']['cv']['path']).read_text(encoding='utf8')
            cb=(b/second['data']['draft']['files']['cv']['path']).read_text(encoding='utf8')
            self.assertIn('SQL',ca);self.assertNotIn('Excel',ca)
            self.assertIn('Excel',cb);self.assertNotIn('SQL',cb)
            self.assertNotIn(pa.data['profile']['name'],cb)
            self.assertEqual('Đà Nẵng',wb.resume().data['jobs'][0]['city'])
            with self.assertRaises(WorkflowError):
                wa.prepare(first['data']['draft']['job_id'],
                    {'schema_version':'1.0','language':'en','fact_ids':['F4']})
            with self.assertRaises(WorkflowError):demo(a,'b')

    def test_demo_can_run_from_fresh_checkout_without_persistent_test_data(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/demo_slice1.py')],
            capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(0,result.returncode,result.stderr+result.stdout)
        self.assertTrue(json.loads(result.stdout)['data']['temporary_workspace_removed_after_check'])
