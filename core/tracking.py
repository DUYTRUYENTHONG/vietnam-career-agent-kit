"""Fast read-only ledger projection; never a content or execution authorization."""
import json
from datetime import datetime, timedelta, timezone

from .contracts import ContractError, Outcome
from .ledger import canonical_hash, utc_now
from .workflow import WorkflowError


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


def throughput(work, target, window_minutes=60):
    """Read-only rolling confirmation KPI. Old records without frozen fit stay separate."""
    if type(target) is not int or not 1<=target<=10_000:
        raise ContractError('target: choose an integer from 1 to 10000')
    if type(window_minutes) is not int or not 1<=window_minutes<=1440:
        raise ContractError('window_minutes: choose an integer from 1 to 1440')
    end=datetime.fromisoformat(utc_now()).astimezone(timezone.utc)
    start=end-timedelta(minutes=window_minutes)
    with work._db() as db:
        db.execute('BEGIN')
        if db.execute('PRAGMA user_version').fetchone()[0]<3:
            raise WorkflowError('needs_input','Execution schema 3 is required for a confirmation KPI; run compatible init first')
        rows=db.execute('SELECT job_id,recorded_utc,snapshot_json,snapshot_sha256 FROM execution_submissions').fetchall()
    qualifying=other_fit=unrecorded=0
    seen=set()
    for row in rows:
        if not isinstance(row['recorded_utc'],str):
            raise WorkflowError('blocked','Invalid confirmation timestamp; reconcile the ledger')
        try:
            recorded=datetime.fromisoformat(row['recorded_utc'].replace('Z','+00:00'))
        except (ValueError,TypeError) as error:
            raise WorkflowError('blocked','Invalid confirmation timestamp; reconcile the ledger') from error
        if recorded.tzinfo is None:
            raise WorkflowError('blocked','Confirmation timestamp lacks a timezone; reconcile the ledger')
        if not start<recorded<=end:
            continue
        if row['job_id'] in seen:
            raise WorkflowError('blocked','Duplicate confirmation job; reconcile the ledger')
        seen.add(row['job_id'])
        snapshot=json.loads(row['snapshot_json'])
        if not isinstance(snapshot,dict) or canonical_hash(snapshot)!=row['snapshot_sha256']:
            raise WorkflowError('blocked','Confirmation snapshot integrity failed; KPI cannot be trusted')
        fit=snapshot.get('fit_classification')
        if fit in {'Strong fit','Plausible fit'}:
            qualifying+=1
        elif fit is None:
            unrecorded+=1
        else:
            other_fit+=1
    return Outcome('ok',{'schema_version':'1.0','window_start_utc':start.isoformat(),
        'window_end_utc':end.isoformat(),'window_minutes':window_minutes,'target':target,
        'qualifying_confirmations':qualifying,'other_fit_confirmations':other_fit,
        'fit_unrecorded_confirmations':unrecorded,'target_met':qualifying>=target,
        'remaining':max(0,target-qualifying),'observed_per_hour':round(qualifying*60/window_minutes,3),
        'validates_artifacts':False,
        'basis':'Unique host-observed confirmations recorded in (start, end]; frozen fit is Strong fit or Plausible fit. '
                'Attempts, drafts and prior user reports are excluded. This does not revalidate suitability or files.'},[])
