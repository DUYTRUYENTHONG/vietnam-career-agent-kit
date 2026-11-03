"""Opt-in career MCP previews do not register email/browser tools or edit hosts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.execution import Executor
from scripts.plugin_config import generate


class PluginConfigTests(unittest.TestCase):
    def test_career_only_config_contains_one_existing_stdio_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Executor(Path(tmp)/'fictional-private')
            result = generate(work, sys.executable, career_only=True)
            self.assertFalse(result['installed'])
            self.assertFalse(result['host_settings_changed'])
            self.assertEqual(1, len(result['packages']))
            root = work.data_dir/'configured-plugins'
            config = json.loads((root/'mcp-servers.example.json').read_text())
            self.assertEqual({'career-career'}, set(config['mcpServers']))
            server = config['mcpServers']['career-career']
            self.assertEqual('career', server['args'][1])
            self.assertEqual(str(work.data_dir), server['args'][3])
            self.assertEqual(str(Path(sys.executable).resolve()), server['command'])
            self.assertFalse((root/'career-email').exists())
            self.assertFalse((root/'career-browser').exists())
            marketplace = json.loads((root/'.agents/plugins/marketplace.json').read_text())
            self.assertEqual(['career-career'], [p['name'] for p in marketplace['plugins']])
            self.assertIn('[mcp_servers.career-career]', (root/'codex.example.toml').read_text())
            self.assertFalse(work.db_path.exists())

    def test_conflicting_modes_fail_before_writing_any_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Executor(Path(tmp)/'fictional-private')
            with self.assertRaisesRegex(ValueError, 'Choose'):
                generate(work, sys.executable, include_career=True, career_only=True)
            self.assertFalse(work.data_dir.exists())

    def test_cli_exposes_mutually_exclusive_opt_in_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(__file__).resolve().parents[1]
            output = Path(tmp)/'fictional-private'
            command = [sys.executable, str(root/'scripts/plugin_config.py'),
                       '--data-dir', str(output), '--python', sys.executable]
            bad = subprocess.run(command+['--career-only', '--include-career'],
                                 capture_output=True, timeout=15)
            self.assertEqual(2, bad.returncode)
            self.assertFalse(output.exists())
            good = subprocess.run(command+['--career-only'], capture_output=True,
                                  encoding='utf8', timeout=15)
            self.assertEqual(0, good.returncode, good.stderr)
            self.assertEqual(1, len(json.loads(good.stdout)['packages']))
