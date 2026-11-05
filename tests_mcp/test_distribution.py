"""Acceptance for the minimal pinned MCP environment, never candidate data."""
import importlib.util
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.career_mcp import check
from scripts.demo_slice1 import demo
from scripts.demo_wording import seed, fictional_review


class MCPDistributionTests(unittest.TestCase):
    def test_recorded_review_task_roundtrips_through_actual_mcp(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory() as temp:
            work,model=seed(Path(temp)/'fictional review workspace')
            work.import_wording(1,model)
            packet=work.wording_packet(1).data
            review=fictional_review(packet);review['rubric_sha256']=packet['review_rubric_sha256']
            work.review_wording(1,review)
            before=work.db_path.read_bytes()
            async def verify():
                parameters=StdioServerParameters(command=sys.executable,
                    args=[str(ROOT/'scripts/career_mcp.py'),'--data-dir',str(work.data_dir)],env={'PYTHONUTF8':'1'})
                async with asyncio.timeout(45):
                    async with stdio_client(parameters) as (read,write):
                        async with ClientSession(read,write) as session:
                            await session.initialize()
                            result=await session.call_tool('learning_export',
                                {'job_ids':[1],'output':'datasets/mcp-review','task':'cv-review'})
                            exported=json.loads(result.content[0].text)
                            self.assertEqual('ok',exported['outcome'])
                            self.assertEqual(1,exported['data']['example_count'])
                            checked=await session.call_tool('learning_check',{'directory':'datasets/mcp-review'})
                            self.assertTrue(json.loads(checked.content[0].text)['data']['current_evidence_checked'])
            asyncio.run(verify())
            manifest=work.private_json(work.inside('datasets/mcp-review/manifest.json'))
            self.assertEqual('cv-review',manifest['task'])
            self.assertFalse(manifest['ready_for_split'])
            self.assertEqual(before,work.db_path.read_bytes())

    def test_clean_profile_has_no_browser_or_email_sdks(self):
        for name in ('playwright','keyring','google_auth_oauthlib'):
            self.assertIsNone(importlib.util.find_spec(name),name+' must not be required by this profile')

    def test_real_handshake_resources_and_validation(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/check_career_mcp.py')],
                              capture_output=True,text=True,encoding='utf8',timeout=60)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertIn('"handshake": "passed"',result.stdout)

    def test_preflight_is_read_only_and_uses_pinned_sdk(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'private';demo(path)
            before={str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()}
            result=check(path)
            self.assertEqual('ok',result['outcome'])
            self.assertEqual('1.30.0',result['data']['mcp_version'])
            self.assertTrue(result['data']['workspace_exists'])
            self.assertFalse(result['data']['workspace_created'])
            self.assertFalse(result['data']['host_settings_changed'])
            after={str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
