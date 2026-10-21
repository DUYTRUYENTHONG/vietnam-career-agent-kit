#!/usr/bin/env python3
"""Generate checked-in Claude pointer skills and INACTIVE hook examples."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]

def main():
    count=0
    for path in sorted((ROOT/'.agents/skills').glob('*/SKILL.md')):
        source=path.read_text(encoding='utf8')
        name=re.search(r'^name: (.+)$',source,re.M).group(1)
        description=re.search(r'^description: (.+)$',source,re.M).group(1)
        target=ROOT/'.claude/skills'/name/'SKILL.md';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('---\nname: '+name+'\ndescription: '+description+'\n---\n\n'
            'Read and execute the shared skill at ../../../.agents/skills/'+name+'/SKILL.md. '
            'Read its referenced files relative to that shared skill. Follow root AGENTS.md and CLAUDE.md. '
            'This adapter grants no browser, hook, upload or submission permission.\n',encoding='utf8')
        count+=1
    for host in ['codex','claude']:
        command='"__PYTHON__" "__KIT_ROOT__/hooks/guard.py" --host '+host+' --data-dir "__DATA_DIR__"'
        example={'hooks':{event:[{'hooks':[{'type':'command','command':command,'timeout':5}]}]
                          for event in ['SessionStart','PreToolUse','PostToolUse','Stop']}}
        (ROOT/'hooks'/(host+'.example.json')).write_text(json.dumps(example,indent=2)+'\n',encoding='utf8')
    print(f'Generated {count} Claude pointer adapters and two inactive hook examples.')

if __name__=='__main__':main()
