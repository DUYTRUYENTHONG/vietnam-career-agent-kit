"""Controlled public-provider fixtures; never access real candidate data or URLs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from adapters.providers.contracts import ContractError, ProviderError
from adapters.providers.firecrawl import BASE, Firecrawl
from adapters.providers.research import Research
from core.execution import Executor
from core.ledger import canonical_hash
from core.workflow import Preparation, WorkflowError
from test_provider_contracts import plan

ROOT = Path(__file__).resolve().parents[1]


def public_dns(*args, **kwargs):
    return [(None, None, None, None, ('93.184.216.34', 443))]


class FakeTransport:
    def __init__(self, latency=0):
        self.calls = []; self.batches = {}; self.latency = latency
        self.fail_start = False; self.bad_next = False; self.cancel_uncertain = False
        self.cancelled = False; self.invalid_page = False; self.partial = False
        self.pages = {
            'https://jobs.example.test/role?id=1': '# Analyst\nExample Cooperative\nTP. Hồ Chí Minh, VN\nFull time hybrid\nSQL project experience required. Open vacancy.',
            'https://jobs.example.test/role?id=2': '# Tư vấn giải pháp\nExample Cooperative\nHồ Chí Minh, VN\nTiếng Việt. Không công bố lương.',
            'https://jobs.example.test/role?id=3': '# Closed role\nThis vacancy is closed.',
        }

    def document(self, url):
        return {'markdown': '' if self.invalid_page else self.pages[url],
                'metadata': {'url': url, 'sourceURL': url, 'statusCode': 200}}

    def __call__(self, method, url, payload):
        self.calls.append((method, url, deepcopy(payload)))
        if self.latency: time.sleep(self.latency)
        if url == BASE+'/search':
            return {'success': True, 'data': {'web': [{'url': u, 'title': 'Lead only', 'description': 'Search snippet'} for u in self.pages]}}
        if url == BASE+'/scrape':
            return {'success': True, 'data': self.document(payload['url'])}
        if url == BASE+'/batch/scrape':
            ident = 'batch-'+str(len(self.batches)+1)
            self.batches[ident] = payload['urls']
            if self.fail_start: raise ProviderError('lost_response', possibly_accepted=True)
            return {'success': True, 'id': ident}
        ident = url.split('/batch/scrape/')[1].split('/')[0].split('?')[0]
        if method == 'DELETE':
            if self.cancel_uncertain: raise ProviderError('lost_cancel', possibly_accepted=True)
            self.cancelled = True
            return {'status': 'cancelled'}
        if url.endswith('/errors'):
            return {'errors': [{'url': self.batches[ident][-1], 'error': 'secret remote string'}] if self.partial else [], 'robotsBlocked': []}
        data = [self.document(u) for u in self.batches[ident]]
        if self.partial: data = data[:-1]
        return {'status': 'cancelled' if self.cancelled else 'scraping' if self.cancel_uncertain else 'completed',
                'data': data, 'next': 'https://evil.example.test/steal' if self.bad_next else None,
                'creditsUsed': len(data), 'expiresAt': '2030-01-01T00:00:00Z'}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-research-')
        self.addCleanup(self.temp.cleanup)
        self.work = Executor(Path(self.temp.name)/'workspace'); self.work.init()
        self.fake = FakeTransport()
        self.research = Research(self.work, Firecrawl(self.fake), resolver=public_dns)

    def start(self, raw=None, individual=False):
        raw = raw or plan()
        return self.research.discover(raw, canonical_hash(raw), individual=individual)

    def test_dry_run_needs_no_workspace_key_or_dns(self):
        preview = Research(None).preview(plan())
        self.assertEqual(preview.data['network_calls'], 0)
        self.assertEqual(self.fake.calls, [])
        with self.assertRaises(WorkflowError): self.research.discover(plan(), 'not-reviewed')

    def test_batch_lifecycle_is_pending_until_evidence_saved_and_imported(self):
        result = self.start(); fingerprint = result.data['fingerprint']
        self.assertEqual(result.data['tasks'][0]['state'], 'running')
        self.assertEqual(result.data['evidence'], [])
        result = self.research.status(fingerprint)
        self.assertEqual(result.outcome, 'ok'); self.assertEqual(len(result.data['evidence']), 1)
        self.assertEqual(result.data['applications'], 0)
        self.assertIsNone(result.data['tokens']); self.assertIsNone(result.data['metrics']['host_reasoning'])
        ident = result.data['evidence'][0]['id']
        captured = json.loads(self.work.inside(result.data['evidence'][0]['artifact_path']).read_text(encoding='utf8'))
        self.assertEqual(captured['liveness'], 'unverified')
        self.assertIsNone(captured['provider_cache_timestamp'])
        raw = json.loads((ROOT/'examples/fictional/job.json').read_text(encoding='utf8'))
        raw.update(platform='employer-careers',url=captured['original_url'], raw_jd=captured['markdown'], title='Analyst', req_id='', liveness='unverified')
        raw['requirements'] = raw['requirements'][:1]
        refs = {'employer':'Example Cooperative','title':'Analyst','city':'TP. Hồ Chí Minh',
                'country':'VN','work_model':'hybrid','employment_type':'Full time',
                'requirement:R1':'SQL project experience required.'}
        imported = self.research.import_jd(ident, {'job':raw, 'references':refs})
        self.assertEqual(imported.data['job']['id'], 1)
        self.assertEqual(self.work.job_document(1)[0]['raw_jd'], captured['markdown'])
        refs['requirement:R1'] = 'Fabricated required experience'
        with self.assertRaises(ContractError): self.research.import_jd(ident, {'job':raw,'references':refs})
        self.work.inside(result.data['evidence'][0]['artifact_path']).write_text('{}')
        with self.assertRaises(WorkflowError): self.research.import_jd(ident, {'job':raw,'references':refs})

    def test_search_is_leads_only_and_deduplicated_before_extraction(self):
        raw = plan(); raw['urls'] = []
        result = self.start(raw)
        self.assertEqual(len(result.data['leads']), 3)
        self.assertEqual(result.data['evidence'], [])
        self.assertTrue(all(c[1].endswith('/search') for c in self.fake.calls))
        self.assertEqual(self.work.status()['jobs'], 0)

    def test_cache_warm_read_option_change_and_ttl(self):
        raw = plan(); first = self.start(raw)
        self.research.status(first.data['fingerprint'])
        before = len(self.fake.calls)
        raw['plan_id'] = 'warm'
        result = self.start(raw)
        self.assertEqual(result.data['cache_hits'], 1)
        self.assertEqual(len(self.fake.calls), before)
        raw['plan_id'] = 'new-options'; raw['freshness']['provider_max_age_ms'] = 0
        options = self.start(raw)
        self.assertEqual(len(self.fake.calls), before+1)
        self.research.status(options.data['fingerprint'])
        before = len(self.fake.calls)
        raw['plan_id'] = 'expired-cache'; raw['freshness']['provider_max_age_ms'] = 21600000
        with self.work._db() as db:
            db.execute("UPDATE research_cache SET expires_utc='2000-01-01T00:00:00Z'")
        self.start(raw); self.assertEqual(len(self.fake.calls), before+1)

    def test_stricter_cache_age_source_scope_and_changed_bytes_are_not_reused(self):
        raw = plan(); first = self.start(raw); self.research.status(first.data['fingerprint'])
        before = len(self.fake.calls)
        raw['plan_id'] = 'strict-age'; raw['freshness']['page_seconds'] = 0
        strict = self.start(raw)
        self.assertEqual(strict.data['cache_hits'], 0); self.assertEqual(len(self.fake.calls), before+1)
        self.research.status(strict.data['fingerprint'])
        raw = plan(); raw['plan_id'] = 'changed-scope'
        raw['sources'][0]['source_id'] = 'public-feed'
        result = self.start(raw); self.assertEqual(result.data['cache_hits'], 0)
        self.research.status(result.data['fingerprint'])
        raw = plan(); raw['plan_id'] = 'restore-fresh'
        fresh = self.start(raw); fresh = self.research.status(fresh.data['fingerprint'])
        self.work.inside(fresh.data['evidence'][0]['artifact_path']).write_text('{}')
        raw = plan(); raw['plan_id'] = 'changed-file'
        with self.assertRaises(WorkflowError): self.start(raw)

    def test_warm_evidence_needs_neither_credentials_nor_dns(self):
        from unittest.mock import patch
        raw = plan(); first = self.start(raw); self.research.status(first.data['fingerprint'])
        raw['plan_id'] = 'offline-warm'
        def no_dns(*a, **k): raise AssertionError('Warm local evidence must not resolve hosts')
        with patch.dict('os.environ', {}, clear=True):
            result = Research(self.work, resolver=no_dns).discover(raw, canonical_hash(raw))
        self.assertEqual(result.data['cache_hits'], 1)

    def test_interrupted_evidence_export_recovers_from_canonical_record(self):
        from unittest.mock import patch
        started = self.start()
        with patch.object(self.work, 'atomic_text', side_effect=OSError('fictional interruption')):
            with self.assertRaises(OSError): self.research.status(started.data['fingerprint'])
        with self.work._db() as db:
            original = db.execute('SELECT payload FROM research_evidence').fetchone()[0]
        result = self.research.status(started.data['fingerprint'])
        self.assertEqual(len(result.data['evidence']), 1)
        self.assertEqual(self.work.inside(result.data['evidence'][0]['artifact_path']).read_text(encoding='utf8'), original)


    def test_uncertain_paid_start_is_not_relaunched(self):
        self.fake.fail_start = True
        raw = plan(); first = self.start(raw)
        self.assertEqual(first.outcome, 'manual_required')
        second = self.start(raw)
        self.assertEqual(second.data['tasks'][0]['state'], 'uncertain')
        self.assertEqual(len(self.fake.calls), 1)
        raw['plan_id'] = 'another'
        with self.assertRaises(WorkflowError): self.start(raw)
        self.assertEqual(len(self.fake.calls), 1)

    def test_single_flight_across_coordinators(self):
        self.fake.latency = .05
        raw = plan()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.start(raw), range(2)))
        self.assertEqual(len(self.fake.calls), 1)
        self.assertTrue(any(r.data['tasks'][0]['state'] == 'running' for r in results))

    def test_domain_and_account_limits_span_separate_plans(self):
        self.start()
        another = plan(); another['plan_id'] = 'another-url'
        another['urls'] = ['https://jobs.example.test/role?id=2']
        with self.assertRaises(WorkflowError): self.start(another)
        self.assertEqual(len(self.fake.calls), 1)
        another['sources'][0]['host'] = 'other.example.test'
        another['urls'] = ['https://other.example.test/role']
        with self.assertRaises(WorkflowError): self.start(another)
        self.assertEqual(len(self.fake.calls), 1)

    def test_partial_failure_does_not_discard_completed_evidence(self):
        raw = plan(); raw['urls'] = list(self.fake.pages)
        result = self.start(raw); self.fake.partial = True
        result = self.research.status(result.data['fingerprint'])
        self.assertEqual(result.outcome, 'manual_required'); self.assertEqual(len(result.data['evidence']), 2)
        self.assertNotIn('secret remote string', json.dumps(result.json()))
        self.assertEqual(len(result.data['tasks'][0]['missing_url_keys']), 1)

    def test_silent_incomplete_success_is_still_partial(self):
        raw = plan(); raw['urls'] = list(self.fake.pages)
        result = self.start(raw); self.fake.partial = True
        original = self.fake.__call__
        def silent(*args):
            return {'errors':[], 'robotsBlocked':[]} if args[1].endswith('/errors') else original(*args)
        self.research._provider = Firecrawl(silent)
        result = self.research.status(result.data['fingerprint'])
        self.assertEqual(result.outcome, 'manual_required')
        self.assertEqual(len(result.data['tasks'][0]['missing_url_keys']), 1)

    def test_unsafe_pagination_does_not_forward_credentials(self):
        result = self.start(); self.fake.bad_next = True
        result = self.research.status(result.data['fingerprint'])
        self.assertEqual(result.outcome, 'manual_required')
        self.assertTrue(all(call[1].startswith(BASE+'/') for call in self.fake.calls))
        self.assertEqual(len(result.data['evidence']), 1)

    def test_empty_success_requires_review(self):
        result = self.start(); self.fake.invalid_page = True
        result = self.research.status(result.data['fingerprint'])
        self.assertEqual(result.outcome, 'manual_required'); self.assertEqual(result.data['evidence'], [])

    def test_cancel_is_reconciled_and_uncertain_cancel_retains_run(self):
        result = self.start(); self.fake.cancel_uncertain = True
        result = self.research.status(result.data['fingerprint'], cancel=True)
        self.assertEqual(result.data['tasks'][0]['state'], 'cancel_requested')
        before = len(self.fake.calls)
        self.research.status(result.data['fingerprint'], cancel=True)
        self.assertEqual(len(self.fake.calls), before)
        with self.work._db() as db:
            db.execute('UPDATE provider_tasks SET not_before_utc=NULL')
        self.fake.cancel_uncertain = False
        self.fake.cancelled = True  # The remote accepted cancellation; response was lost.
        result = self.research.status(result.data['fingerprint'], cancel=True)
        self.assertEqual(result.data['tasks'][0]['state'], 'cancelled')
        self.assertEqual(sum(c[0] == 'DELETE' for c in self.fake.calls), 1)

    def test_request_budget_and_source_expiry_block_before_network(self):
        raw = plan(); raw['limits']['requests'] = 1
        result = self.start(raw)
        before = len(self.fake.calls)
        with self.assertRaises(WorkflowError): self.research.status(result.data['fingerprint'])
        self.assertEqual(len(self.fake.calls), before)
        raw = plan(); raw['sources'][0]['expires_utc'] = '2000-01-01T00:00:00Z'
        with self.assertRaises(ContractError): self.start(raw)
        self.assertEqual(len(self.fake.calls), before)

    def test_candidate_account_isolation_and_no_transaction_during_network(self):
        original = self.fake.__call__
        def observed(*args):
            with self.work._db() as db:
                db.execute('BEGIN IMMEDIATE'); db.rollback()
            return original(*args)
        self.research._provider = Firecrawl(observed)
        first = self.start(); self.research.status(first.data['fingerprint'])
        other = Executor(Path(self.temp.name)/'other'); other.init()
        other_plan = plan()
        result = Research(other, Firecrawl(self.fake), resolver=public_dns).discover(other_plan, canonical_hash(other_plan))
        self.assertEqual(result.data['cache_hits'], 0)
        raw = plan(); raw['provider_account'] = 'other-account'
        result = self.start(raw); self.assertEqual(result.data['cache_hits'], 0)

    def test_migration_preserves_new_version_and_blocks_future(self):
        Preparation(self.work.data_dir).init(); self.work.init()
        with self.work._db() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 5)
            db.execute('PRAGMA user_version=6')
        with self.assertRaises(WorkflowError): self.work.init()
        with self.work._db() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 6)

    def test_cli_doctor_and_dry_run_without_keys(self):
        file = Path(self.temp.name)/'plan.json'; file.write_text(json.dumps(plan()), encoding='utf8')
        for args in [['provider-doctor'], ['discover', '--plan', str(file), '--dry-run']]:
            proc = subprocess.run([sys.executable, str(ROOT/'scripts/kit.py'), *args], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['data']['network_calls'], 0)

    def test_status_pagination_and_repeated_pages_preserve_original_bytes(self):
        raw = plan(); raw['urls'] = list(self.fake.pages)
        started = self.start(raw); original = self.fake.__call__
        def paged(method, url, payload):
            result = original(method, url, payload)
            if method == 'GET' and not url.endswith('/errors'):
                docs = result['data']
                result['data'] = docs[1:] if '?skip=1' in url else docs[:1]
                result['next'] = None if '?skip=1' in url else BASE+'/batch/scrape/batch-1?skip=1'
            return result
        self.research._provider = Firecrawl(paged)
        result = self.research.status(started.data['fingerprint'])
        self.assertEqual(len(result.data['evidence']), 3)
        snapshots = {e['id']:self.work.inside(e['artifact_path']).read_bytes() for e in result.data['evidence']}
        # Reconcile a repeated partial page (e.g. after a lost local acknowledgement).
        with self.work._db() as db: db.execute("UPDATE provider_tasks SET state='running'")
        result = self.research.status(started.data['fingerprint'])
        for e in result.data['evidence']:
            self.assertEqual(snapshots[e['id']], self.work.inside(e['artifact_path']).read_bytes())

    def test_expired_runtime_can_reconcile_but_never_relaunch(self):
        raw = plan(); result = self.start(raw)
        with self.work._db() as db:
            db.execute("UPDATE research_plans SET started_utc='2000-01-01T00:00:00Z'")
        result = self.research.status(result.data['fingerprint'])
        self.assertEqual(result.data['tasks'][0]['state'], 'completed')
        self.assertEqual(len(result.data['evidence']), 1)

    def test_retry_after_and_circuit_breaker_prevent_busy_status_loops(self):
        result = self.start(); count = 0
        def limited(*args):
            nonlocal count
            count += 1
            raise ProviderError('http_429', retry_after=60)
        self.research._provider = Firecrawl(limited)
        for _ in range(2): self.research.status(result.data['fingerprint'])
        self.assertEqual(count, 1)
        for _ in range(2):
            with self.work._db() as db: db.execute('UPDATE provider_tasks SET not_before_utc=NULL')
            self.research.status(result.data['fingerprint'])
        with self.work._db() as db: db.execute('UPDATE provider_tasks SET not_before_utc=NULL')
        last = self.research.status(result.data['fingerprint'])
        self.assertEqual(count, 3)
        self.assertEqual(last.data['tasks'][0]['error_code'], 'circuit_open_manual_reconciliation')

    def test_remote_expiry_retains_local_results_without_new_batch(self):
        result = self.start()
        def expired(*args): raise ProviderError('http_404')
        self.research._provider = Firecrawl(expired)
        result = self.research.status(result.data['fingerprint'])
        self.assertEqual(result.outcome, 'manual_required')
        self.assertEqual(result.data['tasks'][0]['error_code'], 'remote_expired_or_missing')
        self.assertEqual(result.data['tasks'][0]['state'], 'uncertain')

    def test_new_coordinator_resumes_persisted_id_without_paid_relaunch(self):
        result = self.start()
        recovered = Research(Executor(self.work.data_dir), Firecrawl(self.fake), resolver=public_dns)
        recovered.status(result.data['fingerprint'])
        self.assertEqual(sum(call[1] == BASE+'/batch/scrape' for call in self.fake.calls), 1)
        self.assertEqual(len(recovered.summary(result.data['fingerprint']).data['evidence']), 1)

    def test_individual_and_batch_have_equal_evidence_quality(self):
        raw = plan(); raw['urls'] = [*self.fake.pages, list(self.fake.pages)[0]]
        batch = self.start(raw); batch = self.research.status(batch.data['fingerprint'])
        other = Executor(Path(self.temp.name)/'sequential'); other.init()
        sequential = Research(other, Firecrawl(FakeTransport()), resolver=public_dns)
        single = sequential.discover(raw, canonical_hash(raw), individual=True)
        def contents(work, result):
            return sorted(json.loads(work.inside(e['artifact_path']).read_text(encoding='utf8'))['content_sha256'] for e in result.data['evidence'])
        self.assertEqual(contents(self.work,batch), contents(other,single))
        self.assertEqual(len(batch.data['evidence']), 3)
        self.assertEqual(len(single.data['evidence']), 3)

    def test_benchmark_uses_equal_outputs_and_deterministic_request_budgets(self):
        from scripts.benchmark_web import benchmark
        result = benchmark(samples=1, latency_ms=0)
        individual = result['comparison']['individual']['samples'][0]
        batch = result['comparison']['batch']['samples'][0]
        self.assertEqual(individual['normalized_records'], batch['normalized_records'])
        self.assertEqual(individual['provider_calls'], 12)
        self.assertEqual(batch['provider_calls'], 3)
        self.assertEqual(batch['warm_provider_calls'], 0)
        self.assertEqual(batch['duplicate_fetches'], 0)
        self.assertEqual(result['live_host_workflow'], 'not measured')


if __name__ == '__main__': unittest.main()
