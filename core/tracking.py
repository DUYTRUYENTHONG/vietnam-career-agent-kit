"""Fast read-only ledger projection; never a content or execution authorization."""
import json

from .contracts import Outcome
from .ledger import utc_now


def checkpoint(work):
    with work._db() as db:
        # All rows belong to one SQLite read snapshot, including the counts.
        db.execute('BEGIN')
        jobs=[dict(row) for row in db.execute('SELECT id,employer,title,url,state,liveness,updated_utc FROM jobs ORDER BY id')]
        schema=db.execute('PRAGMA user_version').fetchone()[0]
        actions=list(db.execute('SELECT a.job_id,a.action,a.receipt,a.created_utc,a.completed_utc,r.state AS run_state '
            'FROM execution_actions a JOIN execution_runs r ON r.id=a.run_id ORDER BY a.rowid')) if schema>=3 else []
        attempts=db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0] if schema>=3 else 0
        submitted=db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0] if schema>=3 else 0
    latest={row['job_id']:row for row in actions}
    for job in jobs:
        action=latest.get(job['id'])
        job.update(latest_action=None,run_state=None,blocker=None,
                   next_step='Resume and validate current evidence before continuing')
        if action:
            receipt=json.loads(action['receipt']) if action['receipt'] else None
            job.update(latest_action=action['action'],run_state=action['run_state'])
            job['updated_utc']=max(job['updated_utc'],action['completed_utc'] or action['created_utc'])
            if receipt is None:
                job['blocker']='Outstanding '+action['action']+' request'
                job['next_step']='Reconcile execution-status; do not replay a pending action'
            elif receipt.get('status')!='ok':
                job['blocker']=receipt.get('reason') or receipt.get('status','Unknown receipt outcome')
                job['next_step']='Resolve the recorded blocker; do not retry submission'
            else:
                job['next_step']='Check execution-status for the next phase; validate before acting'
        if job['state']=='confirmed_submitted':
            job['next_step']='Await employer response'
        elif job['state']=='user_reported_submitted':
            job['next_step']='Previously applied (candidate report); exclude duplicate application'
        elif job['state']=='submission_uncertain':
            job['next_step']='Verify outcome read-only; never issue another submit'
        elif job['liveness']!='active':
            job['next_step']='Verify vacancy liveness; no application while closed/unverified'
        elif job['state']=='awaiting_manual_submission':
            job['next_step']='Manual handoff; no automatic submission'
    return Outcome('ok',{'schema_version':'1.0','generated_utc':utc_now(),
        'basis':'Recorded ledger state only; artifacts, approvals and live vacancies are not revalidated',
        'validates_artifacts':False,'observed_submissions':submitted,'attempts':attempts,
        'user_reported_submissions':sum(job['state']=='user_reported_submitted' for job in jobs),
        'jobs':jobs},[])


def markdown(data):
    def cell(value):
        return str(value or '—').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('|','&#124;').replace('\r',' ').replace('\n',' ')
    lines=['# Application tracker','',data['basis']+'.','',
        f"Updated (UTC): {data['generated_utc']}",
        f"Host-observed confirmations: {data['observed_submissions']}; durable attempts: {data['attempts']}; candidate-reported prior submissions: {data['user_reported_submissions']}",'',
        '| ID | Employer / role | Source | Status | Blocker | Next step | Updated (UTC) |',
        '|---|---|---|---|---|---|---|']
    for job in data['jobs']:
        lines.append('| '+' | '.join(cell(value) for value in [job['id'],job['employer']+' — '+job['title'],
            job['url'],job['state'],job['blocker'],job['next_step'],job['updated_utc']])+' |')
    return '\n'.join(lines)+'\n'
