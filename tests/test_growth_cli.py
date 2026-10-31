"""Fictional CLI/MCP transport contracts; no model, account or provider calls."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

import core
from core.contracts import Outcome
from core.execution import Executor
from core.workflow import WorkflowError
from scripts import kit
from scripts.demo_slice1 import demo


API_NAMES = ['gap_context', 'capture', 'import_plan', 'review_plan', 'check_plan',
             'record_evidence', 'export_reviewed', 'check_export']


class GrowthCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'fictional-private'
        demo(self.directory)
        self.growth = ModuleType('core.career_growth')
        for name in API_NAMES:
            setattr(self.growth, name, Mock(return_value=Outcome('ok', {'fictional': True}, [])))
        modules = patch.dict(sys.modules, {'core.career_growth': self.growth})
        modules.start(); self.addCleanup(modules.stop)
        attribute = patch.object(core, 'career_growth', self.growth, create=True)
        attribute.start(); self.addCleanup(attribute.stop)

    def execute(self, *arguments):
        return kit.execute(kit.parser().parse_args(['--data-dir', str(self.directory), *arguments]))

    def test_commands_dispatch_to_core_with_explicit_workspace_and_private_json(self):
        packet = {'schema_version': '1.0', 'fictional': True}
        source = self.directory / 'packet.json'
        source.write_text(json.dumps(packet), encoding='utf8')
        cases = [
            (['growth-context', '--job-id', '1', '--job-id', '2'], 'gap_context', ([1, 2],)),
            (['growth-capture', '--job-id', '1'], 'capture', ([1],)),
            (['growth-plan', '--file', str(source)], 'import_plan', (packet,)),
            (['growth-review', '--fingerprint', 'fp', '--file', str(source)], 'review_plan', ('fp', packet)),
            (['growth-check', '--fingerprint', 'fp'], 'check_plan', ('fp',)),
            (['growth-evidence', '--fingerprint', 'fp', '--action-id', 'practice', '--artifact', 'proof.md', '--note', 'Fictional practice'],
             'record_evidence', ('fp', 'practice', 'proof.md', 'Fictional practice')),
            (['growth-export', '--fingerprint', 'fp', '--fingerprint', 'fp2', '--output', 'datasets/growth'],
             'export_reviewed', (['fp', 'fp2'], 'datasets/growth')),
            (['growth-check-export', '--directory', 'datasets/growth'], 'check_export', ('datasets/growth',)),
        ]
        for arguments, name, expected in cases:
            with self.subTest(command=arguments[0]):
                self.assertEqual('ok', self.execute(*arguments).outcome)
                call = getattr(self.growth, name).call_args.args
                self.assertEqual(self.directory.resolve(), call[0].data_dir)
                self.assertEqual(expected, call[1:])

    def test_growth_commands_never_choose_a_default_workspace(self):
        args = kit.parser().parse_args(['growth-context', '--job-id', '1'])
        with self.assertRaisesRegex(WorkflowError, '--data-dir is required'):
            kit.execute(args)
        self.growth.gap_context.assert_not_called()

    def test_plan_and_review_refuse_json_outside_selected_private_workspace(self):
        source = Path(self.temp.name) / 'outside.json'
        source.write_text('{}', encoding='utf8')
        for command in [['growth-plan'], ['growth-review', '--fingerprint', 'fp']]:
            with self.subTest(command=command[0]), self.assertRaises(WorkflowError):
                self.execute(*command, '--file', str(source))
        self.growth.import_plan.assert_not_called()
        self.growth.review_plan.assert_not_called()

    def test_assessment_capture_is_explicit_and_preserves_assessment(self):
        matrix = str(kit.ROOT / 'examples/fictional/matrix.json')
        plain = self.execute('assess', '--job-id', '1', '--matrix', matrix)
        self.growth.capture.assert_not_called()
        captured = self.execute('assess', '--job-id', '1', '--matrix', matrix, '--capture-growth')
        self.assertEqual(plain.outcome, captured.outcome)
        self.assertEqual(plain.data, {k: v for k, v in captured.data.items() if k != 'growth_capture'})
        self.assertEqual('ok', captured.data['growth_capture']['outcome'])
        self.assertEqual([1], self.growth.capture.call_args.args[1])

    def test_capture_failure_is_honest_and_does_not_erase_saved_assessment(self):
        self.growth.capture.side_effect = WorkflowError('blocked', 'Fictional stale source')
        result = self.execute('assess', '--job-id', '1', '--matrix',
                              str(kit.ROOT / 'examples/fictional/matrix.json'), '--capture-growth')
        self.assertEqual('ok', result.outcome)
        self.assertEqual('blocked', result.data['growth_capture']['outcome'])
        self.assertIn('Fictional stale source', result.data['growth_capture']['issues'])
        self.assertTrue(any('Assessment was saved' in issue for issue in result.issues))
        work = Executor(self.directory)
        with work._db() as db:
            saved = json.loads(db.execute('SELECT payload FROM assessments WHERE job_id=1').fetchone()[0])
        self.assertEqual(result.data['classification'], saved['classification'])

    def test_unsuccessful_assessment_does_not_capture(self):
        with patch.object(Executor, 'assess', return_value=Outcome('blocked', {}, ['Fictional block'])):
            result = self.execute('assess', '--job-id', '1', '--matrix',
                                  str(kit.ROOT / 'examples/fictional/matrix.json'), '--capture-growth')
        self.assertEqual('blocked', result.outcome)
        self.assertNotIn('growth_capture', result.data)
        self.growth.capture.assert_not_called()

    def test_mcp_annotations_and_outcomes_match_local_core(self):
        class FakeMCP:
            def __init__(self, *args, **kwargs): self.tools = {}
            def tool(self, **kwargs):
                def register(function):
                    self.tools[function.__name__] = (function, kwargs['annotations'])
                    return function
                return register
            def resource(self, *args): return lambda function: function

        fastmcp = ModuleType('mcp.server.fastmcp'); fastmcp.FastMCP = FakeMCP
        with patch.dict(sys.modules, {'mcp': ModuleType('mcp'), 'mcp.server': ModuleType('mcp.server'),
                                     'mcp.server.fastmcp': fastmcp}):
            spec = importlib.util.spec_from_file_location('growth_test_mcp', kit.ROOT / 'adapters/career_mcp.py')
            adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
            with patch.object(adapter, 'career_growth', self.growth):
                work = Executor(self.directory)
                server = adapter.make_career_server(work)
                cases = [
                    ('career_gap_context', 'gap_context', True, ([1],)),
                    ('career_growth_capture', 'capture', False, ([1],)),
                    ('career_growth_plan', 'import_plan', False, ({'fictional': True},)),
                    ('career_growth_review', 'review_plan', False, ('fp', {})),
                    ('career_growth_check', 'check_plan', True, ('fp',)),
                    ('career_growth_evidence', 'record_evidence', False, ('fp', 'practice', 'proof.md', 'Fictional')),
                    ('career_growth_export', 'export_reviewed', False, (['fp'], 'datasets/growth')),
                    ('career_growth_check_export', 'check_export', True, ('datasets/growth',)),
                ]
                for name, api, read_only, arguments in cases:
                    with self.subTest(tool=name):
                        function, annotations = server.tools[name]
                        self.assertEqual(read_only, annotations['readOnlyHint'])
                        self.assertFalse(annotations['openWorldHint'])
                        if not read_only: self.assertFalse(annotations['destructiveHint'])
                        self.assertEqual('ok', function(*arguments)['outcome'])
                        getattr(self.growth, api).assert_called_with(work, *arguments)
                self.growth.capture.side_effect = WorkflowError('blocked', 'Fictional stale source')
                self.assertEqual('blocked', server.tools['career_growth_capture'][0]([1])['outcome'])


class GrowthCliIntegrationTests(unittest.TestCase):
    def test_real_cli_context_capture_and_assessment_opt_in_use_fictional_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / 'fictional-private'
            demo(directory)
            args = [sys.executable, str(kit.ROOT / 'scripts/kit.py'), '--data-dir', str(directory)]
            def run(*arguments):
                result = subprocess.run(args + list(arguments), capture_output=True, encoding='utf8', timeout=15)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                return json.loads(result.stdout)
            before = set(directory.rglob('*'))
            context = run('growth-context', '--job-id', '1')
            self.assertEqual(before, set(directory.rglob('*')))
            self.assertFalse(context['data']['authority_granted'])
            self.assertEqual(0, context['data']['model_api_calls'])
            captured = run('growth-capture', '--job-id', '1')
            self.assertTrue((directory / captured['data']['path']).is_file())
            assessed = run('assess', '--job-id', '1', '--matrix',
                           str(kit.ROOT / 'examples/fictional/matrix.json'), '--capture-growth')
            self.assertEqual('ok', assessed['data']['growth_capture']['outcome'])
            self.assertEqual(captured['data'], assessed['data']['growth_capture']['data'])


if __name__ == '__main__': unittest.main()
