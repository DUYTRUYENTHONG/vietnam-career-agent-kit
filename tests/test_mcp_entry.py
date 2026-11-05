"""Fictional MCP distribution preflight; no SDK or client configuration required."""
import json
import hashlib
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from scripts.career_mcp import check, configuration, workspace
from core.workflow import WorkflowError


class MCPEntryTests(unittest.TestCase):
    def source_fixture(self, root):
        (root/'data').mkdir(parents=True)
        source=root/'source.txt'
        source.write_text('Fictional AI-assisted API prototype.',encoding='utf8')
        fact={'fact_id':'F1','exact_claim':'Fictional AI-assisted API prototype.',
              'approval_state':'approved','conflict':None,'source_path':'source.txt',
              'locator':'line 1','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        (root/'data/source-facts.json').write_text(json.dumps([fact]),encoding='utf8')
        (root/'data/applications.sqlite3').write_bytes(b'fictional legacy sentinel')
        return source

    def test_explicit_source_configuration_is_separate_and_never_initializes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source space tiếng Việt'
            entry=json.loads(configuration(path,sys.executable,'json',source_memory=True))['mcpServers']['career-source-memory']
            self.assertIn('--source-memory',entry['args'])
            codex=tomllib.loads(configuration(path,sys.executable,'codex',source_memory=True))['mcp_servers']['career-source-memory']
            self.assertEqual(entry,codex)
            self.assertFalse(path.exists())

    def test_source_preflight_validates_hashes_without_opening_any_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'source workspace';source=self.source_fixture(root)
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch('scripts.career_mcp.version',return_value='1.30.0'):
                result=check(root,source_memory=True)
                self.assertEqual('ok',result['outcome'])
                self.assertEqual('source-memory',result['data']['mode'])
                self.assertTrue(result['data']['read_only'])
                self.assertFalse(result['data']['application_database_opened'])
                self.assertEqual(1,result['data']['verified_fact_count'])
                self.assertNotIn('Fictional AI-assisted API prototype.',json.dumps(result))
                self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
                source.write_text('changed',encoding='utf8')
                with self.assertRaises(ValueError):check(root,source_memory=True)
            self.assertFalse((root/'workflow.sqlite3').exists())

    def test_source_mode_missing_packet_and_stale_source_return_structured_cli_errors(self):
        entry=Path(__file__).resolve().parents[1]/'scripts/career_mcp.py'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'missing'
            for setup in ('missing','stale'):
                if setup=='stale':self.source_fixture(root).write_text('changed',encoding='utf8')
                result=subprocess.run([sys.executable,str(entry),'--data-dir',str(root),'--source-memory','--check'],
                                      capture_output=True,text=True,encoding='utf8',timeout=15)
                self.assertEqual(2,result.returncode)
                self.assertEqual('needs_input',json.loads(result.stdout)['outcome'])
                self.assertNotIn('Traceback',result.stdout+result.stderr)
                self.assertEqual('',result.stderr)
                self.assertFalse((root/'workflow.sqlite3').exists())

    def test_default_mode_recognizes_nested_legacy_database_without_initializing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'older';self.source_fixture(root)
            with self.assertRaisesRegex(WorkflowError,'source.memory'):
                workspace(root)
            self.assertFalse((root/'workflow.sqlite3').exists())

    def test_source_mode_preserves_sdk_and_repository_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'older';self.source_fixture(root)
            with patch('scripts.career_mcp.version',return_value='0.0.0'):
                result=check(root,source_memory=True)
                self.assertEqual('manual_required',result['outcome'])
                self.assertFalse(result['data']['server_started'])
        inside=Path(__file__).resolve().parents[1]/'private'
        with self.assertRaises(ValueError):check(inside,source_memory=True)
        with self.assertRaises(ValueError):configuration(inside,sys.executable,'json',source_memory=True)

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
