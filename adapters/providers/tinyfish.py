"""Opt-in TinyFish Fetch: public evidence only, no Agent/browser/upload API.

One batch POST covers at most ten reviewed URLs. No automatic retries: a lost
response may represent accepted work. Caller owns durable intent/accounting.
"""
import hashlib
import json
import os
import socket
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, build_opener

from .contracts import ContractError, ProviderCapabilities, ProviderError, canonical_url
from .firecrawl import NoRedirect, retry_delay

ENDPOINT = 'https://api.fetch.tinyfish.ai'
MAX_BYTES = 2_000_000
CAPABILITIES = ProviderCapabilities('tinyfish-fetch', scrape=True, batch_extraction=True)


class HTTPTransport:
    def __init__(self, key):
        if not isinstance(key, str) or not key.strip() or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise ProviderError('missing_credentials')
        self._key = key

    def __call__(self, method, url, payload):
        if method != 'POST' or url != ENDPOINT:
            raise ProviderError('invalid_provider_endpoint')
        request = Request(url, method='POST', data=json.dumps(payload).encode('utf-8'),
            headers={'X-API-Key': self._key, 'Content-Type': 'application/json',
                     'Accept': 'application/json', 'Accept-Encoding': 'identity'})
        try:
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=15) as response:
                if (response.headers.get_content_type() != 'application/json' or
                        response.headers.get('Content-Encoding', 'identity') != 'identity'):
                    raise ProviderError('invalid_response', possibly_accepted=True)
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ProviderError('response_too_large', possibly_accepted=True)
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ProviderError('invalid_response', possibly_accepted=True)
            return value
        except HTTPError as error:
            raise ProviderError('http_'+str(error.code),
                possibly_accepted=error.code not in (400, 401, 402, 403, 404, 422, 429),
                retry_after=retry_delay(error.headers.get('Retry-After'))) from None
        except ProviderError:
            raise
        except Exception:
            raise ProviderError('transport_failure', possibly_accepted=True) from None


class TinyFish:
    capabilities = CAPABILITIES

    def __init__(self, transport=None, *, resolver=socket.getaddrinfo):
        self.transport = transport if transport is not None else HTTPTransport(os.environ.get('TINYFISH_API_KEY'))
        self.resolver = resolver

    def fetch(self, plan, urls=None):
        """Return ordered per-URL outcomes from one server-parallel Fetch batch.

        ResearchPlan workers governs local workers; this operation starts one
        request. Provider-internal concurrency is not measurable or configurable.
        Final redirects must exactly match the selected URL to be accepted.
        """
        selected = plan.payload['urls'] if urls is None else urls
        if not isinstance(selected, list) or not 1 <= len(selected) <= 10:
            raise ContractError('Use 1-10 bounded public research URLs')
        selected = [canonical_url(u) for u in selected]
        allowed = {canonical_url(u) for u in plan.payload['urls']}
        if len(set(selected)) != len(selected) or any(u not in allowed for u in selected):
            raise ContractError('Use distinct explicitly selected plan URLs')
        sources = {u: plan.source(u, resolver=self.resolver) for u in selected}
        try:
            response = self.transport('POST', ENDPOINT, {'urls': selected, 'format': 'markdown'})
            if (not isinstance(response, dict) or not isinstance(response.get('results'), list) or
                    not isinstance(response.get('errors', []), list) or len(response['results']) > len(selected)):
                raise ProviderError('invalid_response', possibly_accepted=True)
        except Exception as error:
            code = error.code if isinstance(error, ProviderError) and error.code in {
                'response_too_large', 'invalid_response', 'transport_failure',
                'http_400', 'http_401', 'http_402', 'http_403', 'http_404', 'http_422', 'http_429'} else 'provider_failure'
            return [self.failure(u, code, error.possibly_accepted if isinstance(error, ProviderError) else True) for u in selected]
        pages = {}
        duplicates = set()
        for page in response['results']:
            try:
                url = canonical_url(page['url'])
                if url in pages: duplicates.add(url)
                pages[url] = page
            except (ContractError, KeyError, TypeError, ValueError):
                continue
        outcomes = []
        for url in selected:
            page = pages.get(url)
            try:
                if url in duplicates or not isinstance(page, dict):
                    raise ValueError()
                if canonical_url(page['final_url']) != url:
                    raise ValueError()
                text = page['text']
                if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > MAX_BYTES:
                    raise ValueError()
                outcomes.append({'url_key': self.key(url), 'state': 'completed',
                    'source_id': sources[url]['source_id'], 'data': {'markdown': text, 'final_url': url},
                    'liveness': 'unverified'})
            except (ContractError, KeyError, TypeError, ValueError):
                outcomes.append(self.failure(url, 'invalid_or_missing_page', False))
        return outcomes

    @staticmethod
    def key(url):
        return hashlib.sha256(url.encode()).hexdigest()

    @classmethod
    def failure(cls, url, code, accepted):
        return {'url_key': cls.key(url), 'state': 'manual_required',
                'error': {'code': code, 'possibly_accepted': accepted}}
