#!/usr/bin/env python3
"""Synchronize repository-owned Claude wrappers and INACTIVE hook examples."""
import argparse
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='fail on drift without writing')
    parser.add_argument('--dry-run',action='store_true',help='preview without writing')
    args=parser.parse_args()
    expected={}
    for path in sorted((ROOT/'.agents/skills').glob('*/SKILL.md')):
        source=path.read_text(encoding='utf8')
        name=re.search(r'^name: (.+)$',source,re.M).group(1)
        description=re.search(r'^description: (.+)$',source,re.M).group(1)
        expected[ROOT/'.claude/skills'/name/'SKILL.md']=(
            '---\nname: '+name+'\ndescription: '+description+'\n---\n\n'
            'Read and execute the shared skill at ../../../.agents/skills/'+name+'/SKILL.md. '
            'Read its referenced files relative to that shared skill. Follow root AGENTS.md and CLAUDE.md. '
            'This adapter grants no browser, hook, upload or submission permission.\n')
    for host in ['codex','claude']:
        command='"__PYTHON__" "__KIT_ROOT__/hooks/guard.py" --host '+host+' --data-dir "__DATA_DIR__"'
        example={'hooks':{event:[{'hooks':[{'type':'command','command':command,'timeout':5}]}]
                          for event in ['SessionStart','PreToolUse','PostToolUse','Stop']}}
        expected[ROOT/'hooks'/(host+'.example.json')]=json.dumps(example,indent=2)+'\n'
    stale=set((ROOT/'.claude/skills').glob('*/SKILL.md'))-set(expected)
    if stale:
        print('Migrate stale repository-owned adapters explicitly: '+', '.join(str(p.relative_to(ROOT)) for p in stale))
        return 1
    drift=[str(path.relative_to(ROOT)) for path,content in expected.items()
           if not path.exists() or path.read_text(encoding='utf8')!=content]
    if args.check or args.dry_run:
        print(json.dumps({'mode':'check' if args.check else 'dry_run','changed_files':drift,'active_settings_touched':False}))
        return 1 if args.check and drift else 0
    for path,content in expected.items():
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content,encoding='utf8',newline='')
    print('Generated project wrappers and inactive examples; no global/active settings.')
    return 0


if __name__=='__main__':raise SystemExit(main())
