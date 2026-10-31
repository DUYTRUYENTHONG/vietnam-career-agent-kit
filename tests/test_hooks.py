"""Fictional local hook protocol checks; no native callbacks or live sites."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class HookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('kit_guard',ROOT/'hooks/guard.py')
        cls.guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.guard)

    def test_browser_transmission_is_denied_for_each_host(self):
        for host in ['codex','claude']:
            result=self.guard.handle({'hook_event_name':'PreToolUse','tool_name':'mcp__browser__upload','tool_input':{}},host,None)
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')

    def test_generic_control_denied_but_local_read_not_claimed_guarded(self):
        result=self.guard.handle({'hook_event_name':'PreToolUse','tool_name':'mcp__cua_repl__js'},'codex',None)
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')
        self.assertEqual(self.guard.handle({'hook_event_name':'PreToolUse','tool_name':'Read'},'codex',None),{})

    def test_post_edit_marks_old_approvals_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.guard.handle({'hook_event_name':'PostToolUse','tool_name':'apply_patch'},'codex',root)
            marker=json.loads((root/'approvals-invalidated.json').read_text())
            self.assertEqual(marker['reason'],'files_changed')
            self.assertTrue(marker['invalidated_utc'].endswith('+00:00'))

    def test_private_directory_rejects_framework_and_symlink_target(self):
        with self.assertRaises(ValueError):self.guard.checked_data_dir(ROOT/'private')
        with self.assertRaises(ValueError):self.guard.checked_data_dir(ROOT.parent)

    def test_session_and_stop_never_resume_or_access_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            for event in ['SessionStart','Stop']:
                with patch.object(Path,'read_text',side_effect=AssertionError('No transcript access')):
                    result=self.guard.handle({'hook_event_name':event,'transcript_path':'never-read-this'},'codex',Path(folder))
                self.assertNotIn('continue',result)
                self.assertIn('systemMessage',result)
                self.assertIn('growth-context',result['systemMessage'])
                self.assertIn('growth-capture',result['systemMessage'])
                self.assertIn('--data-dir',result['systemMessage'])
                self.assertIn('--job-id',result['systemMessage'])
                self.assertEqual([],list(Path(folder).iterdir()))

    def test_invalid_input_has_no_allow_decision(self):
        with self.assertRaises(ValueError):self.guard.read_event(io.StringIO('not-json'))
        with self.assertRaises(ValueError):self.guard.read_event(io.StringIO('x'*70000))

if __name__=='__main__':unittest.main()
