#!/usr/bin/env python3
"""Bounded public-source hygiene check; not a full secret or privacy scanner."""
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES={'.pdf','.docx','.sqlite','.sqlite3','.db','.png','.jpg','.zip','.pem','.key'}
FORBIDDEN_DIRS={'private','.private','data','sources','applications','screenshots','output','artifacts'}
SECRET=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9_-]{24,}|fc-[A-Za-z0-9_-]{24,}|(?:FIRECRAWL|TINYFISH)_API_KEY\s*[:=]\s*[\x22\x27]?[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
EMAIL=re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')

def issues_for(path,content):
    issues=[]
    if path.suffix.lower() in FORBIDDEN_SUFFIXES or any(p in FORBIDDEN_DIRS for p in path.parts):
        issues.append('private/runtime artifact path')
    if SECRET.search(content):issues.append('possible credential')
    personal_path_pattern=r'[A-Za-z]:[\\/]'+r'Users[\\/]|/'+r'Users/|/'+r'home/[^/]+/'
    if re.search(personal_path_pattern,content):
        issues.append('absolute personal filesystem path')
    for match in EMAIL.finditer(content):
        address=match.group(0).lower()
        if not address.endswith(('.invalid','@example.com','@example.org')):
            issues.append('nonfictional email address');break
    return issues

def main():
    result=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,
                          check=True,capture_output=True)
    paths=sorted(set(result.stdout.decode('utf8').split('\0'))-{''})
    errors=[]
    for raw in paths:
        relative=Path(raw);path=ROOT/relative
        if path.is_symlink():errors.append(raw+': public symlink requires explicit review');continue
        try:content=path.read_text(encoding='utf8')
        except UnicodeError:errors.append(raw+': non-UTF8/binary source');continue
        errors += [raw+': '+issue for issue in issues_for(relative,content)]
        if path.suffix=='.json':
            try:json.loads(content)
            except json.JSONDecodeError:errors.append(raw+': invalid JSON')
    shared=sorted((ROOT/'.agents/skills').glob('*/SKILL.md'))
    expected_skills={'onboarding','candidate-evidence','vietnam-job-discovery','job-normalization',
                     'fit-assessment','application-tailoring','document-review','campaign-approval',
                     'browser-application','application-tracking'}
    if {path.parent.name for path in shared}!=expected_skills:errors.append('expected ten canonical product skills')
    for path in shared:
        text=path.read_text(encoding='utf8')
        if not text.startswith('---\n') or not re.search(r'^name: [a-z0-9-]+$',text,re.M) or not re.search(r'^description: .+$',text,re.M):
            errors.append(str(path.relative_to(ROOT))+': invalid restricted skill frontmatter')
        adapter=ROOT/'.claude/skills'/path.parent.name/'SKILL.md'
        if not adapter.exists() or '../../../.agents/skills/'+path.parent.name+'/SKILL.md' not in adapter.read_text(encoding='utf8'):
            errors.append('missing/shared-path mismatch in Claude adapter '+path.parent.name)
    for path in [ROOT/'.codex/hooks.json',ROOT/'.claude/settings.json',ROOT/'.claude/settings.local.json']:
        if path.exists():errors.append('active host configuration must not be bundled: '+str(path.relative_to(ROOT)))
    if errors:
        print('\n'.join(errors));return 1
    print(f'PASS: {len(paths)} UTF-8 source files, ten shared skills/adapters, no flagged artifacts or credential patterns.')
    print('Bounded check only: inspect the staged diff and sources before publication.')
    return 0

if __name__=='__main__':raise SystemExit(main())
