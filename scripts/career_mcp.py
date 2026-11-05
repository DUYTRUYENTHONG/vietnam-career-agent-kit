#!/usr/bin/env python3
"""Launch the career-only MCP server or print local setup/configuration checks."""
import argparse
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core import career_memory
from core.parallel_execution import ParallelExecutor
from core.workflow import WorkflowError

SDK_VERSION='1.30.0'


def workspace(data_dir):
    work=ParallelExecutor(data_dir,actor='mcp-user')
    if not work.db_path.is_file() and any((work.data_dir/path).is_file()
            for path in ('applications.sqlite3','data/applications.sqlite3')):
        raise WorkflowError('needs_input','Older campaign detected: use the source-memory bridge; do not initialize a second tracker')
    try:
        career_memory.current_workspace(work)
    except sqlite3.Error as error:
        raise WorkflowError('blocked',
            'Cannot read the selected workflow database; preserve it and inspect its integrity before retrying') from error
    return work


def configuration(data_dir, python, kind, *, source_memory=False):
    # Construction validates path isolation but never creates a workspace.
    work=ParallelExecutor(data_dir,actor='mcp-user')
    executable=Path(python).expanduser().resolve(strict=True)
    if not executable.is_file():
        raise ValueError('Select an installed Python interpreter')
    entry={'command':str(executable),'args':[str(ROOT/'scripts/career_mcp.py'),'--data-dir',str(work.data_dir)]}
    name='career-source-memory' if source_memory else 'career-kit'
    if source_memory:
        entry['args'].append('--source-memory')
    if kind=='json':
        return json.dumps({'mcpServers':{name:entry}},ensure_ascii=False,indent=2)
    if kind=='codex':
        return '[mcp_servers.'+name+']\ncommand = '+json.dumps(entry['command'],ensure_ascii=False)+'\nargs = '+json.dumps(entry['args'],ensure_ascii=False)+'\n'
    raise ValueError('Configuration format must be json or codex')


def check(data_dir, *, source_memory=False):
    source_data=None
    if source_memory:
        from core.source_memory import source_context
        # Reuse path isolation only; never inspect or initialize a database.
        work=ParallelExecutor(data_dir,actor='mcp-user')
        # Validate all qualifying evidence but return no candidate quotes.
        packet=source_context(work.data_dir,'preflight',limit=1,max_chars=1)
        if packet.outcome!='ok':
            raise WorkflowError(packet.outcome,'; '.join(packet.issues))
        source_data=packet.data
    else:
        work=workspace(data_dir)
    try:
        installed=version('mcp')
    except PackageNotFoundError:
        installed=None
    report={'outcome':'ok' if installed==SDK_VERSION else 'manual_required',
            'data':{'workspace':str(work.data_dir),'transport':'stdio',
                    'mcp_version':installed,'expected_mcp_version':SDK_VERSION,
                    'workspace_exists':True,'workspace_created':False,'host_settings_changed':False,
                    'model_api_calls':0,'server_started':False},
            'issues':[] if installed==SDK_VERSION else ['Use the selected virtual environment with requirements-mcp.lock installed.']}
    if source_data is not None:
        report['data'].update(mode='source-memory',read_only=True,
            application_database_opened=False,
            verified_fact_count=source_data['verified_fact_count'],
            excluded_fact_count=source_data['excluded_fact_count'],
            exclusion_reasons=source_data['exclusion_reasons'],
            source_packet_sha256=source_data['source_packet_sha256'])
        if not source_data['verified_fact_count']:
            report['issues'].append('No reviewed hash-bound facts qualify; source-memory cannot approve or repair them.')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--source-memory',action='store_true',
                        help='explicit read-only older source-packet mode; no tracker migration')
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--check',action='store_true',help='read-only workspace and pinned-SDK preflight')
    modes.add_argument('--config',choices=['json','codex'],help='print a configuration preview; never modify host settings')
    parser.add_argument('--python',type=Path,help='interpreter for configuration preview; default is this interpreter')
    args=parser.parse_args()
    if args.python and not args.config:
        parser.error('--python is only used with --config')
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf8')
    try:
        if args.config:
            print(configuration(args.data_dir,args.python or sys.executable,args.config,source_memory=args.source_memory))
            return 0
        report=check(args.data_dir,source_memory=args.source_memory)
        if args.check:
            print(json.dumps(report,ensure_ascii=False))
            return 0 if report['outcome']=='ok' else 2
        if report['outcome']!='ok':
            raise WorkflowError(report['outcome'],report['issues'][0])
        # Protocol mode reserves stdout for MCP. No init, migrations or client registration.
        if args.source_memory:
            from scripts.source_memory import make_server
            make_server(Path(args.data_dir).expanduser().resolve()).run(transport='stdio')
        else:
            from adapters.career_mcp import make_career_server
            make_career_server(workspace(args.data_dir)).run(transport='stdio')
        return 0
    except (WorkflowError,ValueError,OSError) as error:
        result={'outcome':getattr(error,'outcome','needs_input'),'data':{},'issues':[str(error)]}
        print(json.dumps(result,ensure_ascii=False),file=sys.stdout if args.check else sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
