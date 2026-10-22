"""Bounded public Greenhouse discovery; no candidate data or application writes."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .contracts import ContractError

MAX_BYTES = 4_000_000
MAX_JOBS = 5000
TOKEN = re.compile(r'[a-zA-Z0-9_-]{1,80}\Z')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_board(board: str) -> bytes:
    """One fixed-origin GET, no cookies/auth/proxies/redirects/retries."""
    if not isinstance(board, str) or not TOKEN.fullmatch(board):
        raise ContractError('Invalid Greenhouse board token')
    request = Request(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true',
                      headers={'Accept': 'application/json', 'Accept-Encoding': 'identity',
                               'User-Agent': 'VietnamCareerAgentKit/1.0 public-discovery'})
    with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=10) as response:
        if response.headers.get_content_type() != 'application/json':
            raise ValueError('Expected JSON response')
        if response.headers.get('Content-Encoding', 'identity') != 'identity':
            raise ValueError('Compressed response unsupported')
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Board response exceeds 4 MB')
    return raw


def normalize(board: str, raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError('Board response exceeds 4 MB')
    payload = json.loads(raw)
    jobs = payload.get('jobs') if isinstance(payload, dict) else None
    if not isinstance(jobs, list) or len(jobs) > MAX_JOBS:
        raise ValueError('Expected at most 5000 board jobs')
    leads = {}
    for item in jobs:
        if not isinstance(item, dict):
            raise ValueError('Invalid job record')
        ident, title, url = item.get('id'), item.get('title'), item.get('absolute_url')
        if type(ident) is not int or ident <= 0 or not isinstance(title, str) or not title.strip():
            raise ValueError('Job needs a positive post ID and title')
        if not isinstance(url, str):
            raise ValueError('Job needs a public HTTPS URL')
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Job needs a public HTTPS URL without credentials')
        location = item.get('location') or {}
        if not isinstance(location, dict) or not isinstance(location.get('name', ''), str):
            raise ValueError('Invalid location')
        content = item.get('content', '')
        if not isinstance(content, str):
            raise ValueError('Invalid job content')
        key = f'greenhouse:{board}:{ident}'
        lead = {'key': key, 'platform_job_id': str(ident), 'title': title,
                'location': location.get('name', ''), 'url': url, 'content': content}
        lead['fingerprint'] = hashlib.sha256(json.dumps(lead, sort_keys=True,
                                             ensure_ascii=False).encode('utf8')).hexdigest()
        if key in leads and leads[key] != lead:
            raise ValueError('Conflicting duplicate post ID')
        leads[key] = lead
    return {'board': board, 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'leads': list(leads.values()), 'records_received': len(jobs)}


def discover(boards: list[str], *, workers: int = 3, include_content: bool = False, reader=None) -> dict:
    """Concurrent reads, deterministic merge, partial failures explicit. No ledger writes."""
    if not boards or len(boards) > 12 or any(not isinstance(b, str) or not TOKEN.fullmatch(b) for b in boards):
        raise ContractError('Use 1-12 explicit Greenhouse board tokens (letters, digits, underscore, hyphen)')
    if type(workers) is not int or not 1 <= workers <= 3:
        raise ContractError('Discovery workers must be 1-3')
    if type(include_content) is not bool:
        raise ContractError('include_content must be boolean')
    unique = list(dict.fromkeys(boards))
    reader = reader or read_board

    def fetch(board):
        try:
            result = normalize(board, reader(board))
            if not include_content:
                for lead in result['leads']:
                    del lead['content']  # Fingerprint still covers the full current JD.
            return result
        except (ValueError, UnicodeError, OSError, HTTPError, URLError, RecursionError) as error:
            # Do not return response bodies or remote-controlled error strings.
            if isinstance(error, HTTPError):
                error.close()
            return {'board': board, 'error': type(error).__name__,
                    'http_status': error.code if isinstance(error, HTTPError) else None}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(fetch, unique))
    return {'schema_version': '1.0', 'observed_utc': datetime.now(timezone.utc).isoformat(),
            'source': 'greenhouse-public-board', 'boards': results,
            'leads_count': sum(len(r.get('leads', [])) for r in results),
            'failed_boards': sum('error' in r for r in results),
            'notice': 'Untrusted discovery leads only; verify fit, Vietnam eligibility, liveness and application rules. No submissions or ledger changes.'}
