"""Opt-in source-bound performance observations; no inferred model telemetry."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import re
from statistics import median

from .contracts import ContractError, Outcome, choice, object_fields, version
from .ledger import canonical_hash, utc_now
from .manifests import timestamp
from .workflow import WorkflowError

TOKENS = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_tokens')
STATUSES = {'success', 'failed', 'cancelled', 'unknown'}
MAX_REPORT_RECORDS = 10_000


def identifier(value, label, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', value):
        raise ContractError(label+': expected a bounded identifier, not prose or a credential')


def validate(work, event):
    object_fields(event, {'schema_version', 'event_id', 'task_id', 'workload_id', 'phase',
        'provider_id', 'model_id', 'effort', 'status', 'accepted', 'observed_utc',
        'duration_ms', 'usage', 'cost', 'source'}, set(), 'performance observation')
    version(event, 'performance observation')
    for key in ('event_id', 'task_id', 'workload_id', 'phase', 'provider_id'):
        identifier(event[key], key)
    identifier(event['model_id'], 'model_id', True)
    identifier(event['effort'], 'effort', True)
    if event['model_id'] is None and event['effort'] is not None:
        raise ContractError('Unknown model cannot have an inferred effort')
    choice(event['status'], STATUSES, 'status')
    if type(event['accepted']) is not bool or event['accepted'] and event['status'] != 'success':
        raise ContractError('Only a successful observation can be caller-reported accepted')
    timestamp(event['observed_utc'], 'observed_utc')
    duration = event['duration_ms']
    if duration is not None and (type(duration) not in (int, float) or
            not math.isfinite(duration) or not 0 <= duration <= 86_400_000):
        raise ContractError('duration_ms: finite measured milliseconds, 0..86400000, or null')
    usage = object_fields(event['usage'], {'kind', *TOKENS}, set(), 'usage')
    if usage['kind'] != 'per_call':
        raise ContractError('Normalize explicitly observed per-call usage; cumulative counters are not individual calls')
    for key in TOKENS:
        if usage[key] is not None and (type(usage[key]) is not int or not 0 <= usage[key] <= 10**12):
            raise ContractError(key+': nonnegative integer tokens or null; never characters/estimates')
    for subset, total in [('cached_input_tokens', 'input_tokens'), ('reasoning_tokens', 'output_tokens')]:
        if usage[subset] is not None and usage[total] is not None and usage[subset] > usage[total]:
            raise ContractError(subset+' must be a subset of '+total+' in this normalized contract')
    if event['cost'] is not None:
        cost = object_fields(event['cost'], {'amount', 'currency'}, set(), 'observed charge')
        if not isinstance(cost['currency'], str) or not re.fullmatch('[A-Z]{3}', cost['currency']):
            raise ContractError('currency: explicit three-letter code; no conversion')
        if not isinstance(cost['amount'], str) or not re.fullmatch(r'\d{1,12}(?:\.\d{1,12})?', cost['amount']):
            raise ContractError('amount: nonnegative observed decimal string, not an estimated price')
        try:
            if not Decimal(cost['amount']).is_finite():
                raise InvalidOperation
        except InvalidOperation as error:
            raise ContractError('Invalid observed amount') from error
    source = object_fields(event['source'], {'kind', 'path', 'sha256'}, set(), 'observation source')
    choice(source['kind'], {'host_export', 'provider_response', 'local_timer', 'manual_observation'}, 'source.kind')
    if not isinstance(source['path'], str) or not isinstance(source['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
        raise ContractError('Source requires an explicit private path and SHA256')
    proof = work.inside(source['path'])
    if not proof.is_file() or not 0 < proof.stat().st_size <= 1_000_000:
        raise WorkflowError('needs_input', 'Select a nonempty source artifact of at most 1 MB inside this workspace')
    with proof.open('rb') as stream:
        content = stream.read(1_000_001)
    if not 0 < len(content) <= 1_000_000 or hashlib.sha256(content).hexdigest() != source['sha256']:
        raise WorkflowError('blocked', 'Observation source changed; no measurement imported')
    return event


def _workspace(work):
    if not work.db_path.is_file():
        raise WorkflowError('needs_input', 'Initialize the selected private workspace first')


def _feature(db, create=False):
    if not 1 <= db.execute('pragma user_version').fetchone()[0] <= 6:
        raise WorkflowError('blocked', 'Unsupported application schema; performance import does not migrate it')
    tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    present = {'performance_meta', 'performance_observations'} & tables
    if present and len(present) != 2:
        raise WorkflowError('needs_input', 'Incomplete performance feature; inspect private state without resetting it')
    if not present:
        if not create:
            return False
        db.execute('CREATE TABLE performance_meta(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)')
        db.execute('INSERT INTO performance_meta VALUES(1,1)')
        db.execute('CREATE TABLE performance_observations(event_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, '
                   'model_id TEXT, phase TEXT NOT NULL, workload_id TEXT NOT NULL, payload TEXT NOT NULL, recorded_utc TEXT NOT NULL)')
        db.execute('CREATE INDEX performance_group_lookup ON performance_observations(model_id,phase,workload_id)')
        for operation in ('UPDATE', 'DELETE'):
            db.execute('CREATE TRIGGER performance_no_'+operation.lower()+' BEFORE '+operation+
                       " ON performance_observations BEGIN SELECT RAISE(ABORT,'performance observations are append-only'); END")
    row = db.execute('SELECT version FROM performance_meta WHERE id=1').fetchone()
    if row is None or row[0] != 1:
        raise WorkflowError('blocked', 'Unsupported performance feature version; preserve existing observations')
    return True


def record(work, event) -> Outcome:
    _workspace(work)
    event = deepcopy(event)
    validate(work, event)
    fingerprint = canonical_hash(event)
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE')
        _feature(db, create=True)
        old = db.execute('SELECT fingerprint FROM performance_observations WHERE event_id=?', (event['event_id'],)).fetchone()
        if old:
            if old[0] != fingerprint:
                raise WorkflowError('blocked', 'Observation ID already names different bytes; never overwrite historical usage')
            reused = True
        else:
            db.execute('INSERT INTO performance_observations VALUES(?,?,?,?,?,?,?)',
                (event['event_id'], fingerprint, event['model_id'], event['phase'], event['workload_id'],
                 json.dumps(event, ensure_ascii=False, sort_keys=True), utc_now()))
            reused = False
        db.commit()
    return Outcome('ok', {'event_id': event['event_id'], 'fingerprint': fingerprint,
        'reused': reused, 'provenance': 'caller-reported observation bound to source hash; provider identity not authenticated'}, [])


def report(work, *, model_id=None, phase=None, workload_id=None) -> Outcome:
    _workspace(work)
    filters = {k: v for k, v in [('model_id', model_id), ('phase', phase), ('workload_id', workload_id)] if v is not None}
    for key, value in filters.items():
        identifier(value, key)
    where = ' WHERE '+' AND '.join(key+'=?' for key in filters) if filters else ''
    with work._db() as db:
        db.execute('BEGIN')
        if _feature(db):
            rows = db.execute('SELECT payload,fingerprint FROM performance_observations'+where+
                ' ORDER BY event_id LIMIT ?', (*filters.values(), MAX_REPORT_RECORDS+1)).fetchall()
        else:
            rows = []
    if len(rows) > MAX_REPORT_RECORDS:
        raise WorkflowError('needs_input', 'Report exceeds 10000 observations; select model/phase/workload filters')
    grouped = defaultdict(list)
    for row in rows:
        event = json.loads(row['payload'])
        if canonical_hash(event) != row['fingerprint']:
            raise WorkflowError('blocked', 'Historical observation changed; inspect without overwriting it')
        grouped[(event['provider_id'], event['model_id'], event['effort'], event['phase'], event['workload_id'])].append(event)
    groups = []
    for key, events in sorted(grouped.items(), key=lambda item: tuple(v or '' for v in item[0])):
        durations = sorted(e['duration_ms'] for e in events if e['duration_ms'] is not None)
        known, coverage, charges = {}, {}, defaultdict(Decimal)
        for token in TOKENS:
            values = [e['usage'][token] for e in events if e['usage'][token] is not None]
            known[token] = sum(values) if values else None
            coverage[token] = {'known': len(values), 'missing': len(events)-len(values)}
        for event in events:
            if event['cost'] is not None:
                charges[event['cost']['currency']] += Decimal(event['cost']['amount'])
        groups.append({**dict(zip(('provider_id', 'model_id', 'effort', 'phase', 'workload_id'), key)),
            'observations': len(events), 'accepted_observations': sum(e['accepted'] for e in events),
            'statuses': {status: sum(e['status'] == status for e in events) for status in sorted(STATUSES)},
            'duration_ms': {'known': len(durations), 'missing': len(events)-len(durations),
                'p50': median(durations) if durations else None,
                'p95': durations[math.ceil(len(durations)*.95)-1] if durations else None,
                'sum_observed': sum(durations) if durations else None},
            'known_tokens': known, 'token_coverage': coverage,
            'known_charges': {currency: format(amount, 'f') for currency, amount in sorted(charges.items())},
            'missing_charge_observations': sum(e['cost'] is None for e in events)})
    return Outcome('ok', {'schema_version': '1.0', 'record_count': len(rows), 'groups': groups,
        'filters': filters, 'source_revalidated_at_import': True, 'source_revalidated_at_report': False,
        'scope': 'Caller-reported, source-hash-bound observations only. Null is unavailable, not zero. '
                 'Cache/reasoning are subsets. Parallel durations are not campaign wall time. '
                 'Acceptance is reported, not an independent quality audit. Compare equivalent workloads; '
                 'no inferred provider usage, token prices, subscription quota or savings.'}, [])


def render(data, format='md') -> str:
    choice(format, {'json', 'md', 'csv'}, 'performance report format')
    if format == 'json':
        return json.dumps(data, ensure_ascii=False, indent=2)+'\n'
    columns = ['provider', 'model', 'effort', 'phase', 'workload', 'observations', 'accepted',
               'input_tokens_known', 'input_missing', 'output_tokens_known', 'output_missing',
               'cached_input_known', 'reasoning_known', 'duration_p50_ms', 'duration_p95_ms',
               'duration_missing', 'observed_charges', 'charge_missing']
    rows = []
    for group in data['groups']:
        rows.append([group['provider_id'], group['model_id'], group['effort'], group['phase'],
            group['workload_id'], group['observations'], group['accepted_observations'],
            group['known_tokens']['input_tokens'], group['token_coverage']['input_tokens']['missing'],
            group['known_tokens']['output_tokens'], group['token_coverage']['output_tokens']['missing'],
            group['known_tokens']['cached_input_tokens'], group['known_tokens']['reasoning_tokens'],
            group['duration_ms']['p50'], group['duration_ms']['p95'], group['duration_ms']['missing'],
            json.dumps(group['known_charges'], sort_keys=True), group['missing_charge_observations']])
    rows = [['unavailable' if value is None else str(value) for value in row] for row in rows]
    if format == 'csv':
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(columns); writer.writerows(rows)
        return stream.getvalue()
    columns = ['provider / model / effort', 'phase / workload', 'calls / accepted',
               'input / output tokens (missing calls)', 'p50 / p95 ms (missing calls)',
               'observed charges (missing calls)']
    rows = []
    for g in data['groups']:
        value = lambda v: 'unavailable' if v is None else str(v)
        rows.append([' / '.join(value(g[k]) for k in ('provider_id', 'model_id', 'effort')),
            g['phase']+' / '+g['workload_id'], str(g['observations'])+' / '+str(g['accepted_observations']),
            ' / '.join(value(g['known_tokens'][k])+' ('+str(g['token_coverage'][k]['missing'])+')'
                       for k in ('input_tokens', 'output_tokens')),
            value(g['duration_ms']['p50'])+' / '+value(g['duration_ms']['p95'])+' ('+str(g['duration_ms']['missing'])+')',
            json.dumps(g['known_charges'], sort_keys=True)+' ('+str(g['missing_charge_observations'])+')'])
    return ('# Model performance observations\n\n'+data['scope']+'\n\n'+
        'Observations: '+str(data['record_count'])+'\n\n| '+' | '.join(columns)+' |\n| '+
        ' | '.join('---' for _ in columns)+' |\n'+
        '\n'.join('| '+' | '.join(row)+' |' for row in rows)+'\n')


def export(work, output: str, format='json', **filters) -> Outcome:
    choice(format, {'json', 'md', 'csv'}, 'performance report format')
    target = work.inside(output)
    if not target.is_relative_to(work.inside('reports/performance')) or target.suffix != '.'+format:
        raise WorkflowError('blocked', 'Use a matching file suffix inside reports/performance/; never overwrite application data')
    result = report(work, **filters)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Reports are dated snapshots. Refuse an existing path, including source artifacts.
    with target.open('x', encoding='utf8', newline='') as stream:
        stream.write(render(result.data, format))
    return Outcome('ok', {'report': work.file_record(target), 'format': format,
                         'record_count': result.data['record_count']}, [])
