"""Bounded application sessions; only the coordinator touches the durable ledger.

BrowserBridge.perform must support independent per-job bindings and concurrent
calls. It must not automatically retry mutations. Provider integration is separate.
"""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json

from .contracts import ContractError, Outcome, text
from .execution import Executor
from .ledger import utc_now
from .workflow import WorkflowError


def migrate_parallel(db):
    """Schema 6 retains immutable evidence and permits one pending action per job.

    Called within init's BEGIN IMMEDIATE transaction. Old clients reject schema6;
    new sequential APIs still enforce one pending action for the complete run.
    """
    if db.execute('PRAGMA user_version').fetchone()[0] < 6:
        db.execute('DROP INDEX IF EXISTS execution_one_pending')
        db.execute('CREATE UNIQUE INDEX execution_one_pending_per_job ON execution_actions(run_id,job_id) WHERE receipt IS NULL')
        db.execute('PRAGMA user_version=6')


class _Lane(Executor):
    _parallel_lane = True

    def __init__(self, coordinator, job_id):
        super().__init__(coordinator.data_dir, actor=coordinator.actor)
        self.job_id = job_id

    def _run(self, db, run_id):
        run, payload = super()._run(db, run_id)
        lane = payload.get('lanes', {}).get(str(self.job_id))
        if lane is None:
            raise WorkflowError('blocked', 'Unknown application lane')
        run['state'] = lane['state']
        return run, dict(lane['flow'])

    def _pending_action(self, db, run_id):
        pending=db.execute('SELECT * FROM execution_actions WHERE run_id=? AND job_id=? AND receipt IS NULL',
                           (run_id, self.job_id)).fetchone()
        if pending is None:
            payload=json.loads(db.execute('SELECT payload FROM execution_runs WHERE id=?',(run_id,)).fetchone()[0])
            count=db.execute('SELECT count(*) FROM execution_actions WHERE run_id=? AND receipt IS NULL',(run_id,)).fetchone()[0]
            if count>=payload['workers']:
                raise WorkflowError('needs_input','All parallel application slots have outstanding actions')
        return pending

    def _save(self, db, run, flow, state='active'):
        row = db.execute('SELECT payload FROM execution_runs WHERE id=?', (run['id'],)).fetchone()
        payload = json.loads(row['payload'])
        lane = payload['lanes'][str(self.job_id)]
        if flow['entry_index'] != lane['index']:
            state = 'completed'
            flow['entry_index'] = lane['index']
        lane.update(state=state, flow=flow)
        states = {item['state'] for item in payload['lanes'].values()}
        overall = ('active' if 'active' in states else
                   'submission_unknown' if 'submission_unknown' in states else
                   'stopped' if 'stopped' in states else 'completed')
        db.execute('UPDATE execution_runs SET payload=?,state=? WHERE id=?',
                   (json.dumps(payload, ensure_ascii=False), overall, run['id']))

    def _status(self, run, flow):
        with self._db() as db:
            current, _ = self._run(db, run['id'])
        return Outcome('submission_unknown' if current['state']=='submission_unknown' else 'ok',
                       {'run_id':run['id'], 'job_id':self.job_id, 'state':current['state']}, [])

    def _validate_identity(self, receipt, request):
        super()._validate_identity(receipt, request)
        # Binding reuse across simultaneous lanes would couple otherwise distinct
        # forms. Reject it before recording even the initial inspection receipt.
        with self._db() as db:
            row = db.execute('SELECT payload FROM execution_runs WHERE id=?', (request['run_id'],)).fetchone()
        lanes = json.loads(row['payload'])['lanes']
        if any(int(job)!=self.job_id and lane['flow']['binding_id']==receipt['binding_id']
               for job,lane in lanes.items()):
            raise WorkflowError('blocked', 'Browser binding already belongs to another application lane')


class ParallelExecutor(Executor):
    def start_parallel_execution(self, fingerprint, bridge_id, runtime_minutes, workers=10):
        if type(workers) is not int or not 1 <= workers <= 10:
            raise ContractError('Application workers must be 1-10')
        def initial_flow(db,manifest,base):
            if db.execute('PRAGMA user_version').fetchone()[0]!=6:
                raise WorkflowError('needs_input','Initialize this workspace to migrate to execution schema 6')
            if manifest['mode'] != 'APPROVED_BATCH':
                raise WorkflowError('blocked', 'Parallel execution requires an approved application batch')
            lanes = {}
            for index, entry in enumerate(manifest['entries']):
                lanes[str(entry['job_id'])] = {'index':index,
                    'state':'active' if index < manifest['submission_limit'] else 'completed_limit',
                    'flow':dict(base, entry_index=index)}
            return {'parallel_version':'1.0', 'workers':workers, 'bridge_id':bridge_id, 'lanes':lanes}
        result=self.start_execution(fingerprint,bridge_id,runtime_minutes,_flow_factory=initial_flow)
        run_id=result.data['run_id']
        return self.parallel_status(run_id)

    def parallel_status(self, run_id):
        with self._db() as db:
            row = db.execute('SELECT * FROM execution_runs WHERE id=?', (run_id,)).fetchone()
            if not row or row['owner'] != self.actor:
                raise WorkflowError('blocked', 'Unknown run or different coordinator')
            payload = json.loads(row['payload'])
            if 'lanes' not in payload:
                raise WorkflowError('blocked', 'Run is not a parallel application batch')
            pending = [dict(item) for item in db.execute(
                'SELECT id,job_id,action FROM execution_actions WHERE run_id=? AND receipt IS NULL', (run_id,))]
        return Outcome('submission_unknown' if row['state']=='submission_unknown' else 'ok',
            {'run_id':run_id, 'state':row['state'], 'workers':payload['workers'],
             'lanes':[{'job_id':int(job), 'state':lane['state'], 'step':lane['flow']['step'],
                       'binding_id':lane['flow']['binding_id']} for job,lane in payload['lanes'].items()],
             'pending':pending}, [])

    def _lane_for_request(self, run_id, request_id):
        self.parallel_status(run_id)
        with self._db() as db:
            row = db.execute('SELECT job_id FROM execution_actions WHERE run_id=? AND id=?', (run_id,request_id)).fetchone()
        if not row:
            raise WorkflowError('blocked', 'Unknown application request')
        return _Lane(self, row['job_id'])

    def next_parallel_action(self, run_id, job_id):
        self.parallel_status(run_id)
        return _Lane(self, job_id).next_action(run_id)

    def check_parallel_action(self, run_id, request_id):
        return self._lane_for_request(run_id,request_id).check_action(run_id,request_id)

    def record_parallel_action(self, run_id, receipt):
        if not isinstance(receipt,dict):
            raise ContractError('Browser receipt must be an object')
        return self._lane_for_request(run_id,receipt.get('request_id')).record_action(run_id,receipt)

    def _cleanup_lane(self, run_id):
        status=self.parallel_status(run_id)
        return _Lane(self,status.data['lanes'][0]['job_id'])

    def parallel_cleanup(self, run_id):
        # Cleanup uses immutable submission snapshots, not the lane's current
        # step or binding, and works after revocation or another lane's failure.
        return self._cleanup_lane(run_id).cleanup_execution(run_id)

    def record_parallel_cleanup(self, run_id, receipt):
        return self._cleanup_lane(run_id).record_cleanup(run_id,receipt)

    def stop_parallel_lane(self, run_id, job_id, reason):
        text(reason, 'reason')
        lane = _Lane(self, job_id)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            run, flow = lane._run(db, run_id)
            if run['state'] != 'active':
                return Outcome('ok', {'run_id':run_id,'job_id':job_id,'state':run['state']}, [])
            state = 'submission_unknown' if flow['attempt_id'] else 'stopped'
            if flow['attempt_id']:
                self._job_state(db, job_id, 'submission_uncertain')
            db.execute('UPDATE execution_actions SET receipt=?,completed_utc=? WHERE run_id=? AND job_id=? AND receipt IS NULL',
                (json.dumps({'status':'unknown','source':'engine_stop','reason':reason}),utc_now(),run_id,job_id))
            lane._save(db,run,flow,state)
            self._event(db,'parallel_lane_stopped',str(job_id),reason)
            db.commit()
        return self.parallel_status(run_id)

    def stop_parallel_execution(self, run_id, reason):
        for lane in self.parallel_status(run_id).data['lanes']:
            self.stop_parallel_lane(run_id,lane['job_id'],reason)
        return self.parallel_status(run_id)

    def recover_parallel_execution(self, run_id, job_id):
        lane = _Lane(self, job_id)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            run, flow = lane._run(db,run_id)
            if run['state']!='submission_unknown' or not flow['attempt_id']:
                raise WorkflowError('blocked','Only an uncertain durable attempt can recover')
            if db.execute("SELECT 1 FROM execution_runs WHERE state='active' AND id<>?",(run_id,)).fetchone():
                raise WorkflowError('blocked','Another coordinator run is active')
            flow.update(step='verify',recovery_only=True)
            lane._save(db,run,flow)
            self._event(db,'parallel_read_only_recovery',str(job_id),flow['attempt_id'])
            db.commit()
        return self.parallel_status(run_id)


def run_parallel_with_bridge(work, run_id, bridge):
    """Execute up to ten independent sessions, recording receipts out of order.

    All ledger operations execute on this caller's thread. Only perform runs in
    workers. Restart refuses outstanding actions: reconcile or explicitly stop
    each affected lane; a possible submit can only be verified afterward.
    """
    status = work.parallel_status(run_id)
    if status.data['pending']:
        raise WorkflowError('needs_input','Outstanding actions require reconciliation before restarting workers')
    workers = status.data['workers']
    errors = [];cleanup_issues=[];attempted_cleanup=set()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {}
        while True:
            status = work.parallel_status(run_id)
            busy = {job for job,request_id in pending.values()}
            for lane in status.data['lanes']:
                if len(pending)>=workers:
                    break
                job = lane['job_id']
                if lane['state']!='active' or job in busy:
                    continue
                try:
                    outcome = work.next_parallel_action(run_id,job)
                    request = outcome.data.get('request')
                    if request is None:
                        continue
                    work.check_parallel_action(run_id,request['request_id'])
                    pending[pool.submit(bridge.perform,request)] = (job,request['request_id'])
                except Exception:
                    work.stop_parallel_lane(run_id,job,'Coordinator validation failed; reconcile this lane')
                    errors.append({'job_id':job,'stage':'preflight'})
            if not pending:
                result = work.parallel_status(run_id)
                result.data['worker_errors'] = errors
                cleanup=work.parallel_cleanup(run_id)
                from .cleanup import through_bridge
                cleanup_issues.extend(through_bridge(work._cleanup_lane(run_id),run_id,bridge,
                                                    cleanup.data['requests'],attempted_cleanup))
                cleanup=work.parallel_cleanup(run_id)
                result.data['cleanup']=cleanup.data
                result.issues.extend(cleanup_issues+cleanup.issues)
                return result
            done,_ = wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                job,request_id = pending.pop(future)
                try:
                    receipt=future.result()
                    if not isinstance(receipt,dict) or receipt.get('request_id')!=request_id:
                        raise WorkflowError('blocked','Worker returned another application request receipt')
                    work.record_parallel_action(run_id,receipt)
                    if receipt.get('confirmed') is True:
                        from .cleanup import through_bridge
                        lane_work=work._cleanup_lane(run_id)
                        requests=work.parallel_cleanup(run_id).data['requests']
                        cleanup_issues.extend(through_bridge(lane_work,run_id,bridge,requests,attempted_cleanup))
                except Exception:
                    work.stop_parallel_lane(run_id,job,'Browser action or receipt failed; never automatically retry')
                    errors.append({'job_id':job,'stage':'perform_or_receipt'})
