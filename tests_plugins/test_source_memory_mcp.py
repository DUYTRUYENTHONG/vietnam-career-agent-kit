"""Real stdio source-only MCP round trip; fictional files, no application database."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


class SourceMemoryMCPTests(unittest.TestCase):
    def test_only_read_context_is_exposed_and_changed_source_is_rejected(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def check(root, source):
            args = [str(Path(__file__).resolve().parents[1]/'scripts/source_memory.py'),
                    '--data-dir', str(root), '--stdio']
            async with asyncio.timeout(30):
                async with stdio_client(StdioServerParameters(command=sys.executable, args=args)) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = (await session.list_tools()).tools
                        self.assertEqual(['career_source_context'], [t.name for t in tools])
                        self.assertTrue(tools[0].annotations.readOnlyHint)
                        result = await session.call_tool('career_source_context', {'query': 'API'})
                        data = json.loads(result.content[0].text)
                        self.assertEqual('F1', data['data']['facts'][0]['id'])
                        source.write_text('changed', encoding='utf8')
                        result = await session.call_tool('career_source_context', {'query': 'API'})
                        self.assertEqual('needs_input', json.loads(result.content[0].text)['outcome'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'data').mkdir()
            source = root/'project.txt'; source.write_text('Fictional API implementation', encoding='utf8')
            fact = {'fact_id': 'F1', 'exact_claim': 'Fictional AI-assisted API implementation',
                    'approval_state': 'approved', 'conflict': None, 'source_path': 'project.txt',
                    'locator': 'line1', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
            (root/'data/source-facts.json').write_text(json.dumps([fact]), encoding='utf8')
            asyncio.run(check(root, source))
            self.assertFalse(list(root.rglob('*.sqlite3')))
