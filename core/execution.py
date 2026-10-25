"""Durable, sequential application execution through an explicit agent-host bridge.

This module does not acquire a browser session. The selected host performs each
request using its supported tools and returns a source-bound receipt. Neither a
bridge ID nor a local receipt authenticates the host, a human, or platform policy.
"""
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import uuid

from .contracts import ContractError, Outcome, object_fields, strings, text, version
from .documents import TERMINAL
from .ledger import canonical_hash, utc_now
from .manifests import Campaign, now_utc, timestamp
from .workflow import WorkflowError


class Executor(Campaign):
    def init(self, language='en'):
        super().init(language)
        statements=[
            'CREATE TABLE IF NOT EXISTS execution_runs(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE REFERENCES campaign_manifests(fingerprint), owner TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, deadline_utc TEXT NOT NULL, created_utc TEXT NOT NULL)',
            "CREATE UNIQUE INDEX IF NOT EXISTS execution_one_active ON execution_runs((1)) WHERE state='active'",
            'CREATE TABLE IF NOT EXISTS execution_actions(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES execution_runs(id), job_id INTEGER NOT NULL REFERENCES jobs(id), action TEXT NOT NULL, payload TEXT NOT NULL, receipt TEXT, created_utc TEXT NOT NULL, completed_utc TEXT)',
            'CREATE TABLE IF NOT EXISTS execution_attempts(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES execution_runs(id), job_id INTEGER NOT NULL UNIQUE REFERENCES jobs(id), fingerprint TEXT NOT NULL, snapshot_json TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL, created_utc TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS execution_submissions(id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE REFERENCES execution_attempts(id), job_id INTEGER NOT NULL UNIQUE REFERENCES jobs(id), snapshot_json TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL, recorded_utc TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS campaign_authorizations(fingerprint TEXT PRIMARY KEY,payload TEXT NOT NULL,approved_utc TEXT,revoked_utc TEXT,reason TEXT,created_utc TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS manifest_authorizations(fingerprint TEXT PRIMARY KEY REFERENCES campaign_manifests(fingerprint),authorization_fingerprint TEXT NOT NULL REFERENCES campaign_authorizations(fingerprint),allocated_submissions INTEGER NOT NULL CHECK(allocated_submissions BETWEEN 0 AND 100))',
        ]
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            for statement in statements:db.execute(statement)
            for table in ['execution_attempts','execution_submissions']:
                for operation in ['UPDATE','DELETE']:
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable execution evidence'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS execution_actions_no_rewrite BEFORE UPDATE ON execution_actions WHEN OLD.receipt IS NOT NULL OR NEW.payload<>OLD.payload OR NEW.id<>OLD.id OR NEW.run_id<>OLD.run_id OR NEW.job_id<>OLD.job_id OR NEW.action<>OLD.action OR NEW.created_utc<>OLD.created_utc BEGIN SELECT RAISE(ABORT,'immutable action or completed receipt'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS execution_actions_no_delete BEFORE DELETE ON execution_actions BEGIN SELECT RAISE(ABORT,'append-only actions'); END")
            for operation in ['UPDATE','DELETE']:
                db.execute(f"CREATE TRIGGER IF NOT EXISTS manifest_authorizations_no_{operation.lower()} BEFORE {operation} ON manifest_authorizations BEGIN SELECT RAISE(ABORT,'immutable standing allocation'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS campaign_authorizations_no_rewrite BEFORE UPDATE ON campaign_authorizations WHEN NEW.fingerprint<>OLD.fingerprint OR NEW.payload<>OLD.payload OR NEW.created_utc<>OLD.created_utc BEGIN SELECT RAISE(ABORT,'immutable standing scope'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS campaign_authorizations_no_delete BEFORE DELETE ON campaign_authorizations BEGIN SELECT RAISE(ABORT,'append-only standing scopes'); END")
            from .research_store import migrate
            migrate(db)
            from .parallel_execution import migrate_parallel
            migrate_parallel(db)
            db.commit()
        return Outcome('ok',{'workspace':str(self.data_dir),'schema':6,'language':self.language()},[])

    def _run(self, db, run_id):
        row=db.execute('SELECT * FROM execution_runs WHERE id=?',(run_id,)).fetchone()
        if not row:raise WorkflowError('needs_input','Unknown execution run')
        if row['owner']!=self.actor:raise WorkflowError('blocked','A different coordinator owns this run')
        payload=json.loads(row['payload'])
        if 'lanes' in payload and not getattr(self,'_parallel_lane',False):
            raise WorkflowError('blocked','Use parallel execution commands for this run')
        return dict(row),payload

    def _pending_action(self, db, run_id):
        return db.execute('SELECT * FROM execution_actions WHERE run_id=? AND receipt IS NULL',(run_id,)).fetchone()

    def _manifest_snapshot(self, fingerprint):
        with self._db() as db:
            row=db.execute('SELECT payload FROM campaign_manifests WHERE fingerprint=?',(fingerprint,)).fetchone()
        if not row:raise WorkflowError('blocked','Execution manifest disappeared')
        payload=json.loads(row[0])
        if canonical_hash(payload)!=fingerprint:raise WorkflowError('blocked','Execution manifest integrity failed')
        return payload

    def _save(self, db, run, payload, state='active'):
        db.execute('UPDATE execution_runs SET payload=?,state=? WHERE id=?',
                   (json.dumps(payload,ensure_ascii=False),state,run['id']))

    def _job_state(self, db, job_id, state):
        db.execute('UPDATE jobs SET state=?,version=version+1,updated_utc=? WHERE id=?',
                   (state,utc_now(),job_id))

    def start_execution(self, fingerprint, bridge_id, runtime_minutes, *, _flow_factory=None):
        text(bridge_id,'bridge_id')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.check_manifest(fingerprint)
            manifest=self.current_manifest(fingerprint)
            if (not manifest.get('execution_enabled') or
                    manifest.get('execution')!={'bridge_id':bridge_id,'runtime_minutes':runtime_minutes} or
                    type(runtime_minutes) is not int):
                raise WorkflowError('blocked','Review a new manifest explicitly binding this host bridge and runtime; preparation-only approvals cannot execute')
            if db.execute("SELECT 1 FROM execution_runs WHERE state='active' OR fingerprint=?",(fingerprint,)).fetchone():
                raise WorkflowError('blocked','Resume/stop the existing run; one coordinator and one run per approved scope')
            for entry in manifest['entries']:
                if (self.get_job(entry['job_id'])['state'] in TERMINAL or
                        db.execute('SELECT 1 FROM execution_attempts WHERE job_id=?',(entry['job_id'],)).fetchone()):
                    raise WorkflowError('blocked','Previously attempted, submitted or uncertain vacancy cannot be retried')
            run_id=uuid.uuid4().hex
            deadline=min(now_utc()+timedelta(minutes=runtime_minutes),timestamp(manifest['expires_utc'],'expiry'))
            payload={'entry_index':0,'step':'inspect','binding_id':None,'inspection':None,
                     'bridge_id':bridge_id,'attempt_id':None}
            if _flow_factory is not None:
                payload=_flow_factory(db,manifest,payload)
            db.execute('INSERT INTO execution_runs VALUES(?,?,?,?,?,?,?)',
                (run_id,fingerprint,self.actor,'active',json.dumps(payload),deadline.isoformat(),utc_now()))
            self._event(db,'execution_started',run_id,fingerprint);db.commit()
        return Outcome('ok',{'run_id':run_id,'state':'active','deadline_utc':deadline.isoformat(),
                             'bridge_id':bridge_id,'browser_connected':False},
                       ['Host must bind its explicitly authorized browser session; no browser is acquired by this command.'])

    def launch_execution(self,fingerprint,authorization,bridge_id,runtime_minutes):
        from .dispatch import launch
        return launch(self,fingerprint,authorization,bridge_id,runtime_minutes)

    def _frozen_document(self, entry):
        source=self.inside(entry['document']['path'])
        data=source.read_bytes()
        if hashlib.sha256(data).hexdigest()!=entry['document_sha256']:
            raise WorkflowError('blocked','Approved upload bytes changed')
        relative='execution/documents/'+entry['document_sha256']+'/'+source.name
        target=self.inside(relative);target.parent.mkdir(parents=True,exist_ok=True)
        try:
            with target.open('xb') as stream:stream.write(data)
        except FileExistsError:
            if target.read_bytes()!=data:raise WorkflowError('blocked','Frozen document integrity failed')
        return self.file_record(target)

    def _disclosure_check(self, run, entry, action):
        if now_utc()>=timestamp(run['deadline_utc'],'runtime deadline'):
            raise WorkflowError('blocked','Execution runtime expired; stop this run and approve a fresh finite scope')
        intent=None
        if action in {'fill','upload','submit'}:
            intent={k:entry[k] for k in ['job_id','destination','document_sha256','answers_sha256','consents_sha256']}
            intent.update(schema_version='1.0',action=action)
        self.check_manifest(run['fingerprint'],intent)
        if now_utc()>=timestamp(run['deadline_utc'],'runtime deadline'):
            raise WorkflowError('blocked','Execution runtime expired during validation; approve a fresh finite scope')

    def next_action(self, run_id):
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');run,flow=self._run(db,run_id)
            if run['state']!='active':return self._status(run,flow)
            manifest=self._manifest_snapshot(run['fingerprint'])
            pending=self._pending_action(db,run_id)
            if pending:
                if pending['action']!='submit':
                    raise WorkflowError('needs_input','An action is outstanding; record its receipt or stop. Never replay a pending browser mutation blindly.')
                # Recovery closes the issued click request, not the attempt. No second click.
                db.execute('UPDATE execution_actions SET receipt=?,completed_utc=? WHERE id=?',
                    (json.dumps({'status':'unknown','source':'engine_recovery','reason':'Submit receipt missing; read-only verification only'}),utc_now(),pending['id']))
                flow['step']='verify'
                self._event(db,'submission_recovery',flow['attempt_id'],'never reissue submit')
            if flow['entry_index']>=len(manifest['entries']):
                state='assisted' if manifest['mode']=='ASSIST' else 'completed'
                self._save(db,run,flow,state);db.commit();run['state']=state
                return self._status(run,flow)
            entry=manifest['entries'][flow['entry_index']];action=flow['step']
            if action!='verify':self._disclosure_check(run,entry,action)
            consumed=db.execute('SELECT count(*) FROM execution_attempts WHERE fingerprint=?',(run['fingerprint'],)).fetchone()[0]
            if action=='inspect' and manifest['mode']=='APPROVED_BATCH' and consumed>=manifest['submission_limit']:
                self._save(db,run,flow,'completed_limit');db.commit();run['state']='completed_limit'
                return self._status(run,flow)
            request={'schema_version':'1.0','request_id':uuid.uuid4().hex,'run_id':run_id,
                'job_id':entry['job_id'],'action':action,'binding_id':flow['binding_id'],
                'destination':entry['destination'],'employer':entry['employer'],'requisition':entry['requisition'],
                'manifest_fingerprint':run['fingerprint'],'bridge_id':flow['bridge_id']}
            request['deadline_utc']=run['deadline_utc']
            if action=='fill':
                request['values']={k:v['value'] for k,v in entry['answers'].items() if k in flow['inspection']['fields']}
                request['consents']=entry['consents']
            if action=='upload':request['document']=self._frozen_document(entry)
            if action=='review':
                request.update(values={k:v['value'] for k,v in entry['answers'].items() if k in flow['inspection']['fields']},
                               consents=entry['consents'],document_sha256=entry['document_sha256'])
            if action=='submit':
                if consumed>=manifest['submission_limit']:
                    raise WorkflowError('blocked','Submission budget exhausted')
                if db.execute('SELECT 1 FROM execution_attempts WHERE job_id=?',(entry['job_id'],)).fetchone():
                    raise WorkflowError('blocked','Vacancy already has a durable attempt; verify instead of retrying')
                flow['attempt_id']=uuid.uuid4().hex
                snapshot={'manifest_fingerprint':run['fingerprint'],'entry':entry,'binding_id':flow['binding_id'],
                          'actor':self.actor,'document':self._frozen_document(entry),
                          'fit_classification':self.current_draft(entry['job_id'])['classification']}
                db.execute('INSERT INTO execution_attempts VALUES(?,?,?,?,?,?,?)',
                    (flow['attempt_id'],run_id,entry['job_id'],run['fingerprint'],json.dumps(snapshot,ensure_ascii=False),canonical_hash(snapshot),utc_now()))
                self._job_state(db,entry['job_id'],'submission_uncertain')
                self._event(db,'submission_attempt_started',flow['attempt_id'],'durable before returning submit request')
            if action in {'submit','verify'}:request['attempt_id']=flow['attempt_id']
            db.execute('INSERT INTO execution_actions(id,run_id,job_id,action,payload,receipt,created_utc) VALUES(?,?,?,?,?,?,?)',
                (request['request_id'],run_id,entry['job_id'],action,json.dumps(request,ensure_ascii=False),None,utc_now()))
            self._save(db,run,flow);db.commit()
        return Outcome('ok',{'run_id':run_id,'state':'active','request':request},[])

    def _status(self, run, flow):
        state=run['state']
        cleanup=self.cleanup_execution(run['id'])
        return Outcome('submission_unknown' if state=='submission_unknown' else 'ok',
                       {'run_id':run['id'],'state':state,'entry_index':flow['entry_index'],'cleanup':cleanup.data},cleanup.issues)

    def _validate_identity(self, receipt, request):
        for key in ['binding_id','url','employer','requisition']:text(receipt[key],key,empty=key=='requisition')
        if ((request['binding_id'] is not None and receipt['binding_id']!=request['binding_id']) or
                receipt['employer']!=request['employer'] or receipt['requisition']!=request['requisition']):
            raise WorkflowError('blocked','Browser binding/employer/requisition differs from exact approval')
        actual=urlsplit(receipt['url']);expected=urlsplit(request['destination'])
        if request['action']=='verify':
            valid=(actual.scheme,actual.hostname,actual.port)==(expected.scheme,expected.hostname,expected.port)
            valid=valid and not actual.username and not actual.password
        else:valid=receipt['url']==request['destination']
        if not valid:raise WorkflowError('manual_required','Application redirected outside its approved destination; review before any further disclosure')

    def _inspect(self, receipt, entry):
        strings(receipt['fields'],'fields');strings(receipt['required_fields'],'required_fields')
        strings(receipt['blockers'],'blockers');strings(receipt['upload_extensions'],'upload_extensions')
        if receipt['blockers']:raise WorkflowError('manual_required','Resolve page challenges/legal terms/new consent directly: '+', '.join(receipt['blockers']))
        if (not set(receipt['required_fields'])<=set(receipt['fields']) or
                not set(receipt['required_fields'])<=entry['answers'].keys() or
                not set(entry['required_answers'])<=set(receipt['fields'])):
            raise WorkflowError('needs_input','The actual form contains unknown required answers; approve an updated exact scope')
        if 'upload' in entry['operations'] and Path(entry['document']['path']).suffix.lower() not in receipt['upload_extensions']:
            raise WorkflowError('manual_required','Form does not accept the approved document format')
        if not isinstance(receipt['consents'],list):raise ContractError('consents must be a list')
        observed={}
        for consent in receipt['consents']:
            object_fields(consent,{'id','text','required'},set(),'observed consent')
            if type(consent['required']) is not bool or consent['id'] in observed:raise ContractError('Invalid/duplicate consent')
            text(consent['id'],'consent.id');text(consent['text'],'consent.text');observed[consent['id']]=consent
        approved={c['id']:c for c in entry['consents']}
        if (any(c['required'] and i not in approved for i,c in observed.items()) or
                any(i not in observed or observed[i]['text']!=c['text'] for i,c in approved.items())):
            raise WorkflowError('needs_input','Consent text or required consent differs from reviewed manifest')

    def _evidence(self, receipt):
        text(receipt['confirmation_text'],'confirmation_text')
        text(receipt['screenshot'],'screenshot')
        path=self.inside(receipt['screenshot'])
        if not path.is_file() or not 16<=path.stat().st_size<=20_000_000:
            raise WorkflowError('blocked','A private screenshot is required for observed confirmation')
        data=path.read_bytes()
        suffix='.png' if data.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if data.startswith(b'\xff\xd8\xff') else None
        if suffix is None:raise WorkflowError('blocked','Confirmation evidence is not a PNG/JPEG screenshot')
        digest=hashlib.sha256(data).hexdigest()
        relative='execution/evidence/'+digest+suffix;target=self.inside(relative)
        target.parent.mkdir(parents=True,exist_ok=True)
        try:
            with target.open('xb') as stream:stream.write(data)
        except FileExistsError:
            if target.read_bytes()!=data:raise WorkflowError('blocked','Frozen screenshot integrity failed')
        return {'screenshot':self.file_record(target),'text':receipt['confirmation_text'],'url':receipt['url']}

    def record_action(self, run_id, receipt):
        common={'schema_version','request_id','binding_id','url','employer','requisition','status'}
        optional={'form','consents','values','document_sha256','confirmed','confirmation_text','screenshot','reason'}
        object_fields(receipt,common,optional,'browser receipt');version(receipt,'browser receipt')
        if receipt['status'] not in {'ok','failed','unknown','manual_required'}:raise ContractError('Invalid receipt status')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');run,flow=self._run(db,run_id)
            row=db.execute('SELECT * FROM execution_actions WHERE id=? AND run_id=?',
                (receipt['request_id'],run_id)).fetchone()
            if run['state']!='active' or not row or row['receipt'] is not None:
                raise WorkflowError('blocked','Receipt is stale, replayed or belongs to another run')
            request=json.loads(row['payload']);action=request['action']
            phase_keys={'inspect':{'form'},'fill':{'form'},'upload':{'form','document_sha256'},
                'review':{'form','values','consents','document_sha256'},'submit':set(),
                'verify':{'confirmed','confirmation_text','screenshot'}}
            if set(receipt)-common-phase_keys[action]-{'reason'}:
                raise ContractError('Receipt contains fields for another action')
            self._validate_identity(receipt,request)
            manifest=self._manifest_snapshot(run['fingerprint']);entry=manifest['entries'][flow['entry_index']]
            if row['job_id']!=entry['job_id']:
                raise WorkflowError('blocked','Receipt belongs to another application lane')
            if receipt['status']=='ok' and action in {'inspect','fill','upload','review'}:
                form=object_fields(receipt.get('form'),{'fields','required_fields','consents','upload_extensions','blockers'},set(),'form observation')
                self._inspect(form,entry)
                if flow['inspection'] is not None and canonical_hash(form)!=canonical_hash(flow['inspection']):
                    raise WorkflowError('needs_input','Form fields, consents or accepted files changed; review a new exact scope')
            state='active'
            if receipt['status']!='ok':
                state='submission_unknown' if flow['attempt_id'] else 'stopped'
            elif action=='inspect':
                flow.update(binding_id=receipt['binding_id'],inspection=receipt['form'])
            elif action=='upload':
                if receipt.get('document_sha256')!=entry['document_sha256']:
                    raise WorkflowError('blocked','Upload receipt differs from exact approved document')
            elif action=='review':
                if (canonical_hash(receipt.get('values'))!=canonical_hash(request['values']) or
                        canonical_hash(receipt.get('consents'))!=canonical_hash(request['consents']) or
                        receipt.get('document_sha256')!=entry['document_sha256']):
                    raise WorkflowError('blocked','Final visible form review differs from approved answers, file or consents')
                self._job_state(db,entry['job_id'],'form_prepared')
            elif action=='verify':
                if type(receipt.get('confirmed')) is not bool:raise ContractError('Verification requires an explicit boolean confirmed value')
                if receipt['confirmed']:
                    evidence=self._evidence(receipt)
                    attempt=db.execute('SELECT * FROM execution_attempts WHERE id=?',(flow['attempt_id'],)).fetchone()
                    if not attempt:raise WorkflowError('blocked','Submission attempt disappeared')
                    snapshot=json.loads(attempt['snapshot_json'])
                    if canonical_hash(snapshot)!=attempt['snapshot_sha256']:raise WorkflowError('blocked','Attempt snapshot integrity failed')
                    document=self.inside(snapshot['document']['path'])
                    if self.hash_file(document)!=snapshot['document']['sha256']:raise WorkflowError('blocked','Frozen submitted document changed')
                    snapshot.update(evidence=evidence,evidence_kind='observed_host_receipt',recorded_utc=utc_now())
                    db.execute('INSERT INTO execution_submissions VALUES(?,?,?,?,?,?)',
                        (uuid.uuid4().hex,flow['attempt_id'],entry['job_id'],json.dumps(snapshot,ensure_ascii=False),canonical_hash(snapshot),utc_now()))
                    self._job_state(db,entry['job_id'],'confirmed_submitted')
                    self._event(db,'submission_confirmed',entry['job_id'],canonical_hash(snapshot))
                else:state='submission_unknown'
            db.execute('UPDATE execution_actions SET receipt=?,completed_utc=? WHERE id=?',
                (json.dumps(receipt,ensure_ascii=False),utc_now(),receipt['request_id']))
            if state=='submission_unknown':self._job_state(db,entry['job_id'],'submission_uncertain')
            if state=='active' and flow.get('recovery_only'):
                state='recovered'
            elif state=='active':
                steps=['inspect']+[x for x in ['fill','upload'] if x in entry['operations']]+['review']
                if manifest['mode']=='APPROVED_BATCH':steps+=['submit','verify']
                position=steps.index(action)+1
                if position==len(steps):
                    if manifest['mode']=='ASSIST':self._job_state(db,entry['job_id'],'awaiting_manual_submission')
                    flow.update(entry_index=flow['entry_index']+1,step='inspect',binding_id=None,inspection=None,attempt_id=None)
                else:flow['step']=steps[position]
            self._save(db,run,flow,state)
            self._event(db,'browser_action_recorded',receipt['request_id'],action+': '+receipt['status']);db.commit()
        run['state']=state
        return self._status(run,flow)

    def recover_execution(self, run_id):
        """Reconcile one uncertain attempt, never resume its submit or other jobs."""
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');run,flow=self._run(db,run_id)
            if run['state']!='submission_unknown' or not flow['attempt_id']:
                raise WorkflowError('blocked','Only an uncertain durable attempt can enter read-only recovery')
            if db.execute("SELECT 1 FROM execution_runs WHERE state='active'").fetchone():
                raise WorkflowError('blocked','Another coordinator run is active')
            flow.update(step='verify',recovery_only=True)
            self._save(db,run,flow);self._event(db,'read_only_recovery_started',run_id,flow['attempt_id']);db.commit()
        return Outcome('ok',{'run_id':run_id,'state':'active','recovery_only':True},[])

    def advance_execution(self, run_id, receipt):
        """Commit a receipt, then issue one successor. Never repeat either on error.

        Two transactions intentionally preserve the receipt if the successor is
        blocked. A lost response is reconciled with execution-status, not replay.
        """
        recorded=self.record_action(run_id,receipt)
        try:
            result=self.next_action(run_id) if recorded.data['state']=='active' else recorded
        except WorkflowError as error:
            return Outcome(error.outcome,{'run_id':run_id,'receipt_recorded':True,
                'recorded_request_id':receipt['request_id'],'cleanup':recorded.data['cleanup']},[str(error)])
        result.data['cleanup']=recorded.data['cleanup']
        result.data.update(receipt_recorded=True,recorded_request_id=receipt['request_id'])
        return result

    def cleanup_execution(self,run_id):
        from .cleanup import pending
        return pending(self,run_id)

    def record_cleanup(self,run_id,receipt):
        from .cleanup import record
        return record(self,run_id,receipt)

    def tracker(self):
        from .tracking import checkpoint
        return checkpoint(self)

    def throughput(self, target, window_minutes=60):
        from .tracking import throughput
        return throughput(self,target,window_minutes)

    def stop_execution(self, run_id, reason):
        text(reason,'reason')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');run,flow=self._run(db,run_id)
            if run['state']!='active':return self._status(run,flow)
            state='submission_unknown' if flow['attempt_id'] else 'stopped'
            if flow['attempt_id']:
                attempt=db.execute('SELECT job_id FROM execution_attempts WHERE id=?',(flow['attempt_id'],)).fetchone()
                self._job_state(db,attempt['job_id'],'submission_uncertain')
            db.execute('UPDATE execution_actions SET receipt=?,completed_utc=? WHERE run_id=? AND receipt IS NULL',
                (json.dumps({'status':'unknown','source':'engine_stop','reason':reason}),utc_now(),run_id))
            self._save(db,run,flow,state);self._event(db,'execution_stopped',run_id,reason);db.commit()
        run['state']=state
        return self._status(run,flow)

    def execution_status(self, run_id):
        with self._db() as db:
            run,flow=self._run(db,run_id)
            actions=[dict(r) for r in db.execute('SELECT id,job_id,action,created_utc,completed_utc FROM execution_actions WHERE run_id=? ORDER BY created_utc',(run_id,))]
        result=self._status(run,flow);result.data.update(actions=actions,deadline_utc=run['deadline_utc'])
        return result

    def check_action(self, run_id, request_id):
        """Host calls immediately before performing an issued action; never replays it."""
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');run,flow=self._run(db,run_id)
            row=db.execute('SELECT payload FROM execution_actions WHERE id=? AND run_id=? AND receipt IS NULL',
                           (request_id,run_id)).fetchone()
            if run['state']!='active' or not row:raise WorkflowError('blocked','Action is not pending in this active run')
            request=json.loads(row['payload'])
            if request['action']!='verify':
                manifest=self._manifest_snapshot(run['fingerprint'])
                self._disclosure_check(run,manifest['entries'][flow['entry_index']],request['action'])
        return Outcome('ok',{'run_id':run_id,'request_id':request_id,'action':request['action'],'current':True},[])

    def resume(self):
        result=super().resume()
        with self._db() as db:
            if db.execute('PRAGMA user_version').fetchone()[0]<3:return result
            runs=[dict(r) for r in db.execute('SELECT id,fingerprint,state,deadline_utc FROM execution_runs ORDER BY created_utc')]
            attempts=db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0]
            submitted=db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0]
            action_receipts=db.execute("SELECT receipt FROM execution_actions WHERE receipt IS NOT NULL AND action IN ('fill','upload','submit')").fetchall()
            observed_actions=sum(json.loads(row['receipt']).get('status')=='ok' for row in action_receipts)
        result.data.update(execution_runs=runs,execution_attempts=attempts,observed_submissions=submitted,
                           mode='EXECUTION' if runs else 'PREPARE',external_actions=observed_actions,
                           external_actions_basis='Successful host action receipts; not independent platform verification')
        message=('Đã tải trạng thái; số hồ sơ có xác nhận từ trình duyệt: ' if self.language()=='vi' else
                 'Checkpoint loaded; host-observed confirmed applications: ')+str(submitted)
        return Outcome(result.outcome,result.data,result.issues,message)


def run_with_bridge(work, run_id, bridge):
    """Run sequentially with a caller-supplied supported BrowserBridge.perform.

    Exceptions stop mutations. A possibly issued submit remains durable and may
    only resume as verification. No automatic exception retry is performed.
    """
    from .cleanup import through_bridge
    cleanup_issues=[];attempted_cleanup=set()
    while True:
        outcome=work.next_action(run_id)
        request=outcome.data.get('request')
        if request is None:
            cleanup_issues.extend(through_bridge(work,run_id,bridge,outcome.data['cleanup']['requests'],attempted_cleanup))
            outcome.data['cleanup']=work.cleanup_execution(run_id).data
            outcome.issues.extend(cleanup_issues);return outcome
        work.check_action(run_id,request['request_id'])
        receipt=bridge.perform(request)
        result=work.record_action(run_id,receipt)
        if request['action']=='verify' and receipt.get('confirmed'):
            cleanup_issues.extend(through_bridge(work,run_id,bridge,result.data['cleanup']['requests'],attempted_cleanup))
            result.data['cleanup']=work.cleanup_execution(run_id).data
        if result.data['state']!='active':
            result.issues.extend(cleanup_issues);return result
