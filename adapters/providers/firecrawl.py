"""Auditable Firecrawl v2 HTTP adapter. Stdlib, fixed origin, no implicit retries.

Only public search/scrape/batch endpoints are exposed. No actions, cookies,
profiles, parsers, screenshots, uploads, Interact or autonomous agent API.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .contracts import ProviderCapabilities, ProviderError

BASE = 'https://api.firecrawl.dev/v2'
MAX_BYTES = 12_000_000
ID = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
CAPABILITIES = ProviderCapabilities('firecrawl-v2', search=True, scrape=True,
                                    batch_extraction=True, cancellation=True)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def retry_delay(value: str | None) -> float | None:
    try:
        delay = float(value)
        return max(0., delay) if math.isfinite(delay) else None
    except (ValueError, TypeError):
        try:
            return max(0., (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None


class HTTPTransport:
    """No redirect, proxy, compression or SDK retry; 15s socket timeout.

    HTTP 429/402 are definitely rejected; connection/response failures on POST
    are conservatively possibly accepted. Raw exception/response data is hidden.
    """
    def __init__(self, key: str):
        if not key or '\r' in key or '\n' in key:
            raise ProviderError('missing_credentials')
        self._key = key

    def __call__(self, method: str, url: str, payload: dict | None) -> dict:
        if not url.startswith(BASE+'/'):
            raise ProviderError('invalid_provider_endpoint')
        request = Request(url, method=method,
            data=json.dumps(payload).encode('utf8') if payload is not None else None,
            headers={'Authorization': 'Bearer '+self._key, 'Content-Type': 'application/json',
                     'Accept': 'application/json', 'Accept-Encoding': 'identity'})
        try:
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=15) as response:
                if response.headers.get_content_type() != 'application/json' or response.headers.get('Content-Encoding', 'identity') != 'identity':
                    raise ProviderError('invalid_response', possibly_accepted=method != 'GET')
                content = response.read(MAX_BYTES+1)
            if len(content) > MAX_BYTES:
                raise ProviderError('response_too_large', possibly_accepted=method != 'GET')
            value = json.loads(content)
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except HTTPError as error:
            code, delay = error.code, retry_delay(error.headers.get('Retry-After'))
            error.close()
            known_rejection = code in {400, 401, 402, 403, 404, 422, 429}
            raise ProviderError('http_'+str(code), possibly_accepted=method != 'GET' and not known_rejection,
                                retry_after=delay) from None
        except (OSError, URLError, ValueError, UnicodeError):
            raise ProviderError('transport_uncertain', possibly_accepted=method != 'GET') from None


class Firecrawl:
    capabilities = CAPABILITIES

    def __init__(self, transport=None, *, account_concurrency=None):
        self.transport = transport or HTTPTransport(os.environ.get('FIRECRAWL_API_KEY', ''))
        value = account_concurrency if account_concurrency is not None else os.environ.get('FIRECRAWL_MAX_CONCURRENCY', '1')
        try:
            self.account_concurrency = int(value)
        except (ValueError, TypeError):
            raise ProviderError('invalid_account_concurrency') from None
        if not 1 <= self.account_concurrency <= 4:
            raise ProviderError('invalid_account_concurrency')

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        value = self.transport(method, BASE+path, payload)
        if not isinstance(value, dict):
            raise ProviderError('invalid_response', possibly_accepted=method != 'GET')
        if value.get('success') is False:
            raise ProviderError('provider_failure', possibly_accepted=method != 'GET')
        return value

    @staticmethod
    def options(max_age_ms: int) -> dict:
        return {'formats': ['markdown'], 'onlyMainContent': True, 'maxAge': max_age_ms,
                'timeout': 10000, 'parsers': []}

    def search(self, query: str, hosts: list[str], limit: int) -> dict:
        return self.request('POST', '/search', {'query': query, 'limit': limit,
                            'sources': ['web'], 'includeDomains': hosts})

    def scrape(self, url: str, max_age_ms: int) -> dict:
        return self.request('POST', '/scrape', {'url': url, **self.options(max_age_ms)})

    def start_batch(self, urls: list[str], concurrency: int, max_age_ms: int) -> dict:
        return self.request('POST', '/batch/scrape', {'urls': urls, 'maxConcurrency': concurrency,
                            'ignoreInvalidURLs': False, **self.options(max_age_ms)})

    @staticmethod
    def batch_path(remote_id: str) -> str:
        if not isinstance(remote_id, str) or not ID.fullmatch(remote_id):
            raise ProviderError('invalid_remote_id')
        return '/batch/scrape/'+remote_id

    def continuation_path(self, remote_id: str, value: str) -> str:
        parsed = urlsplit(value)
        expected = '/v2'+self.batch_path(remote_id)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if (parsed.scheme != 'https' or parsed.netloc != 'api.firecrawl.dev' or
                parsed.path != expected or parsed.fragment or set(query)-{'skip', 'limit'} or
                any(len(v) != 1 or not v[0].isdigit() or len(v[0]) > 8 for v in query.values())):
            raise ProviderError('unsafe_continuation')
        return parsed.path[3:] + ('?'+parsed.query if parsed.query else '')

    def status(self, remote_id: str, continuation: str | None = None) -> dict:
        path = self.continuation_path(remote_id, continuation) if continuation else self.batch_path(remote_id)
        return self.request('GET', path)

    def errors(self, remote_id: str) -> dict:
        return self.request('GET', self.batch_path(remote_id)+'/errors')

    def cancel(self, remote_id: str) -> dict:
        return self.request('DELETE', self.batch_path(remote_id))
