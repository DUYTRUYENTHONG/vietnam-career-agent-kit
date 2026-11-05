"""Fictional MCP distribution preflight; no SDK or client configuration required."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
import unittest

from scripts.career_mcp import configuration, workspace
from core.workflow import WorkflowError


class MCPEntryTests(unittest.TestCase):
    def test_configuration_roundtrips_paths_without_creating_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fictional space tiếng Việt 🧪'
            entry=json.loads(configuration(path,sys.executable,'json'))['mcpServers']['career-kit']
            self.assertEqual(str(Path(sys.executable).resolve()),entry['command'])
            self.assertIn(str(path.resolve()),entry['args'])
            codex=tomllib.loads(configuration(path,sys.executable,'codex'))['mcp_servers']['career-kit']
            self.assertEqual(entry['command'],codex['command'])
            self.assertEqual(entry['args'],codex['args'])
            self.assertFalse(path.exists())

    def test_missing_workspace_and_legacy_workspace_are_not_initialized(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'missing'
            with self.assertRaises(WorkflowError):workspace(path)
            self.assertFalse(path.exists())
            path.mkdir()
            legacy=path/'applications.sqlite3'
            legacy.write_bytes(b'fictional legacy sentinel')
            with self.assertRaisesRegex(WorkflowError,'source.memory'):
                workspace(path)
            self.assertEqual(b'fictional legacy sentinel',legacy.read_bytes())
            self.assertFalse((path/'workflow.sqlite3').exists())

    def test_unsupported_schema_and_repo_paths_stay_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'private';path.mkdir()
            with closing(sqlite3.connect(path/'workflow.sqlite3')) as db:
                db.execute('PRAGMA user_version=999')
            before=(path/'workflow.sqlite3').read_bytes()
            with self.assertRaises(WorkflowError):workspace(path)
            self.assertEqual(before,(path/'workflow.sqlite3').read_bytes())
        with self.assertRaises(ValueError):
            configuration(Path(__file__).resolve().parents[1]/'private',sys.executable,'json')

    def test_corrupt_database_is_rejected_without_rewriting(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'private';path.mkdir()
            database=path/'workflow.sqlite3'
            database.write_bytes(b'fictional damaged database')
            with self.assertRaises(WorkflowError):workspace(path)
            self.assertEqual(b'fictional damaged database',database.read_bytes())

    def test_corrupt_database_returns_structured_cli_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'private';path.mkdir()
            database=path/'workflow.sqlite3'
            database.write_bytes(b'fictional damaged database')
            entry=Path(__file__).resolve().parents[1]/'scripts/career_mcp.py'
            for flags in (['--check'],[]):
                result=subprocess.run([sys.executable,str(entry),'--data-dir',str(path),*flags],
                                      capture_output=True,text=True,encoding='utf8',timeout=15)
                self.assertEqual(2,result.returncode)
                output=result.stdout if flags else result.stderr
                self.assertEqual('blocked',json.loads(output)['outcome'])
                self.assertNotIn('Traceback',result.stdout+result.stderr)
                self.assertEqual('',result.stderr if flags else result.stdout)
                self.assertEqual(b'fictional damaged database',database.read_bytes())
