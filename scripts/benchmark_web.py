#!/usr/bin/env python3
"""Equivalent fictional Firecrawl transport workload. No network, keys or browser."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.providers.firecrawl import BASE, Firecrawl
from adapters.providers.research import Research
from core.execution import Executor
from core.ledger import canonical_hash


def corpus():
    records = json.loads((ROOT/'examples/fictional/web-corpus.json').read_text(encoding='utf8'))['records']
    pages = {}
    for number in range(12):
        record = records[number % len(records)]
        req = 'FX-'+str(number)
        content = f"# {record['title']}\nExample Cooperative\n{record['city']}\nVN\n{req}\n{record['requirement']}\nStatus: {record['status']}\n"
        pages['https://jobs.example.test/'+req] = {**record, 'req_id':req, 'markdown':content}
    return pages


class FixtureTransport:
    """Fixed call overhead, identical per-page work and evidence on both paths."""
    def __init__(self, pages, latency):
        self.pages, self.latency, self.calls, self.batches = pages, latency, 0, {}

    def __call__(self, method, url, payload):
        self.calls += 1
        time.sleep(self.latency)
        def document(target):
            time.sleep(.001)  # Same per-page simulated extraction work.
            return {'markdown':self.pages[target]['markdown'], 'metadata':{'url':target, 'statusCode':200}}
        if url == BASE+'/scrape': return {'success':True, 'data':document(payload['url'])}
        if url == BASE+'/batch/scrape':
            self.batches['fixture'] = payload['urls']; return {'success':True, 'id':'fixture'}
        if url.endswith('/errors'): return {'errors':[], 'robotsBlocked':[]}
        return {'status':'completed', 'data':[document(u) for u in self.batches['fixture']]}


def run_sample(individual, latency):
    pages = corpus()
    now = datetime.now(timezone.utc)
    plan = {'schema_version':'1.0', 'plan_id':'fixture-cold', 'provider_account':'fixture',
        'expires_utc':(now+timedelta(hours=1)).isoformat(), 'roles':['Analyst'], 'locations':['Example City'],
        'sources':[{'source_id':'employer-careers','host':'jobs.example.test', 'permission_reference':'Controlled fictional transport',
            'expires_utc':(now+timedelta(hours=1)).isoformat(),'public_read_allowed':True}],
        'urls':[*pages, next(iter(pages)), next(iter(pages))],
        'limits':{'requests':40,'pages':24,'workers':1,'domain_workers':1,'runtime_seconds':120,'credit_reservation':40},
        'freshness':{'search_seconds':3600,'page_seconds':21600,'provider_max_age_ms':21600000}}
    with tempfile.TemporaryDirectory(prefix='career-web-bench-') as temp:
        work = Executor(Path(temp)/'private'); work.init()
        fake = FixtureTransport(pages, latency)
        research = Research(work, Firecrawl(fake), resolver=lambda *a,**k:[(None,None,None,None,('93.184.216.34',443))])
        started = time.perf_counter()
        result = research.discover(plan, canonical_hash(plan), individual=individual)
        if not individual: result = research.status(result.data['fingerprint'])
        captured_ms = (time.perf_counter()-started)*1000
        first_ms = None
        # Exact source-reference normalization/import has identical acceptance on both paths.
        for evidence in result.data['evidence']:
            captured = json.loads(work.inside(evidence['artifact_path']).read_text(encoding='utf8'))
            truth = pages[captured['original_url']]
            assert captured['content_sha256'] == hashlib.sha256(truth['markdown'].encode()).hexdigest()
            job = {'schema_version':'1.0','platform':'employer-careers','platform_job_id':truth['req_id'],
                'employer':'Example Cooperative','req_id':truth['req_id'],'title':truth['title'],
                'url':captured['original_url'],'city':truth['city'],'country':'VN','work_model':None,
                'employment_type':None,'document_language':truth['language'],'raw_jd':truth['markdown'],
                'liveness':truth['status'],'readable':True,
                'requirements':[{'id':'R1','text':truth['requirement'],'field':'capability','value':truth['requirement'],'mandatory':True,'hard':False}],
                'salary':{'amount':None,'currency':None,'period':None,'gross_net':None,'bonus':None}}
            refs = {name:job[name] for name in ('employer','req_id','title','city','country')}
            if job['liveness'] != 'unverified': refs['liveness'] = 'Status: '+truth['status']
            refs['requirement:R1'] = truth['requirement']
            imported = research.import_jd(evidence['id'], {'job':job,'references':refs})
            assert work.job_document(imported.data['job']['id'])[0] == job
            if first_ms is None: first_ms = (time.perf_counter()-started)*1000
        elapsed_ms = (time.perf_counter()-started)*1000
        assert len(result.data['evidence']) == len(pages) == work.status()['jobs']
        calls = fake.calls
        plan['plan_id'] = 'fixture-warm'
        warm_started = time.perf_counter()
        warm = research.discover(plan, canonical_hash(plan), individual=individual)
        warm_ms = (time.perf_counter()-warm_started)*1000
        assert warm.data['cache_hits'] == len(pages) and fake.calls == calls
        return {'capture_ms':round(captured_ms,3),'complete_ms':round(elapsed_ms,3),
            'first_imported_jd_ms':round(first_ms,3),'warm_ms':round(warm_ms,3),
            'provider_calls':calls,'warm_provider_calls':0,'cache_hits':12,'unique_evidence':12,
            'normalized_records':12,'active_jobs':6,'closed_jobs':3,'unverified_jobs':3,
            'content_digest_accuracy':1.0,'fixture_normalization_accuracy':1.0,
            'duplicate_fetches':0,'browser_starts':0,
            'active_jobs_per_minute':round(6*60000/elapsed_ms,3)}


def benchmark(samples=7, latency_ms=30):
    if type(samples) is not int or not 1 <= samples <= 20 or not 0 <= latency_ms <= 100:
        raise ValueError('Use 1-20 samples and 0-100 ms fixture overhead')
    results = {'individual':[], 'batch':[]}
    for index in range(samples):
        # Alternate ordering to avoid always favouring one path.
        for mode in (['individual','batch'] if index % 2 == 0 else ['batch','individual']):
            results[mode].append(run_sample(mode == 'individual', latency_ms/1000))
    summary = {}
    for mode, rows in results.items():
        summary[mode] = {'samples':rows}
        for field in ('capture_ms','complete_ms','first_imported_jd_ms','warm_ms'):
            values = [r[field] for r in rows]
            summary[mode][field] = {'median':round(statistics.median(values),3),'range':[min(values),max(values)]}
    return {'fictional_only':True,'python':sys.version.split()[0], 'sample_count':samples,
        'fixed_transport_overhead_ms':latency_ms, 'unique_pages':12,'duplicate_inputs':2,
        'comparison':summary,'live_host_workflow':'not measured','tinyfish_hybrid':'unsupported in this increment',
        'internal_provider_queueing':None,'observed_cost':None,'tokens':None,
        'browser_sessions':'not measured','human_wait':'not measured',
        'limits':'Simulated transport overhead and local SQLite only. No live provider, browser, paid cost or application-throughput inference. Accuracy uses supplied fixture normalization, not an autonomous parser.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples',type=int,default=7)
    parser.add_argument('--latency-ms',type=int,default=30)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.samples,args.latency_ms),ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
