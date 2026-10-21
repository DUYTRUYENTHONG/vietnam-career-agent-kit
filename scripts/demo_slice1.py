#!/usr/bin/env python3
"""Run the fictional local preparation demonstration without model/network calls."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.workflow import Preparation, WorkflowError


def demo(directory: Path, candidate: str = 'a') -> dict:
    if directory.exists() and any(directory.iterdir()):
        raise WorkflowError('blocked','Demo requires a new empty directory; it never overwrites an existing candidate workspace')
    fixtures=ROOT/'examples/fictional'
    load=lambda name:json.loads((fixtures/name).read_text(encoding='utf8'))
    work=Preparation(directory,actor='fictional-demo')
    work.init('vi' if candidate=='b' else 'en')
    work.import_cv(fixtures/f'cv-{candidate}.md','CV1')
    imported=work.import_profile(load(f'profile-{candidate}.json'))
    fingerprint=imported.data['fingerprint']
    proof=work.atomic_text('fictional-profile-review.txt','CONFIRM PROFILE '+fingerprint)
    work.confirm_profile(fingerprint,proof)
    suffix='-b' if candidate=='b' else ''
    job_id=work.import_job(load(f'job{suffix}.json')).data['job']['id']
    assessment=work.assess(job_id,load(f'matrix{suffix}.json'))
    draft=work.prepare(job_id,load(f'plan{suffix}.json'))
    report=work.atomic_text('reports/checkpoint.json',json.dumps(work.resume().json(),ensure_ascii=False,indent=2))
    return {'schema_version':'1.0','outcome':'ok','data':{'fictional_only':True,
        'workspace':str(directory),'fit':assessment.data['classification'],'draft':draft.data,
        'checkpoint':str(report),'handoff':work.handoff(job_id).json(),
        'notice':'The generated confirmation belongs only to fictional fixtures; never fabricate approval for a real candidate.'},'issues':[]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,help='new empty private directory outside this checkout')
    parser.add_argument('--candidate',choices=['a','b'],default='a')
    args=parser.parse_args()
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    try:
        if args.data_dir:result=demo(args.data_dir.resolve(),args.candidate)
        else:
            with tempfile.TemporaryDirectory(prefix='career-kit-fictional-') as temp:
                result=demo(Path(temp)/'private',args.candidate)
                result['data']['temporary_workspace_removed_after_check']=True
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        return 0
    except (WorkflowError,ValueError,OSError) as error:
        print(json.dumps({'schema_version':'1.0','outcome':'blocked','data':{},'issues':[str(error)]}))
        return 2


if __name__=='__main__':raise SystemExit(main())
