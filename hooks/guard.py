#!/usr/bin/env python3
"""Optional conservative preparation-only hook helper. Not a global sandbox."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
WRITE_TOOLS={'write','edit','apply_patch','multiedit'}
RECOGNIZABLE_CONTROL=re.compile(r'browser|computer|cua|sky|upload|submit|send.?mail',re.I)

def checked_data_dir(path):
    result=Path(path).expanduser().resolve()
    if result==ROOT or result.is_relative_to(ROOT) or ROOT.is_relative_to(result):
        raise ValueError('hook data directory must be separate from the framework')
    return result

def read_event(stream):
    raw=stream.read(65537)
    if len(raw)>65536:raise ValueError('hook input exceeds 64 KiB')
    try:value=json.loads(raw)
    except json.JSONDecodeError as error:raise ValueError('invalid hook JSON') from error
    if not isinstance(value,dict):raise ValueError('hook event must be an object')
    return value

def handle(event,host,data_dir):
    if host not in {'codex','claude'}:raise ValueError('unsupported host protocol')
    name=event.get('hook_event_name')
    tool=str(event.get('tool_name',''))
    if name=='PreToolUse' and RECOGNIZABLE_CONTROL.search(tool):
        return {'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny',
            'permissionDecisionReason':'Preparation-only guard: generic UI/transmission tools cannot prove recipient and effect. Prepare a reviewed package and hand off; this starter hook does not authorize browser writes.'}}
    if name=='PostToolUse' and tool.casefold() in WRITE_TOOLS:
        if data_dir is None:
            return {'systemMessage':'Approval invalidation unavailable: no private data directory. Treat reviews and approvals as stale; use manual handling.'}
        directory=checked_data_dir(data_dir)
        directory.mkdir(parents=True,exist_ok=True)
        value={'invalidated_utc':datetime.now(timezone.utc).isoformat(),'reason':'files_changed'}
        target=directory/'approvals-invalidated.json'
        temporary=directory/('approval-marker-'+str(os.getpid())+'.tmp')
        temporary.write_text(json.dumps(value),encoding='utf8')
        os.replace(temporary,target)
        return {'systemMessage':'File edit observed. Earlier local approvals are stale; check the exact current package before any disclosure.'}
    if name=='SessionStart':
        return {'systemMessage':'Vietnam career kit: preparation-only. Use the approved private directory and check unfinished ledger state. No background browsing or submission is authorized by this hook.'}
    if name=='Stop':
        return {'systemMessage':'Report actual artifacts, verified application states and blockers. Do not infer submission or restart work automatically.'}
    return {}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',required=True,choices=['codex','claude'])
    parser.add_argument('--data-dir',type=Path)
    args=parser.parse_args()
    try:
        directory=checked_data_dir(args.data_dir) if args.data_dir else None
        result=handle(read_event(sys.stdin),args.host,directory)
    except (ValueError,OSError) as error:
        # A nonzero hook process may fail open in some hosts. Never emit allow.
        print('Career hook unavailable; manual handling required: '+type(error).__name__,file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0

if __name__=='__main__':raise SystemExit(main())
