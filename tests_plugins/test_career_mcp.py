"""Real hash-locked MCP stdio smoke on fictional data; no remote service."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.demo_slice1 import demo
from scripts.plugin_config import generate
from core.execution import Executor


class CareerMCPTests(unittest.TestCase):
    def test_stdio_context_usage_validation_and_opt_in_config(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def check(workspace):
            server = StdioServerParameters(command=sys.executable,
                args=[str(ROOT/'scripts/serve_plugin.py'), 'career', '--data-dir', str(workspace)])
            async with asyncio.timeout(45):
                async with stdio_client(server) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                        self.assertEqual({'performance_record', 'performance_report', 'career_context',
                                          'career_outcome_record', 'career_outcome_report',
                                          'career_email_context', 'campaign_tracker', 'career_evaluate',
                                          'learning_export', 'learning_check', 'career_writing_brief',
                                          'career_check_draft', 'career_gap_context', 'career_growth_capture',
                                          'career_growth_plan', 'career_growth_review', 'career_growth_check',
                                          'career_growth_evidence', 'career_growth_export',
                                          'career_growth_check_export'}, set(tools))
                        self.assertTrue(tools['career_context'].annotations.readOnlyHint)
                        self.assertFalse(tools['performance_record'].annotations.openWorldHint)
                        self.assertTrue(tools['career_gap_context'].annotations.readOnlyHint)
                        self.assertFalse(tools['career_growth_capture'].annotations.readOnlyHint)
                        gaps = await session.call_tool('career_gap_context', {'job_ids': [1]})
                        gap_packet = json.loads(gaps.content[0].text)
                        self.assertEqual('ok', gap_packet['outcome'])
                        self.assertEqual([], gap_packet['data']['gaps'])
                        self.assertFalse(gap_packet['data']['authority_granted'])
                        captured = await session.call_tool('career_growth_capture', {'job_ids': [1]})
                        self.assertEqual('ok', json.loads(captured.content[0].text)['outcome'])
                        self.assertTrue((workspace/json.loads(captured.content[0].text)['data']['path']).is_file())
                        result = await session.call_tool('career_context', {'query': 'SQL', 'limit': 1})
                        self.assertFalse(result.isError)
                        packet = json.loads(result.content[0].text)
                        self.assertEqual('ok', packet['outcome'])
                        self.assertEqual(1, len(packet['data']['facts']))
                        brief = await session.call_tool('career_writing_brief', {'job_id': 1, 'kind': 'cv'})
                        data = json.loads(brief.content[0].text)['data']
                        fact = data['context']['facts'][0]
                        checked = await session.call_tool('career_check_draft', {
                            'request': {'job_id': 1, 'kind': 'cv', 'language': 'en', 'limit': 5},
                            'draft': {'schema_version': '1.0', 'brief_fingerprint': data['brief_fingerprint'],
                                      'blocks': [{'kind': 'cv_bullet', 'text': fact['quote'], 'fact_ids': [fact['id']]}]}})
                        checked_data = json.loads(checked.content[0].text)['data']
                        self.assertTrue(checked_data['review_required'])
                        self.assertFalse(checked_data['semantic_truth_verified'])
                        gold = {'schema_version': '1.0', 'limit': 1, 'cases': [{'id': 'sql', 'query': 'SQL',
                                'expected_fact_ids': [packet['data']['facts'][0]['id']]}]}
                        evaluated = await session.call_tool('career_evaluate', {'evaluation': gold})
                        self.assertEqual(1, json.loads(evaluated.content[0].text)['data']['positive_metrics']['recall_at_k'])
                        unreviewed = await session.call_tool('learning_export', {'job_ids': [1], 'output': 'datasets/unreviewed'})
                        self.assertNotEqual('ok', json.loads(unreviewed.content[0].text)['outcome'])
                        invalid = await session.call_tool('performance_record', {'observation': {'unexpected': 'value'}})
                        self.assertEqual('needs_input', json.loads(invalid.content[0].text)['outcome'])
                        usage = await session.call_tool('performance_report', {})
                        self.assertEqual(0, json.loads(usage.content[0].text)['data']['record_count'])
                        self.assertTrue(tools['career_outcome_report'].annotations.readOnlyHint)
                        self.assertFalse(tools['career_outcome_record'].annotations.readOnlyHint)
                        outcomes = await session.call_tool('career_outcome_report', {'min_age_days': 0})
                        self.assertEqual(0, json.loads(outcomes.content[0].text)['data']['confirmed_submissions'])
                        invalid_outcome = await session.call_tool('career_outcome_record', {'observation': {'unexpected': True}})
                        self.assertEqual('needs_input', json.loads(invalid_outcome.content[0].text)['outcome'])
                        resources = (await session.list_resources()).resources
                        self.assertIn('career-kit://writing-policy', [str(resource.uri) for resource in resources])
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)/'private'; demo(workspace)
            work = Executor(workspace)
            work.init()
            configured = generate(work, sys.executable, include_career=True)
            self.assertEqual(3, len(configured['packages']))
            self.assertFalse(configured['host_settings_changed'])
            asyncio.run(check(workspace))
