"""Private source-bound recruitment observations; no hiring or model authority."""
from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import re

from .contracts import ContractError, Outcome, choice, object_fields, version
from .ledger import canonical_hash, utc_now
from .manifests import timestamp
from .workflow import WorkflowError

KINDS = {'acknowledged', 'screening_passed', 'shortlisted', 'assessment_invited',
         'interview_invited', 'rejected', 'offer_received', 'withdrawn'}
MAX_SUBMISSIONS = 10_000
MAX_EVENTS = 20_000
MAX_TOTAL_BYTES = 20_000_000
MAX_SOURCE_BYTES = 262_144
MAX_EVENT_BYTES = 16_384


def _time(value, label):
    if not isinstance(value,str) or not 1 <= len(value) <= 64:
        raise ContractError(label+': bounded explicit UTC timestamp required')
    return timestamp(value,label)


def _identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', value):
        raise ContractError(label+': bounded identifier required')


def _hash(value, label):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ContractError(label+': SHA256 required')


def _shape(event):
    object_fields(event, {'schema_version','event_id','job_id','submission_id',
        'submission_sha256','document_sha256','kind','received_utc','observed_utc',
        'retracts_event_id','source'}, set(), 'CV outcome')
    version(event, 'CV outcome')
    for key in ('event_id','submission_id'):
        _identifier(event[key], key)
    if type(event['job_id']) is not int or not 1 <= event['job_id'] <= 2**63-1:
        raise ContractError('job_id: positive integer required')
    for key in ('submission_sha256','document_sha256'):
        _hash(event[key], key)
    choice(event['kind'], KINDS | {'retract'}, 'kind')
    received = _time(event['received_utc'], 'received_utc')
    observed = _time(event['observed_utc'], 'observed_utc')
    if received > observed:
        raise ContractError('received_utc cannot follow observed_utc')
    if event['kind'] == 'retract':
        _identifier(event['retracts_event_id'], 'retracts_event_id')
    elif event['retracts_event_id'] is not None:
        raise ContractError('Only a retract event names retracts_event_id')
    source = object_fields(event['source'], {'kind','path','sha256'}, set(), 'source')
    choice(source['kind'], {'employer_message','portal_observation','manual_record'}, 'source.kind')
    if not isinstance(source['path'], str) or not 0 < len(source['path']) <= 4096:
        raise ContractError('source.path: bounded private path required')
    _hash(source['sha256'], 'source.sha256')
    return received, observed


def _proof(work, source):
    path = work.inside(source['path'])
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_SOURCE_BYTES:
        raise WorkflowError('needs_input', 'Select a nonempty private outcome source of at most 256 KiB')
    with path.open('rb') as stream:
        raw = stream.read(MAX_SOURCE_BYTES+1)
    if not 0 < len(raw) <= MAX_SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise WorkflowError('blocked', 'Outcome source bytes changed')


def _workspace(work, db):
    if not 3 <= db.execute('PRAGMA user_version').fetchone()[0] <= 6:
        raise WorkflowError('needs_input', 'Portable execution schema 3–6 required; outcomes never migrate a legacy tracker')
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'execution_submissions','execution_attempts'} <= tables:
        raise WorkflowError('needs_input', 'Execution confirmation tables are missing; preserve and inspect this workspace')


def _feature(db, create=False):
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    present = tables & {'cv_outcome_meta','cv_outcome_events'}
    if present and len(present) != 2:
        raise WorkflowError('blocked', 'Incomplete CV outcome feature; inspect without resetting history')
    if not present:
        if not create:
            return False
        db.execute('CREATE TABLE cv_outcome_meta(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)')
        db.execute('INSERT INTO cv_outcome_meta VALUES(1,1)')
        db.execute('CREATE TABLE cv_outcome_events(event_id TEXT PRIMARY KEY, submission_id TEXT NOT NULL '
                   'REFERENCES execution_submissions(id), job_id INTEGER NOT NULL REFERENCES jobs(id), '
                   'fingerprint TEXT NOT NULL, payload TEXT NOT NULL, recorded_utc TEXT NOT NULL)')
        db.execute('CREATE INDEX cv_outcome_submission ON cv_outcome_events(submission_id)')
        for operation in ('UPDATE','DELETE'):
            db.execute('CREATE TRIGGER cv_outcomes_no_'+operation.lower()+' BEFORE '+operation+
                       " ON cv_outcome_events BEGIN SELECT RAISE(ABORT,'CV outcomes are append-only'); END")
    row = db.execute('SELECT version FROM cv_outcome_meta WHERE id=1').fetchone()
    if row is None or row[0] != 1:
        raise WorkflowError('blocked', 'Unsupported CV outcome feature version')
    return True


def _submission(row):
    raw = row['snapshot_json']
    if not isinstance(raw, str) or len(raw.encode('utf8')) > 1_000_000:
        raise WorkflowError('blocked', 'Invalid or oversized historical confirmation')
    try:
        snap = json.loads(raw)
        valid = (canonical_hash(snap) == row['snapshot_sha256'] and
                 snap['entry']['job_id'] == row['job_id'] and
                 snap['document']['sha256'] == snap['entry']['document_sha256'] and
                 row['state'] == 'confirmed_submitted')
        _hash(snap['document']['sha256'], 'historical CV hash')
        recorded = timestamp(row['recorded_utc'], 'confirmation time')
        attempted = timestamp(row['attempted_utc'], 'attempt time')
        if not valid or attempted > recorded:
            raise ValueError('Inconsistent confirmation')
    except (KeyError, TypeError, ValueError) as error:
        raise WorkflowError('blocked', 'Historical submission linkage/integrity failed; reconcile without rewriting it') from error
    return snap, recorded, attempted


BASE_SELECT = ('SELECT s.*,a.created_utc AS attempted_utc,j.state FROM execution_submissions s '
               'LEFT JOIN execution_attempts a ON a.id=s.attempt_id AND a.job_id=s.job_id '
               'JOIN jobs j ON j.id=s.job_id ')


def record(work, event):
    if not work.db_path.is_file():
        raise WorkflowError('needs_input', 'Initialize the selected portable workspace first')
    event = deepcopy(event)
    received, observed = _shape(event)
    payload = json.dumps(event,ensure_ascii=False)
    if len(payload.encode('utf8')) > MAX_EVENT_BYTES:
        raise ContractError('CV outcome exceeds the 16 KiB serialized UTF-8 limit; shorten the source path')
    if observed > timestamp(utc_now(), 'now'):
        raise ContractError('observed_utc cannot be future-dated')
    _proof(work, event['source'])
    fingerprint = canonical_hash(event)
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE')
        _workspace(work, db)
        size = db.execute('SELECT length(CAST(snapshot_json AS BLOB)) FROM execution_submissions WHERE id=?',
                          (event['submission_id'],)).fetchone()
        if not size or size[0] is None or size[0] > 1_000_000:
            raise WorkflowError('needs_input', 'Select a bounded confirmed portable-engine submission')
        row = db.execute(BASE_SELECT+'WHERE s.id=?', (event['submission_id'],)).fetchone()
        if row is None:
            raise WorkflowError('needs_input', 'Submission/attempt/job linkage is missing')
        snap, _, attempted = _submission(row)
        if (row['job_id'] != event['job_id'] or row['snapshot_sha256'] != event['submission_sha256'] or
                snap['document']['sha256'] != event['document_sha256'] or received < attempted):
            raise WorkflowError('blocked', 'Outcome belongs to a different submission/CV or predates its attempt')
        present = _feature(db)
        if event['kind'] == 'retract':
            target = db.execute('SELECT payload,fingerprint,recorded_utc FROM cv_outcome_events WHERE event_id=?',
                                (event['retracts_event_id'],)).fetchone() if present else None
            if target is None:
                raise ContractError('Retraction requires an existing outcome for this submission')
            original = json.loads(target['payload'])
            if (canonical_hash(original) != target['fingerprint'] or original['kind'] == 'retract' or
                    original['submission_id'] != event['submission_id'] or
                    timestamp(original['observed_utc'], 'original observation') > observed):
                raise ContractError('Retraction must correct an earlier non-retraction outcome for the same submission')
        _feature(db, create=True)
        old = db.execute('SELECT fingerprint FROM cv_outcome_events WHERE event_id=?', (event['event_id'],)).fetchone()
        if old and old[0] != fingerprint:
            raise WorkflowError('blocked', 'Outcome ID already names different bytes; use an explicit correction')
        if not old:
            db.execute('INSERT INTO cv_outcome_events VALUES(?,?,?,?,?,?)', (event['event_id'],
                event['submission_id'],event['job_id'],fingerprint,payload,utc_now()))
        db.commit()
    return Outcome('ok', {'event_id':event['event_id'],'fingerprint':fingerprint,'reused':bool(old),
        'basis':'Caller-classified outcome bound to source bytes and a frozen confirmed CV; employer identity/content not authenticated.'}, [])


def report(work, *, min_age_days=14, as_of=None, job_ids=None):
    if not work.db_path.is_file():
        raise WorkflowError('needs_input', 'Initialize the selected portable workspace first')
    if type(min_age_days) is not int or not 0 <= min_age_days <= 3650:
        raise ContractError('min_age_days: integer 0..3650 required')
    if job_ids is not None and (not isinstance(job_ids,list) or not 1 <= len(job_ids) <= 1000 or
            any(type(i) is not int or not 1 <= i <= 2**63-1 for i in job_ids) or len(set(job_ids)) != len(job_ids)):
        raise ContractError('job_ids: 1..1000 unique positive IDs, or omit for all confirmations')
    now = timestamp(utc_now(), 'now')
    end = _time(as_of, 'as_of') if as_of is not None else now
    if end > now:
        raise ContractError('as_of cannot be future-dated')
    where = 'WHERE s.job_id IN ('+','.join('?' for _ in job_ids)+')' if job_ids is not None else ''
    params = tuple(job_ids or [])
    with work._db() as db:
        db.execute('BEGIN')
        _workspace(work, db)
        sizes = db.execute('SELECT s.id,length(CAST(s.snapshot_json AS BLOB)) AS bytes FROM execution_submissions s '+
                           where+' LIMIT ?', (*params,MAX_SUBMISSIONS+1)).fetchall()
        if (len(sizes) > MAX_SUBMISSIONS or any(r['bytes'] is None or r['bytes'] > 1_000_000 for r in sizes) or
                sum(r['bytes'] for r in sizes) > MAX_TOTAL_BYTES):
            raise WorkflowError('needs_input', 'Confirmation report exceeds bounded input; select fewer job IDs')
        rows = db.execute(BASE_SELECT+where+' ORDER BY s.job_id', params).fetchall()
        if _feature(db):
            event_where = 'WHERE e.job_id IN ('+','.join('?' for _ in job_ids)+')' if job_ids is not None else ''
            sizes = db.execute('SELECT length(CAST(e.payload AS BLOB)) AS bytes FROM cv_outcome_events e '+
                               event_where+' LIMIT ?', (*params,MAX_EVENTS+1)).fetchall()
            if (len(sizes) > MAX_EVENTS or any(r['bytes'] is None or r['bytes'] > MAX_EVENT_BYTES for r in sizes) or
                    sum(r['bytes'] for r in sizes) > MAX_TOTAL_BYTES):
                raise WorkflowError('needs_input', 'Outcome report exceeds bounded input; select fewer job IDs')
            events = db.execute('SELECT e.* FROM cv_outcome_events e '+event_where+' ORDER BY e.event_id',params).fetchall()
        else:
            events = []
    submissions = {}
    for row in rows:
        snap, recorded, _ = _submission(row)
        if recorded <= end:
            submissions[row['id']] = {'job_id':row['job_id'],'submission_sha256':row['snapshot_sha256'],
                'document_sha256':snap['document']['sha256'],'recorded_utc':recorded,
                'eligible':recorded <= end-timedelta(days=min_age_days)}
    available = []
    proof_cache = {}
    proof_bytes = 0
    for row in events:
        try:
            event = json.loads(row['payload']);_shape(event)
            if (canonical_hash(event) != row['fingerprint'] or event['event_id'] != row['event_id'] or
                    event['job_id'] != row['job_id'] or event['submission_id'] != row['submission_id']):
                raise ValueError('Outcome identity changed')
            recorded = timestamp(row['recorded_utc'],'outcome record time')
            if timestamp(event['observed_utc'],'observed_utc') > recorded:
                raise ValueError('Invalid observation chronology')
            if recorded > end or event['submission_id'] not in submissions:
                continue
            sub = submissions[event['submission_id']]
            if (event['job_id'] != sub['job_id'] or event['submission_sha256'] != sub['submission_sha256'] or
                    event['document_sha256'] != sub['document_sha256']):
                raise ValueError('Outcome confirmation binding changed')
        except (ValueError,TypeError,KeyError) as error:
            raise WorkflowError('blocked','Outcome history integrity failed; preserve and inspect it') from error
        key = (event['source']['path'],event['source']['sha256'])
        if key not in proof_cache:
            try:
                source_size = work.inside(key[0]).stat().st_size
            except (ValueError,OSError):
                source_size = 0
            if proof_bytes+min(source_size,MAX_SOURCE_BYTES+1) > MAX_TOTAL_BYTES:
                raise WorkflowError('needs_input','Outcome source verification exceeds 20 MB; select fewer job IDs')
            proof_bytes += min(source_size,MAX_SOURCE_BYTES+1)
            try:
                _proof(work,event['source']);proof_cache[key] = True
            except (ValueError,OSError):
                proof_cache[key] = False
        verified = proof_cache[key]
        available.append((event,verified))
    # A recorded correction remains conservative even if its source later disappears.
    retracted = {e['retracts_event_id'] for e,_ in available if e['kind'] == 'retract'}
    active = defaultdict(set)
    for event,verified in available:
        if verified and event['kind'] != 'retract' and event['event_id'] not in retracted:
            active[event['submission_id']].add(event['kind'])
    groups = {}
    for sid,sub in submissions.items():
        digest = sub['document_sha256']
        group = groups.setdefault(digest,{'document_sha256':digest,'eligible_applications':0,
            'recent_applications':0,'no_recorded_response':0,'outcome_counts':{k:0 for k in sorted(KINDS)}})
        if not sub['eligible']:
            group['recent_applications'] += 1
            continue
        group['eligible_applications'] += 1
        if not active[sid]:
            group['no_recorded_response'] += 1
        for kind in active[sid]:
            group['outcome_counts'][kind] += 1
    for group in groups.values():
        n = group['eligible_applications']
        group['outcome_rates'] = {k:round(v/n,6) if n else None for k,v in group['outcome_counts'].items()}
    return Outcome('ok',{'schema_version':'1.0','as_of_utc':end.isoformat(),'min_age_days':min_age_days,
        'confirmed_submissions':len(submissions),'eligible_submissions':sum(s['eligible'] for s in submissions.values()),
        'recent_submissions':sum(not s['eligible'] for s in submissions.values()),'event_count':len(available),
        'unverified_events':sum(not good for _,good in available),'cv_groups':[groups[k] for k in sorted(groups)],
        'applications':[{'submission_id':sid,**{k:v for k,v in sub.items() if k!='recorded_utc'},
                         'recorded_utc':sub['recorded_utc'].isoformat(),
                         'active_evidenced_outcomes':sorted(active[sid])} for sid,sub in submissions.items()],
        'basis':'Frozen confirmed CV hashes and source-bound caller classifications available by as-of. '
                'Rates use age-eligible confirmations, categories overlap, missing/changed sources are excluded. '
                'No recorded response is not rejection or proof of a complete mailbox audit. '
                'Groups are observational, not causal model/CV rankings; no automatic training or promotion.'}, [])
