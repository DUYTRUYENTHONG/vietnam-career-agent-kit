"""Acceptance for the minimal pinned MCP environment, never candidate data."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.career_mcp import check
from scripts.demo_slice1 import demo


class MCPDistributionTests(unittest.TestCase):
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
