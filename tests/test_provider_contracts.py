"""Fictional provider boundary tests; no external request or credentials."""
from datetime import datetime, timedelta, timezone
from email.message import Message
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from adapters.providers.contracts import ContractError, ResearchPlan, canonical_url, public_host, ProviderError
from adapters.providers.firecrawl import Firecrawl, HTTPTransport, BASE


def plan():
    expiry = (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    return {'schema_version': '1.0', 'plan_id': 'fictional', 'provider_account': 'fixture-account',
        'expires_utc': expiry, 'roles': ['Analyst'], 'locations': ['Example City'],
        'sources': [{'source_id': 'employer-careers', 'host': 'jobs.example.test',
            'permission_reference': 'Fictional controlled fixture', 'expires_utc': expiry,
            'public_read_allowed': True}], 'urls': ['https://jobs.example.test/role?id=1'],
        'limits': {'requests': 30, 'pages': 10, 'workers': 4, 'domain_workers': 1,
            'runtime_seconds': 120, 'credit_reservation': 30},
        'freshness': {'search_seconds': 3600, 'page_seconds': 21600, 'provider_max_age_ms': 21600000}}


class ProviderContractsTests(unittest.TestCase):
    def test_scope_has_no_candidate_or_mutating_operations(self):
        raw = plan()
        value = ResearchPlan.parse(raw)
        self.assertEqual(len(value.queries()), 2)
        self.assertIn('tuyển dụng', value.queries()[1])
        raw['candidate'] = {'name': 'Fictional'}
        with self.assertRaises(ContractError): ResearchPlan.parse(raw)
        self.assertFalse(Firecrawl.capabilities.uploads)
        self.assertFalse(Firecrawl.capabilities.browser_sessions)

    def test_manual_source_cannot_be_relabelled_as_employer(self):
        raw = plan(); raw['sources'][0]['host'] = 'www.linkedin.com'; raw['urls'] = []
        with self.assertRaises(ContractError): ResearchPlan.parse(raw)
        raw = plan(); raw['sources'][0]['public_read_allowed'] = False
        with self.assertRaises(ContractError): ResearchPlan.parse(raw)

    def test_urls_preserve_requisitions_and_reject_private_or_access_urls(self):
        self.assertEqual(canonical_url('https://JOBS.example.test/role?req=1#part'),
                         'https://jobs.example.test/role?req=1')
        for url in ['http://example.test/', 'https://user:pass@example.invalid/',
                    'https://example.test/?token=secret', 'https://example.test/?%74oken=secret',
                    'https://example.test:8080/']:
            with self.assertRaises(ContractError): canonical_url(url)
        for host in ['127.0.0.1', '169.254.169.254', '::1', 'localhost', '10.0.0.1']:
            with self.assertRaises(ContractError): public_host(host)
        with self.assertRaises(ContractError):
            public_host('jobs.example.test', lambda *a, **k: [(None,None,None,None,('192.168.0.1',443))])

    def test_firecrawl_payloads_and_credential_safe_continuations(self):
        calls = []
        api = Firecrawl(lambda *args: calls.append(args) or {'success': True, 'id': 'task-1'})
        api.search('Analyst Example City', ['jobs.example.test'], 5)
        self.assertNotIn('scrapeOptions', calls[-1][2])
        api.start_batch(['https://jobs.example.test/role'], 1, 0)
        self.assertEqual(calls[-1][2]['maxConcurrency'], 1)
        self.assertEqual(calls[-1][2]['parsers'], [])
        api.status('task-1', BASE+'/batch/scrape/task-1?skip=2')
        for url in ['https://evil.example.test/v2/batch/scrape/task-1',
                    BASE+'/batch/scrape/other?skip=2', BASE+'/batch/scrape/task-1?token=x',
                    'https://api.firecrawl.dev@evil.example.invalid/v2/batch/scrape/task-1']:
            before = len(calls)
            with self.assertRaises(ProviderError): api.status('task-1', url)
            self.assertEqual(len(calls), before)
        api.cancel('task-1'); self.assertEqual(calls[-1][0], 'DELETE')

    def test_http_200_failure_is_not_success(self):
        api = Firecrawl(lambda *a: {'success': False, 'error': 'private content'})
        with self.assertRaises(ProviderError) as caught: api.start_batch([], 1, 0)
        self.assertNotIn('private', str(caught.exception))
        self.assertTrue(caught.exception.possibly_accepted)

    def test_unexpected_redirect_timeout_or_conflict_does_not_clear_paid_intent(self):
        for status in (302, 408, 409, 500, 429):
            error = HTTPError(BASE+'/batch/scrape', status, 'untrusted message', Message(), None)
            with patch('adapters.providers.firecrawl.build_opener') as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaises(ProviderError) as caught:
                    HTTPTransport('fictional-key')('POST', BASE+'/batch/scrape', {})
                self.assertEqual(caught.exception.possibly_accepted, status != 429)
                self.assertEqual(opener.return_value.open.call_count, 1)
                self.assertNotIn('untrusted', str(caught.exception))


if __name__ == '__main__': unittest.main()
