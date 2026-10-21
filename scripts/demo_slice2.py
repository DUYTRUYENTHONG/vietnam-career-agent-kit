#!/usr/bin/env python3
"""Render fictional documents for real page inspection. Never auto-review/approve."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.manifests import Campaign
from core.workflow import WorkflowError
from scripts.demo_slice1 import demo


def render_demo(directory,candidate='a',soffice=None):
    demo(directory,candidate)
    work=Campaign(directory,actor='fictional-demo');work.init()
    rendered=work.render(1,soffice).data
    review={'schema_version':'1.0','render_fingerprint':rendered['fingerprint'],'reviewed_pages':[],
        'checks':dict.fromkeys(['content','layout','glyphs','language'],False)}
    review_file=work.atomic_text('document-review.json',json.dumps(review,indent=2))
    now=datetime.now(timezone.utc)
    plan={'schema_version':'1.0','campaign_id':'fictional-demo','mode':'ASSIST',
        'expires_utc':(now+timedelta(hours=2)).isoformat(),'submission_limit':0,
        'entries':[{'job_id':1,'render_id':rendered['render_id'],'format':'pdf',
            'destination':'https://apply.example.test/fictional','operations':['fill','upload'],
            'answers':{},'required_answers':[],'consents':[],
            'policy':{'permission':'permitted','source':'https://apply.example.test/policy',
                'checked_utc':now.isoformat(),'allowed_operations':['fill','upload']}}]}
    plan_file=work.atomic_text('campaign-plan.json',json.dumps(plan,indent=2))
    return {'schema_version':'1.0','outcome':'ok','data':{'fictional_only':True,'render':rendered,
        'review_template':str(review_file),'plan_template':str(plan_file),'approved':False,
        'execution_enabled':False,'next_steps':['Inspect every page image and content.json.',
            'Complete the review template truthfully; run review-documents, then create-manifest.',
            'Inspect the exact manifest before recording approval. example.test is never contacted.']},'issues':[]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True,help='new empty external private directory')
    parser.add_argument('--candidate',choices=['a','b'],default='a')
    parser.add_argument('--soffice',type=Path)
    args=parser.parse_args()
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    try:
        result=render_demo(args.data_dir.resolve(),args.candidate,args.soffice)
    except (WorkflowError,OSError,ValueError) as error:
        result={'schema_version':'1.0','outcome':getattr(error,'outcome','failed'),'data':{},'issues':[str(error)]}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['outcome']=='ok' else 2


if __name__=='__main__':raise SystemExit(main())
