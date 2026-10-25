"""Durable, explicitly approved TinyFish public batches in schema-5 workspaces."""
from dataclasses import asdict
import hashlib
import json
import uuid

from core.contracts import ContractError, Outcome
from core.ledger import canonical_hash, utc_now
from core.workflow import WorkflowError
from .contracts import PageEvidence, ResearchPlan, canonical_url
from .research import Research
from .tinyfish import TinyFish, MAX_BYTES

PROVIDER = 'tinyfish-fetch'
OPERATION = 'tinyfish_fetch'


def _plan(raw):
    plan = ResearchPlan.parse(raw)
    urls = [canonical_url(u) for u in plan.payload['urls']]
    if not 1 <= len(urls) <= 10 or len(set(urls)) != len(urls):
        raise ContractError('TinyFish requires 1-10 distinct reviewed URLs')
    return plan, urls


def preview(raw):
    plan, urls = _plan(raw)
    for url in urls:
        plan.source(url, resolve=False)
    fingerprint = canonical_hash({'provider': PROVIDER, 'plan': plan.payload})
    return Outcome('ok', {'fingerprint': fingerprint, 'provider': PROVIDER,
        'selected_urls': urls, 'network_calls': 0, 'planned_requests': 1,
        'credit_reservation_estimate': len(urls), 'application_authority': False,
        'disclosure': 'Selected public URLs only; no candidate files or application authority.'}, [])


def _saved(work, fingerprint, task):
    with work._db() as db:
        evidence = [dict(r) for r in db.execute(
            'SELECT id,payload,artifact_path FROM research_evidence WHERE task_id=?', (task['id'],))]
    for item in evidence:
        target = work.inside(item['artifact_path'])
        if target.exists():
            if target.read_text(encoding='utf8') != item['payload']:
                raise WorkflowError('blocked', 'Captured TinyFish evidence bytes changed')
        else:
            work.atomic_text(item['artifact_path'], item['payload'])
        del item['payload']
    result = json.loads(task['result']) if task['result'] else []
    uncertain = task['state'] in ('intent', 'uncertain')
    return Outcome('ok' if task['state'] == 'completed' else 'manual_required',
        {'fingerprint': fingerprint, 'provider': PROVIDER, 'task_id': task['id'],
         'state': task['state'], 'items': result, 'evidence': evidence,
         'requests_reserved': 1, 'applications': 0, 'observed_cost': None,
         'notice': 'Untrusted public evidence; review before importing a job.'},
        ['Reconcile the prior request manually; no automatic replay.'] if uncertain else
        ['Partial or invalid evidence requires review.'] if task['state'] != 'completed' else [])


def fetch(work, raw, approved_fingerprint, provider=None):
    plan, urls = _plan(raw)
    fingerprint = canonical_hash({'provider': PROVIDER, 'plan': plan.payload})
    if approved_fingerprint != fingerprint:
        raise WorkflowError('needs_input', 'Review TinyFish dry-run and approve its exact fingerprint')
    # Read-only recovery needs neither credentials nor fresh provider access.
    with work._db() as db:
        prior = db.execute('SELECT * FROM provider_tasks WHERE plan_fingerprint=? AND operation=?',
                           (fingerprint, OPERATION)).fetchone()
    if prior:
        return _saved(work, fingerprint, dict(prior))
    provider = provider if provider is not None else TinyFish()
    coordinator = Research(work, resolver=provider.resolver)
    coordinator._check(plan, resolve=True)
    if len(urls) > plan.payload['limits']['credit_reservation']:
        raise WorkflowError('blocked', 'TinyFish batch exceeds credit reservation estimate')
    trace = uuid.uuid4().hex
    key = canonical_hash({'provider': PROVIDER, 'account': plan.payload['provider_account'], 'urls': sorted(urls)})
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE')
        prior = db.execute('SELECT * FROM provider_tasks WHERE plan_fingerprint=? AND operation=?',
                           (fingerprint, OPERATION)).fetchone()
        if prior:
            db.rollback()
        else:
            # Changed expiry/plan IDs cannot relaunch overlapping uncertain URLs.
            pending = db.execute("SELECT payload FROM provider_tasks WHERE operation=? AND state IN ('intent','uncertain','running')", (OPERATION,)).fetchall()
            if any(set(urls) & set(json.loads(r['payload'])) for r in pending):
                raise WorkflowError('manual_required', 'Overlapping TinyFish request needs reconciliation')
            db.execute('INSERT INTO research_plans(fingerprint,payload,created_utc,started_utc,requests,reserved_credits) VALUES(?,?,?,?,?,?)',
                (fingerprint, json.dumps(plan.payload, ensure_ascii=False), utc_now(), utc_now(), 1, len(urls)))
            db.execute('INSERT INTO provider_tasks(id,plan_fingerprint,operation,cache_key,state,payload,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?)',
                (trace, fingerprint, OPERATION, key, 'intent', json.dumps(urls), utc_now(), utc_now()))
            db.commit()
    if prior:
        return _saved(work, fingerprint, dict(prior))
    try:
        results = provider.fetch(plan)
    except Exception:
        results = []
    # Revalidate the adapter boundary, persist only bounded known fields.
    clean, evidence = [], []
    uncertain = not isinstance(results, list) or len(results) != len(urls)
    for index, url in enumerate(urls):
        item = results[index] if isinstance(results, list) and index < len(results) else None
        url_key = TinyFish.key(url)
        try:
            if not isinstance(item, dict) or item.get('url_key') != url_key or item.get('state') != 'completed':
                raise ValueError()
            data = item['data']; markdown = data['markdown']
            if canonical_url(data['final_url']) != url or not isinstance(markdown, str) or not markdown.strip() or len(markdown.encode('utf8')) > MAX_BYTES:
                raise ValueError()
            source = plan.source(url, resolve=False)
            document = PageEvidence(url, url, source['source_id'], PROVIDER, utc_now(),
                hashlib.sha256(markdown.encode('utf8')).hexdigest(), markdown, {}, [], 'captured_untrusted')
            ident = canonical_hash({'task': trace, 'url': url})
            evidence.append((ident, trace, canonical_hash(url), json.dumps(asdict(document), ensure_ascii=False), 'research/evidence/'+ident+'.json'))
            clean.append({'url_key': url_key, 'state': 'completed', 'evidence_id': ident})
        except (ValueError, TypeError, KeyError, ContractError):
            error = item.get('error') if isinstance(item, dict) else None
            accepted = not isinstance(error, dict) or error.get('possibly_accepted') is not False
            uncertain = uncertain or accepted
            clean.append({'url_key': url_key, 'state': 'manual_required', 'error': {'code': 'invalid_or_missing_evidence', 'possibly_accepted': accepted}})
    state = 'uncertain' if uncertain else 'completed' if len(evidence) == len(urls) else 'failed'
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE')
        for row in evidence:
            db.execute('INSERT INTO research_evidence VALUES(?,?,?,?,?)', row)
        db.execute('UPDATE provider_tasks SET state=?,result=?,updated_utc=? WHERE id=?',
                   (state, json.dumps(clean), utc_now(), trace))
        db.commit()
        task = dict(db.execute('SELECT * FROM provider_tasks WHERE id=?', (trace,)).fetchone())
    return _saved(work, fingerprint, task)
