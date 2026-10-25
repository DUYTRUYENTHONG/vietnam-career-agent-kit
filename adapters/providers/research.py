"""Opt-in Firecrawl research coordinator over the existing private workspace.

Workers never write SQLite. All network operations occur outside transactions.
Application execution and authority are deliberately not dependencies.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import socket
import sqlite3
import time
from urllib.parse import urlsplit
import uuid

from core.contracts import ContractError, Outcome, normalize_city, validate_job
from core.ledger import canonical_hash, utc_now
from core.workflow import WorkflowError
from .contracts import (DiscoveryHit, PageEvidence, PARSER_VERSION, ProviderError,
                        ResearchPlan, canonical_url, timestamp)
from .firecrawl import Firecrawl

STAGES = ('discovery', 'provider_queueing', 'retrieval', 'extraction', 'normalization',
          'deduplication', 'fit_assessment', 'host_reasoning', 'document_preparation',
          'conversion', 'browser_startup', 'inspection', 'filling', 'upload', 'review',
          'submission', 'verification', 'human_wait', 'local_queue', 'retry_backoff', 'cache')


class Research:
    def __init__(self, work, provider=None, *, resolver=socket.getaddrinfo):
        self.work = work
        self._provider = provider
        self.resolver = resolver

    @property
    def provider(self):
        if self._provider is None:
            self._provider = Firecrawl()
        return self._provider

    def _metric(self, trace, stage, started, **detail):
        # Only opaque IDs, numeric counters and fixed labels enter diagnostics.
        with self.work._db() as db:
            db.execute('INSERT INTO research_metrics(trace_id,stage,seconds,occurred_utc,detail) VALUES(?,?,?,?,?)',
                       (trace, stage, time.perf_counter()-started, utc_now(), json.dumps(detail)))

    def _check(self, plan, *, resolve=False):
        if timestamp(plan.payload['expires_utc']) <= datetime.now(timezone.utc):
            raise WorkflowError('blocked', 'Research scope expired; no provider call made')
        registry = json.loads((self.work.repo_root/'connectors/registry.json').read_text(encoding='utf8'))
        sources = {s['id']: s for s in registry['sources']}
        for item in plan.payload['sources']:
            source = sources.get(item['source_id'])
            if not source or source['implementation_status'] == 'Manual-only':
                raise WorkflowError('blocked', 'Source registry prohibits this provider route')
            plan.source('https://'+item['host'], resolve=resolve, resolver=self.resolver)

    @staticmethod
    def key(plan, operation, value):
        return canonical_hash({'provider': 'firecrawl-v2', 'account': plan.payload['provider_account'],
            'operation': operation, 'value': value, 'locale': ['en', 'vi'], 'scope': 'public-unauthenticated',
            'sources':sorted((s['source_id'],s['host']) for s in plan.payload['sources']), 'schema_version':'1.0',
            'parser': PARSER_VERSION, 'max_age_ms': plan.payload['freshness']['provider_max_age_ms']})

    def preview(self, raw):
        plan = ResearchPlan.parse(raw)
        # No DNS, credentials or database reads in dry-run.
        for url in plan.payload['urls']:
            plan.source(url, resolve=False)
        return Outcome('ok', {'fingerprint': canonical_hash(plan.payload), 'network_calls': 0,
            'provider': 'firecrawl-v2', 'account': plan.payload['provider_account'],
            'queries': plan.queries() if not plan.payload['urls'] else [],
            'selected_urls': list(dict.fromkeys(map(canonical_url, plan.payload['urls']))),
            'limits': plan.payload['limits'], 'freshness': plan.payload['freshness'],
            'disclosure': 'Public URLs and non-identifying role/location terms only; provider account is billed separately.',
            'routing': ['fresh eligible local evidence', 'documented feed/manual import if available',
                        'Firecrawl public retrieval', 'interactive research unsupported in this slice', 'host/manual'],
            'application_authority': False}, [])

    def _register(self, plan, approved):
        fingerprint = canonical_hash(plan.payload)
        if approved != fingerprint:
            raise WorkflowError('needs_input', 'Review dry-run and supply its exact --approve-plan fingerprint')
        self._check(plan)
        with self.work._db() as db:
            db.execute('INSERT OR IGNORE INTO research_plans(fingerprint,payload,created_utc,started_utc) VALUES(?,?,?,?)',
                       (fingerprint, json.dumps(plan.payload, ensure_ascii=False), utc_now(), utc_now()))
        return fingerprint

    def _reserve(self, db, fingerprint, plan, credits=0, *, recovery=False):
        row = db.execute('SELECT * FROM research_plans WHERE fingerprint=?', (fingerprint,)).fetchone()
        if not recovery and (datetime.now(timezone.utc)-timestamp(row['started_utc'])).total_seconds() >= plan.payload['limits']['runtime_seconds']:
            raise WorkflowError('blocked', 'Finite research runtime ended; use read-only saved results')
        if row['requests'] >= plan.payload['limits']['requests'] or row['reserved_credits']+credits > plan.payload['limits']['credit_reservation']:
            raise WorkflowError('blocked', 'Research request/credit reservation exhausted')
        db.execute('UPDATE research_plans SET requests=requests+1,reserved_credits=reserved_credits+? WHERE fingerprint=?',
                   (credits, fingerprint))

    def _load_cache(self, key, max_age):
        with self.work._db() as db:
            row = db.execute('SELECT * FROM research_cache WHERE cache_key=?', (key,)).fetchone()
        now = datetime.now(timezone.utc)
        if row and timestamp(row['expires_utc']) > now and (now-timestamp(row['stored_utc'])).total_seconds() < max_age:
            value = json.loads(row['payload'])
            if 'evidence_id' in value:
                with self.work._db() as db:
                    evidence = db.execute('SELECT payload,artifact_path FROM research_evidence WHERE id=?', (value['evidence_id'],)).fetchone()
                if not evidence or self.work.inside(evidence['artifact_path']).read_text(encoding='utf8') != evidence['payload']:
                    raise WorkflowError('blocked', 'Cached evidence bytes changed; do not reuse')
            return value
        return None

    def _cache(self, key, value, ttl):
        with self.work._db() as db:
            db.execute('INSERT OR REPLACE INTO research_cache VALUES(?,?,?,?)', (key,
                json.dumps(value, ensure_ascii=False), utc_now(),
                (datetime.now(timezone.utc)+timedelta(seconds=ttl)).isoformat()))

    def _task(self, plan, fingerprint, operation, values, credits, call):
        """Durable intent before dispatch, immediately persist remote ID. Never relaunch."""
        self._check(plan, resolve=True)
        key = self.key(plan, operation, values)
        trace = uuid.uuid4().hex
        try:
            with self.work._db() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT * FROM provider_tasks WHERE plan_fingerprint=? AND operation=? AND cache_key=?',
                                 (fingerprint, operation, key)).fetchone()
                if row:
                    return dict(row)
                if operation in {'batch','scrape'}:
                    active = db.execute("SELECT t.payload,p.payload AS plan_payload FROM provider_tasks t JOIN research_plans p ON p.fingerprint=t.plan_fingerprint WHERE t.operation IN ('batch','scrape') AND t.state IN ('intent','running','uncertain','cancel_requested')").fetchall()
                    domains = {urlsplit(u).hostname for u in values}
                    account_active = 0
                    for running in active:
                        if domains & {urlsplit(u).hostname for u in json.loads(running['payload'])}:
                            raise WorkflowError('manual_required', 'Destination domain already has unresolved extraction; reconcile it first')
                        if json.loads(running['plan_payload'])['provider_account'] == plan.payload['provider_account']:
                            account_active += 1
                    if account_active >= min(plan.payload['limits']['workers'], self.provider.account_concurrency):
                        raise WorkflowError('manual_required', 'Provider account already has its bounded active extraction capacity')
                self._reserve(db, fingerprint, plan, credits)
                db.execute('INSERT INTO provider_tasks(id,plan_fingerprint,operation,cache_key,state,payload,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?)',
                    (trace, fingerprint, operation, key, 'intent', json.dumps(values, ensure_ascii=False), utc_now(), utc_now()))
                db.commit()
        except sqlite3.IntegrityError as error:
            raise WorkflowError('manual_required', 'An identical public request is already in flight; reconcile it instead') from error
        started = time.perf_counter()
        try:
            result = call()
            remote_id = result.get('id') if operation == 'batch' else None
            if operation == 'batch':
                try:
                    self.provider.batch_path(remote_id)
                except ProviderError:
                    raise ProviderError('start_response_missing_id', possibly_accepted=True) from None
            with self.work._db() as db:
                db.execute('UPDATE provider_tasks SET state=?,remote_id=?,result=?,updated_utc=? WHERE id=?',
                    ('running' if remote_id else 'completed', remote_id, json.dumps(result, ensure_ascii=False), utc_now(), trace))
        except ProviderError as error:
            with self.work._db() as db:
                db.execute('UPDATE provider_tasks SET state=?,error_code=?,updated_utc=? WHERE id=?',
                    ('uncertain' if error.possibly_accepted else 'failed', error.code, utc_now(), trace))
            # No automatic POST/DELETE retry, including paid search/scrape calls.
        finally:
            self._metric(trace, 'discovery' if operation == 'search' else 'retrieval', started)
        with self.work._db() as db:
            return dict(db.execute('SELECT * FROM provider_tasks WHERE id=?', (trace,)).fetchone())

    def discover(self, raw, approved, *, individual=False):
        plan = ResearchPlan.parse(raw)
        fingerprint = self._register(plan, approved)
        cache_hits = 0
        if not plan.payload['urls']:
            for query in plan.queries():
                key = self.key(plan, 'search', query)
                cached = self._load_cache(key, plan.payload['freshness']['search_seconds'])
                if cached is not None:
                    cache_hits += 1
                    continue
                task = self._task(plan, fingerprint, 'search', query, 2,
                    lambda: self.provider.search(query, [s['host'] for s in plan.payload['sources']],
                                                 min(10, plan.payload['limits']['pages'])))
                if task['state'] == 'completed':
                    result = json.loads(task['result'])
                    data = result.get('data', {}).get('web', [])
                    hits = []
                    if not isinstance(data, list):
                        raise ProviderError('invalid_search_output')
                    for item in data[:plan.payload['limits']['pages']]:
                        try:
                            url = canonical_url(item['url']); source = plan.source(url, resolver=self.resolver)
                            hits.append(asdict(DiscoveryHit(url, str(item.get('title', ''))[:500],
                                str(item.get('description', ''))[:1000], source['source_id'])))
                        except (ContractError, KeyError, TypeError):
                            continue
                    self._cache(key, {'hits': hits}, plan.payload['freshness']['search_seconds'])
        else:
            started = time.perf_counter()
            urls = list(dict.fromkeys(map(canonical_url, plan.payload['urls'])))
            self._metric(fingerprint, 'deduplication', started, input_count=len(plan.payload['urls']), unique_count=len(urls))
            groups = {}
            for url in urls:
                plan.source(url, resolve=False)
                cached = self._load_cache(self.key(plan, 'page', url), plan.payload['freshness']['page_seconds'])
                if cached:
                    cache_hits += 1
                else:
                    groups.setdefault(urlsplit(url).hostname, []).append(url)
            # At most workers jobs, each with server-side concurrency 1. Thus a
            # batch cannot defeat the reviewed one-request-per-domain bound.
            if groups and len(groups) > min(plan.payload['limits']['workers'], self.provider.account_concurrency):
                raise WorkflowError('needs_input', 'Split domains to the configured reviewed account concurrency (default one)')
            for group in groups.values():
                if individual:
                    for url in group:
                        task = self._task(plan, fingerprint, 'scrape', [url], 1,
                            lambda url=url: self.provider.scrape(url, plan.payload['freshness']['provider_max_age_ms']))
                        if task['state'] == 'completed':
                            self._save_page(plan, task, json.loads(task['result']).get('data', {}))
                else:
                    self._task(plan, fingerprint, 'batch', group, len(group),
                        lambda group=group: self.provider.start_batch(group, 1, plan.payload['freshness']['provider_max_age_ms']))
        result = self.summary(fingerprint)
        result.data['cache_hits'] = cache_hits
        self._metric(fingerprint, 'cache', time.perf_counter(), hits=cache_hits)
        return result

    def _save_page(self, plan, task, document):
        started = time.perf_counter()
        if not isinstance(document, dict):
            raise ProviderError('invalid_page_output')
        meta, markdown = document.get('metadata', {}), document.get('markdown')
        if not isinstance(meta, dict) or not isinstance(markdown, str) or not markdown.strip() or len(markdown.encode()) > 2_000_000:
            raise ProviderError('empty_or_oversized_page')
        final = canonical_url(meta.get('url') or meta.get('sourceURL') or '')
        source = plan.source(final, resolver=self.resolver)
        requested = json.loads(task['payload'])
        # Cross-destination redirects are quarantined, never silently rebound.
        if final not in requested:
            raise ProviderError('unbound_page_destination')
        if type(meta.get('statusCode', 200)) is not int or meta.get('statusCode', 200) >= 400:
            raise ProviderError('page_http_failure')
        digest = hashlib.sha256(markdown.encode('utf8')).hexdigest()
        evidence = asdict(PageEvidence(final, final if meta.get('url') else None, source['source_id'],
            'firecrawl-v2', utc_now(), digest, markdown, {},
            ['employer', 'requisition', 'title', 'location', 'salary', 'experience', 'deadline', 'liveness'],
            'captured_requires_normalization', provider_cache_timestamp=meta.get('cachedAt'),
            source_timestamp=meta.get('publishedTime')))
        # Preserve provider timestamps as observations only, never receipt time.
        ident = canonical_hash({'task': task['id'], 'url': final, 'digest': digest})
        relative = 'research/evidence/'+ident+'.json'
        content = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
        # SQLite chooses the immutable winning record before export. Concurrent
        # status readers cannot replace it with different retrieval timestamps.
        # A crash between commit and file export can repair the derived file.
        with self.work._db() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT id,payload,artifact_path FROM research_evidence WHERE task_id=? AND url_key=?',
                               (task['id'], canonical_hash(final))).fetchone()
            if prior:
                if json.loads(prior['payload'])['content_sha256'] != digest:
                    raise ProviderError('changed_remote_evidence')
                ident, content, relative = prior['id'], prior['payload'], prior['artifact_path']
            else:
                db.execute('INSERT INTO research_evidence VALUES(?,?,?,?,?)',
                           (ident, task['id'], canonical_hash(final), content, relative))
            db.commit()
        target = self.work.inside(relative)
        if target.exists():
            if target.read_text(encoding='utf8') != content:
                raise ProviderError('changed_local_evidence')
        else:
            self.work.atomic_text(relative, content)
        self._cache(self.key(plan, 'page', final), {'evidence_id': ident}, plan.payload['freshness']['page_seconds'])
        self._metric(task['id'], 'extraction', started, validated_pages=1)

    def _plan(self, fingerprint):
        with self.work._db() as db:
            row = db.execute('SELECT * FROM research_plans WHERE fingerprint=?', (fingerprint,)).fetchone()
        if not row:
            raise WorkflowError('needs_input', 'Unknown research plan fingerprint')
        return ResearchPlan.parse(json.loads(row['payload']))

    def status(self, fingerprint, *, cancel=False):
        plan = self._plan(fingerprint)
        # Recovery can inspect/cancel already-created IDs after scope/runtime
        # expiry. It never starts a new task or grants current source permission.
        # Only Firecrawl batch tasks implement this polling/cancellation API.
        # Other providers share the ledger, never this remote-ID namespace.
        with self.work._db() as db:
            tasks = [dict(r) for r in db.execute("SELECT * FROM provider_tasks WHERE plan_fingerprint=? AND operation='batch' AND remote_id IS NOT NULL AND state IN ('running','cancel_requested')", (fingerprint,))]
        for task in tasks:
            # Unknown accepted starts have no ID; do not create replacements.
            if cancel and task['state'] != 'cancel_requested':
                with self.work._db() as db:
                    db.execute('UPDATE provider_tasks SET state=? WHERE id=?', ('cancel_requested', task['id']))
                try:
                    self._read(plan, fingerprint, task, lambda: self.provider.cancel(task['remote_id']), mutation=True)
                except ProviderError:
                    continue  # Request does not prove termination; GET reconciles.
            saved = json.loads(task['result']) if task['result'] else {}
            continuation = saved.get('next') if saved.get('status') == 'completed' else None
            seen = set()
            try:
                for _ in range(8):
                    result = self._read(plan, fingerprint, task,
                        lambda: self.provider.status(task['remote_id'], continuation))
                    documents = result.get('data', [])
                    if not isinstance(documents, list) or len(documents) > plan.payload['limits']['pages']:
                        raise ProviderError('invalid_page_list')
                    page_errors = []
                    for document in documents:
                        try:
                            self._save_page(plan, task, document)
                        except (ProviderError, ContractError):
                            page_errors.append({'code':'invalid_page_evidence'})
                    next_url = result.get('next')
                    state = result.get('status')
                    if state not in {'scraping', 'completed', 'failed', 'cancelled'}:
                        raise ProviderError('unknown_remote_state')
                    if next_url:
                        self.provider.continuation_path(task['remote_id'], next_url)
                    # Persist results and cursor before next read. No automatic
                    # polling loop when next denotes progress rather than a page.
                    with self.work._db() as db:
                        db.execute('UPDATE provider_tasks SET result=?,updated_utc=?,error_code=COALESCE(?,error_code) WHERE id=?',
                                   (json.dumps(result, ensure_ascii=False), utc_now(), json.dumps(page_errors) if page_errors else None, task['id']))
                    if state in {'failed', 'cancelled'} or not next_url:
                        if state in {'completed', 'failed', 'cancelled'}:
                            with self.work._db() as db:
                                db.execute('UPDATE provider_tasks SET state=? WHERE id=?', (state, task['id']))
                        break
                    if next_url in seen or state == 'scraping':
                        break
                    seen.add(next_url); continuation = next_url
                if state in {'completed', 'failed'}:
                    errors = self._read(plan, fingerprint, task, lambda: self.provider.errors(task['remote_id']))
                    # Remote error messages may contain private content. Store
                    # per-URL opaque keys and fixed codes, never raw strings.
                    with self.work._db() as db:
                        prior = db.execute('SELECT error_code FROM provider_tasks WHERE id=?', (task['id'],)).fetchone()[0]
                    clean_errors = json.loads(prior) if prior and prior.startswith('[') else []
                    for item in errors.get('errors', []):
                        clean_errors.append({'url_key': canonical_hash(item.get('url', '')), 'code': 'provider_url_error'})
                    for url in errors.get('robotsBlocked', []):
                        clean_errors.append({'url_key': canonical_hash(url), 'code': 'robots_blocked_no_fallback'})
                    with self.work._db() as db:
                        db.execute('UPDATE provider_tasks SET error_code=? WHERE id=?',
                                   (json.dumps(clean_errors) if clean_errors else None, task['id']))
            except ProviderError as error:
                with self.work._db() as db:
                    db.execute('UPDATE provider_tasks SET error_code=? WHERE id=?', (error.code, task['id']))
                    if error.code == 'http_404':
                        db.execute("UPDATE provider_tasks SET state='uncertain',error_code='remote_expired_or_missing' WHERE id=?", (task['id'],))
        return self.summary(fingerprint)

    def _read(self, plan, fingerprint, task, call, *, mutation=False):
        with self.work._db() as db:
            row = db.execute('SELECT failures,not_before_utc FROM provider_tasks WHERE id=?', (task['id'],)).fetchone()
            if row['not_before_utc'] and timestamp(row['not_before_utc']) > datetime.now(timezone.utc):
                raise ProviderError('retry_after_pending')
            if row['failures'] >= 3:
                raise ProviderError('circuit_open_manual_reconciliation')
            db.execute('BEGIN IMMEDIATE'); self._reserve(db, fingerprint, plan, recovery=True); db.commit()
        started = time.perf_counter()
        try:
            result = call()
            with self.work._db() as db:
                db.execute('UPDATE provider_tasks SET failures=0,not_before_utc=NULL WHERE id=?', (task['id'],))
            return result
        except ProviderError as error:
            # No blocking sleep or blind retry. Persist Retry-After for subsequent
            # CLI calls; bound status failures with a circuit breaker.
            delay = error.retry_after if error.retry_after is not None else 2**min(row['failures'], 5)
            after = (datetime.now(timezone.utc)+timedelta(seconds=min(delay, 86400))).isoformat()
            with self.work._db() as db:
                db.execute('UPDATE provider_tasks SET failures=failures+1,not_before_utc=? WHERE id=?', (after, task['id']))
                if delay > 86400:
                    db.execute('UPDATE provider_tasks SET failures=3 WHERE id=?', (task['id'],))
            self._metric(task['id'], 'retry_backoff', time.perf_counter(), deferred_seconds=delay)
            raise
        finally:
            self._metric(task['id'], 'verification', started)

    def summary(self, fingerprint):
        with self.work._db() as db:
            run = db.execute('SELECT * FROM research_plans WHERE fingerprint=?', (fingerprint,)).fetchone()
            tasks = [dict(r) for r in db.execute('SELECT id,operation,state,remote_id,error_code,result,payload FROM provider_tasks WHERE plan_fingerprint=?', (fingerprint,))]
            pages = [dict(r) for r in db.execute('SELECT e.id,e.artifact_path FROM research_evidence e JOIN provider_tasks t ON t.id=e.task_id WHERE t.plan_fingerprint=?', (fingerprint,))]
            metrics = [dict(r) for r in db.execute('SELECT stage,SUM(seconds) seconds,COUNT(*) samples FROM research_metrics WHERE trace_id=? OR trace_id IN (SELECT id FROM provider_tasks WHERE plan_fingerprint=?) OR trace_id IN (SELECT e.id FROM research_evidence e JOIN provider_tasks t ON t.id=e.task_id WHERE t.plan_fingerprint=?) GROUP BY stage', (fingerprint,fingerprint,fingerprint))]
        if run is None:
            raise WorkflowError('needs_input', 'Unknown research fingerprint')
        observed_credits = []
        for task in tasks:
            response = json.loads(task.pop('result') or '{}')
            requested = json.loads(task.pop('payload'))
            if task['operation'] in {'batch','scrape'}:
                with self.work._db() as db:
                    present = {r[0] for r in db.execute('SELECT url_key FROM research_evidence WHERE task_id=?', (task['id'],))}
                task['missing_url_keys'] = [canonical_hash(u) for u in requested if canonical_hash(u) not in present]
            # TinyFish stores per-URL results, not a Firecrawl response object;
            # its observed billing is unavailable rather than estimated here.
            credit = response.get('creditsUsed') if isinstance(response,dict) else None
            task['observed_credits'] = credit if type(credit) in (int, float) and math.isfinite(credit) and credit >= 0 else None
            observed_credits.append(task['observed_credits'])
        plan = ResearchPlan.parse(json.loads(run['payload']))
        hits = {}
        for query in plan.queries() if not plan.payload['urls'] else []:
            cached = self._load_cache(self.key(plan, 'search', query), plan.payload['freshness']['search_seconds'])
            for hit in (cached or {}).get('hits', []): hits[hit['url']] = hit
        for url in plan.payload['urls']:
            cached = self._load_cache(self.key(plan, 'page', canonical_url(url)), plan.payload['freshness']['page_seconds'])
            if cached and not any(p['id'] == cached['evidence_id'] for p in pages):
                pages.append({'id': cached['evidence_id'], 'artifact_path': 'research/evidence/'+cached['evidence_id']+'.json'})
        uncertain = any(t['state'] in {'intent', 'uncertain', 'cancel_requested'} for t in tasks)
        failures = any(t['state'] == 'failed' or t['error_code'] or
                       t['state'] == 'completed' and t.get('missing_url_keys') for t in tasks)
        # A terminal provider success with no useful output is not a good result.
        empty = bool(tasks) and all(t['state'] == 'completed' for t in tasks) and not pages and not hits
        return Outcome('manual_required' if uncertain or failures or empty else 'ok',
            {'fingerprint': fingerprint, 'tasks': tasks, 'evidence': pages, 'leads': list(hits.values()),
             'requests_reserved': run['requests'], 'credit_reservation_estimate': run['reserved_credits'],
             'observed_credits': sum(observed_credits) if observed_credits and all(v is not None for v in observed_credits) else None,
            'observed_cost': None, 'tokens': None, 'browser_starts': 0,
             'metrics': {stage: next((m for m in metrics if m['stage'] == stage), None) for stage in STAGES},
             'applications': 0, 'notice': 'Captured evidence is untrusted. Normalize with source references, assess, then prepare selected jobs. No application authority.'},
            ['Reconcile pending/uncertain tasks; never relaunch a possibly accepted start.'] if uncertain else
            ['Partial, invalid or empty output requires review.'] if failures or empty else [])

    def import_jd(self, evidence_id, raw):
        """Explicit host-normalized JD through the existing import/fingerprint flow."""
        with self.work._db() as db:
            row = db.execute('SELECT * FROM research_evidence WHERE id=?', (evidence_id,)).fetchone()
        if not row:
            raise WorkflowError('needs_input', 'Unknown captured evidence')
        captured = self.work.inside(row['artifact_path']).read_text(encoding='utf8')
        if captured != row['payload']:
            raise WorkflowError('blocked', 'Captured evidence bytes changed')
        evidence = json.loads(captured)
        if set(raw) != {'job', 'references'}:
            raise ContractError('Supply normalized job and exact source quote references')
        job = validate_job(raw['job']); refs = raw['references']
        if job['platform'] != evidence['source_id']:
            raise ContractError('Retain the job source as platform; a retrieval provider is not a job source')
        if job['raw_jd'] != evidence['markdown'] or canonical_url(job['url']) != evidence['original_url']:
            raise ContractError('Normalized JD must bind the full captured evidence and destination')
        claims = {name: job[name] for name in ('employer', 'title', 'city', 'country', 'req_id', 'work_model', 'employment_type', 'liveness', 'posted', 'deadline') if job.get(name) and job[name] != 'unverified'}
        claims.update({'requirement:'+r['id']: r['text'] for r in job['requirements']})
        claims.update({'salary:'+k: str(v) for k, v in job['salary'].items() if v is not None})
        if not isinstance(refs, dict) or set(refs) != set(claims):
            raise ContractError('Every normalized claim requires a source reference; keep unknown fields unknown')
        for field, quote in refs.items():
            if not isinstance(quote, str) or not quote.strip() or quote not in evidence['markdown']:
                raise ContractError('Reference absent from captured evidence: '+field)
            if field in {'employer','title','req_id'} and claims[field].casefold() not in quote.casefold():
                raise ContractError('Identity claim absent from its source quote: '+field)
            if field == 'city' and normalize_city(claims[field]) != normalize_city(quote):
                raise ContractError('City claim differs from its source quote')
            if field.startswith('requirement:') and claims[field].casefold() not in quote.casefold():
                raise ContractError('Requirement claim absent from its source quote')
        # Exact quote presence is a consistency check, not semantic entailment.
        started = time.perf_counter()
        result = self.work.import_job(job)
        with self.work._db() as db:
            db.execute('INSERT INTO research_imports(job_id,evidence_id,job_fingerprint,reference_json,created_utc) VALUES(?,?,?,?,?)',
                (result.data['job']['id'], evidence_id, canonical_hash(job), json.dumps(refs, ensure_ascii=False), utc_now()))
        self._metric(evidence_id, 'normalization', started)
        result.data.update(evidence_id=evidence_id, source_mode='reviewed provider evidence import')
        result.issues.append('Quote presence does not prove semantic truth; review normalized requirements and liveness. Fresh destination inspection is still required before disclosure.')
        return result
