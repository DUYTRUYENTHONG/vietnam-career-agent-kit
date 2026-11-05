#!/usr/bin/env python3
"""Run a real local MCP handshake on disposable fictional data, then clean up."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.demo_slice1 import demo


async def verify(directory):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    parameters=StdioServerParameters(command=sys.executable,
        args=[str(ROOT/'scripts/career_mcp.py'),'--data-dir',str(directory)],
        env={'PYTHONUTF8':'1'})
    async with asyncio.timeout(45):
        async with stdio_client(parameters) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                tools={tool.name for tool in (await session.list_tools()).tools}
                required={'career_context','career_writing_brief','career_check_draft',
                          'campaign_tracker','performance_report','learning_export'}
                if not required.issubset(tools) or len(tools)!=20:
                    raise ValueError('Unexpected career tool inventory')
                context=await session.call_tool('career_context',{'query':'SQL'})
                packet=json.loads(context.content[0].text)
                if packet['outcome']!='ok' or not packet['data']['facts'] or packet['data']['model_api_calls']!=0:
                    raise ValueError('Fictional retrieval did not pass')
                brief=await session.call_tool('career_writing_brief',{'job_id':1,'kind':'cv'})
                if json.loads(brief.content[0].text)['outcome']!='ok':
                    raise ValueError('Fictional writing brief did not pass')
                resources=await session.list_resources()
                if 'career-kit://writing-policy' not in {str(item.uri) for item in resources.resources}:
                    raise ValueError('Writing policy resource missing')
                policy=await session.read_resource('career-kit://writing-policy')
                if not policy.contents or not policy.contents[0].text:
                    raise ValueError('Writing policy resource unreadable')
                invalid=await session.call_tool('career_context',{'query':'SQL','limit':0})
                if json.loads(invalid.content[0].text)['outcome']!='needs_input':
                    raise ValueError('Invalid input was not rejected')
                return {'outcome':'ok','fictional_only':True,'transport':'stdio',
                        'tools':len(tools),'handshake':'passed','retrieval':'passed',
                        'writing_brief':'passed','resource_read':'passed','invalid_input':'rejected',
                        'model_api_calls':0,'host_settings_changed':False,'applications_submitted':0}


def main():
    with tempfile.TemporaryDirectory(prefix='career-mcp-check-') as temp:
        directory=Path(temp)/'fictional workspace'
        demo(directory)
        result=asyncio.run(verify(directory))
    print(json.dumps(result))


if __name__=='__main__':
    main()
