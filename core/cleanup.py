"""Source-bound tab cleanup after an immutable confirmation, via host tools."""
import json
import uuid

from .contracts import ContractError,Outcome,object_fields,text,version
from .ledger import canonical_hash,utc_now
from .workflow import WorkflowError


def _schema(db):
    schema=db.execute('PRAGMA user_version').fetchone()[0]
    if schema not in {3,4,5,6}:
        raise WorkflowError('blocked' if schema>6 else 'needs_input','Use compatible execution schema 3/4/5/6 for tab cleanup')


def _closed(db,run_id):
    rows=db.execute("SELECT receipt FROM execution_actions WHERE run_id=? AND action='cleanup'",(run_id,)).fetchall()
    return {r['request_id']:r for row in rows if (r:=json.loads(row['receipt']))['status'] in {'closed','already_absent'}}


def _pending(work,db,run_id):
    _schema(db);_,flow=work._run(db,run_id)
    closed=_closed(db,run_id);requests=[];blocked=[]
    rows=db.execute('SELECT s.* FROM execution_submissions s JOIN execution_attempts a ON a.id=s.attempt_id WHERE a.run_id=? ORDER BY s.recorded_utc',(run_id,)).fetchall()
    rows=[row for row in rows if 'cleanup-'+row['id'] not in closed]
    latest={}
    if rows:
        # Binding IDs are meaningful only inside their explicit host bridge.
        # A later inspect/fill may have reused a completed application's tab.
        for action in db.execute("SELECT a.job_id,a.payload,a.receipt,r.payload AS run_payload FROM execution_actions a JOIN execution_runs r ON r.id=a.run_id WHERE a.action<>'cleanup' ORDER BY a.rowid"):
            request=json.loads(action['payload'])
            receipt=json.loads(action['receipt']) if action['receipt'] else {}
            binding=receipt.get('binding_id') or request.get('binding_id')
            if binding:
                bridge=json.loads(action['run_payload'])['bridge_id']
                latest[(bridge,binding)]=action['job_id']
    for row in rows:
        request_id='cleanup-'+row['id']
        try:
            snapshot=json.loads(row['snapshot_json'])
            if canonical_hash(snapshot)!=row['snapshot_sha256']:
                raise ValueError('Invalid confirmation snapshot')
            image=snapshot['evidence']['screenshot'];path=work.inside(image['path'])
            if not path.is_file() or work.hash_file(path)!=image['sha256']:
                raise ValueError('Saved screenshot unavailable or changed')
            entry=snapshot['entry']
            if latest.get((flow['bridge_id'],snapshot['binding_id']))!=row['job_id']:
                blocked.append({'job_id':row['job_id'],'reason':'Application binding was reused; preserve the current tab.'})
                continue
            requests.append({'schema_version':'1.0','request_id':request_id,
                'action':'close_application_tab','job_id':row['job_id'],
                'bridge_id':flow['bridge_id'],'binding_id':snapshot['binding_id'],'employer':entry['employer'],
                'requisition':entry['requisition'],'destination':entry['destination'],
                'screenshot':image,'requires_agent_owned':True,'requires_cleanup_request':True})
        except (KeyError,ValueError,OSError,WorkflowError):
            blocked.append({'job_id':row['job_id'],'reason':'Confirmation evidence unavailable or changed; preserve the application tab.'})
    return {'run_id':run_id,'requests':requests,'blocked':blocked,
            'browser_closed_by_core':False,'basis':'Saved confirmation and host-reported cleanup; not independently authenticated.'}


def pending(work,run_id):
    with work._db() as db:data=_pending(work,db,run_id)
    return Outcome('ok',data,['Tab cleanup is blocked; reconcile evidence and current binding ownership.'] if data['blocked'] else [])


def record(work,run_id,receipt):
    object_fields(receipt,{'schema_version','request_id','bridge_id','binding_id','status','agent_owned','cleanup_requested'},
                  {'reason'},'cleanup receipt');version(receipt,'cleanup receipt')
    for key in ['request_id','bridge_id','binding_id']:text(receipt[key],key)
    if (receipt['status'] not in {'closed','already_absent','failed'} or
            type(receipt['agent_owned']) is not bool or type(receipt['cleanup_requested']) is not bool):
        raise ContractError('Invalid cleanup status or intent/ownership flags')
    if receipt['status']=='failed':text(receipt.get('reason'),'reason')
    elif not (receipt['agent_owned'] and receipt['cleanup_requested']):
        raise WorkflowError('blocked','Close only a known agent-owned application tab when cleanup was requested')
    if 'reason' in receipt:text(receipt['reason'],'reason')
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE');_schema(db);work._run(db,run_id)
        previous=_closed(db,run_id).get(receipt['request_id'])
        if previous:
            if canonical_hash(previous)!=canonical_hash(receipt):
                raise WorkflowError('blocked','A successful cleanup receipt cannot be rewritten')
            return Outcome('ok',{'run_id':run_id,'cleanup_recorded':True,'already_recorded':True,'tab_closed':True},[])
        item=next((r for r in _pending(work,db,run_id)['requests'] if r['request_id']==receipt['request_id']),None)
        if not item or any(receipt[key]!=item[key] for key in ['bridge_id','binding_id']):
            raise WorkflowError('blocked','Cleanup is not eligible for this exact confirmed application binding')
        db.execute('INSERT INTO execution_actions(id,run_id,job_id,action,payload,receipt,created_utc,completed_utc) VALUES(?,?,?,?,?,?,?,?)',
            (uuid.uuid4().hex,run_id,item['job_id'],'cleanup',json.dumps(item,ensure_ascii=False),json.dumps(receipt,ensure_ascii=False),utc_now(),utc_now()))
        work._event(db,'application_tab_cleanup_recorded',item['job_id'],receipt['status']);db.commit()
    return Outcome('ok',{'run_id':run_id,'cleanup_recorded':True,'already_recorded':False,
                         'tab_closed':receipt['status'] in {'closed','already_absent'}},[])


def through_bridge(work,run_id,bridge,requests,attempted):
    """An explicit optional handler supplies cleanup intent/ownership checks."""
    handler=getattr(bridge,'close_application_tab',None);issues=[]
    if not callable(handler):return issues
    for item in requests:
        if item['request_id'] in attempted:continue
        attempted.add(item['request_id'])
        try:
            current=work.cleanup_execution(run_id).data['requests']
            if not any(canonical_hash(item)==canonical_hash(candidate) for candidate in current):
                issues.append('Tab cleanup deferred: the application binding or saved evidence changed; preserve the current tab.')
                continue
            work.record_cleanup(run_id,handler(item))
        except Exception as error:
            issues.append('Tab cleanup failed ('+type(error).__name__+'); preserve the confirmed application and reconcile cleanup separately.')
    return issues
