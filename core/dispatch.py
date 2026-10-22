"""Compose existing authority/start/request checks without adding permission."""
from .authorization import link,require_schema
from .contracts import Outcome,text
from .workflow import WorkflowError


def existing_run(work,fingerprint,authorization):
    with work._db() as db:
        row=db.execute('SELECT id FROM execution_runs WHERE fingerprint=?',(fingerprint,)).fetchone()
        if not row:return None
        run,flow=work._run(db,row['id'])
        pending=db.execute('SELECT action FROM execution_actions WHERE run_id=? AND receipt IS NULL',(run['id'],)).fetchone()
    origin=link(work,fingerprint)
    if not origin or origin['authorization_fingerprint']!=authorization:
        raise WorkflowError('blocked','Existing run belongs to another approval origin')
    return Outcome('needs_input' if run['state']=='active' else 'ok',
        {'run_id':run['id'],'state':run['state'],'existing_run':True,'run_started':False,
         'authority_recorded':True,'authority_revalidated':False,
         'pending_action':pending['action'] if pending else None,
         'next_step':'Reconcile with execution-status and the supported host. next-action recovers pending submit as read-only verify; never replay a browser mutation.'},
        ['Existing-run status is not renewed authority. No request, second run or new allocation was created.'])


def launch(work,fingerprint,authorization,bridge_id,runtime_minutes):
    require_schema(work);text(bridge_id,'bridge_id');text(authorization,'authorization')
    manifest=work._manifest_snapshot(fingerprint)
    if (type(runtime_minutes) is not int or
            manifest.get('execution')!={'bridge_id':bridge_id,'runtime_minutes':runtime_minutes}):
        raise WorkflowError('blocked','Launch must match the reviewed bridge and runtime exactly')
    previous=existing_run(work,fingerprint,authorization)
    if previous:return previous
    work.authorize_manifest(fingerprint,authorization)
    try:
        started=work.start_execution(fingerprint,bridge_id,runtime_minutes)
    except WorkflowError as error:
        # Another launch may have committed the same run while this one waited.
        previous=existing_run(work,fingerprint,authorization)
        if previous:return previous
        return Outcome(error.outcome,{'manifest_fingerprint':fingerprint,
            'authority_recorded':True,'run_started':False},[str(error)])
    try:
        result=work.next_action(started.data['run_id'])
    except WorkflowError as error:
        return Outcome(error.outcome,{**started.data,'authority_recorded':True,
            'run_started':True,'next_step':'Reconcile the committed run; do not launch a replacement.'},[str(error)])
    result.data.update(authority_recorded=True,run_started=True,
        approval_basis='standing_authorization',authorization_fingerprint=authorization)
    result.issues.extend(started.issues)
    return result
