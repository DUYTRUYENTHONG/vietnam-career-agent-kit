#!/usr/bin/env python3
"""Run a real local MCP handshake on disposable fictional data, then clean up."""
import asyncio
import hashlib
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


async def verify_source(directory):
    """Exercise the explicit one-tool mode without touching a legacy ledger."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    (directory/'data').mkdir(parents=True)
    source=directory/'source.txt'
    source.write_text('Fictional AI-assisted API prototype.',encoding='utf8')
    fact={'fact_id':'F1','exact_claim':source.read_text(encoding='utf8'),
          'approval_state':'approved','conflict':None,'source_path':'source.txt',
          'locator':'line 1','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    (directory/'data/source-facts.json').write_text(json.dumps([fact]),encoding='utf8')
    legacy=directory/'data/applications.sqlite3'
    legacy.write_bytes(b'fictional legacy sentinel')
    before={p:p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    parameters=StdioServerParameters(command=sys.executable,
        args=[str(ROOT/'scripts/career_mcp.py'),'--data-dir',str(directory),'--source-memory'],
        env={'PYTHONUTF8':'1'})
    async with asyncio.timeout(45):
        async with stdio_client(parameters) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                tools=(await session.list_tools()).tools
                if [tool.name for tool in tools]!=['career_source_context'] or not tools[0].annotations.readOnlyHint:
                    raise ValueError('Source-memory mode must expose only its read-only context tool')
                result=await session.call_tool('career_source_context',{'query':'API'})
                packet=json.loads(result.content[0].text)
                if (packet['outcome']!='ok' or packet['data']['facts'][0]['id']!='F1'
                        or packet['data']['application_database_opened'] or packet['data']['model_api_calls']):
                    raise ValueError('Source-memory retrieval did not pass')
                invalid=await session.call_tool('career_source_context',{'query':'API','limit':0})
                if json.loads(invalid.content[0].text)['outcome']!='needs_input':
                    raise ValueError('Source-memory invalid input was not rejected')
                if before!={p:p.read_bytes() for p in directory.rglob('*') if p.is_file()}:
                    raise ValueError('Source-memory wrote to the fictional workspace')
                source.write_text('Changed fictional evidence.',encoding='utf8')
                stale=await session.call_tool('career_source_context',{'query':'API'})
                if json.loads(stale.content[0].text)['outcome']!='needs_input':
                    raise ValueError('Source-memory accepted changed evidence')
    if legacy.read_bytes()!=b'fictional legacy sentinel' or (directory/'workflow.sqlite3').exists():
        raise ValueError('Source-memory touched or initialized an application ledger')
    return {'outcome':'ok','tools':['career_source_context'],'stale_source':'rejected',
            'application_database_opened':False,'model_api_calls':0,'host_settings_changed':False}


def main():
    with tempfile.TemporaryDirectory(prefix='career-mcp-check-') as temp:
        directory=Path(temp)/'fictional workspace'
        demo(directory)
        result=asyncio.run(verify(directory))
        result['source_memory']=asyncio.run(verify_source(Path(temp)/'fictional source workspace'))
    print(json.dumps(result))


if __name__=='__main__':
    main()
