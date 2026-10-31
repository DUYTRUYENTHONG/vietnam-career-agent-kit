"""Bounded public board discovery; no candidate data or application writes."""
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
    return _read_json(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')


def read_ashby_board(board: str) -> bytes:
    """Read one explicit public Ashby board, never the authenticated application API."""
    if not isinstance(board, str) or not TOKEN.fullmatch(board):
        raise ContractError('Invalid Ashby board token')
    return _read_json(f'https://api.ashbyhq.com/posting-api/job-board/{board}')


def _read_json(url: str) -> bytes:
    """Transport shared by validated fixed-origin board readers only."""
    request = Request(url,
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


def normalize_ashby(board: str, raw: bytes) -> dict:
    """Keep listed posts and explicit location/type fields; remote is not country eligibility."""
    if not isinstance(board, str) or not TOKEN.fullmatch(board):
        raise ContractError('Invalid Ashby board token')
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError('Expected board bytes within 4 MB')
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get('apiVersion') != '1':
        raise ValueError('Expected Ashby posting API version 1')
    jobs = payload.get('jobs')
    if not isinstance(jobs, list) or len(jobs) > MAX_JOBS:
        raise ValueError('Expected at most 5000 board jobs')
    leads = {}

    def field(item, name):
        value = item.get(name, '')
        if not isinstance(value, str):
            raise ValueError('Invalid text field')
        return value

    for item in jobs:
        if not isinstance(item, dict) or type(item.get('isListed')) is not bool:
            raise ValueError('Expected explicit listed status')
        if not item['isListed']:
            continue  # Never expose direct-link-only postings in a public discovery list.
        title, url = field(item, 'title'), field(item, 'jobUrl')
        parsed = urlsplit(url)
        parts = parsed.path.strip('/').split('/')
        if (not title.strip() or parsed.scheme != 'https' or parsed.netloc != 'jobs.ashbyhq.com'
                or len(parts) != 2 or parts[0] != board or not TOKEN.fullmatch(parts[1])):
            raise ValueError('Expected a title and same-board public Ashby job URL')
        workplace, employment = field(item, 'workplaceType'), field(item, 'employmentType')
        if workplace not in {'', 'OnSite', 'Remote', 'Hybrid'}:
            raise ValueError('Unsupported workplace type')
        if employment not in {'', 'FullTime', 'PartTime', 'Intern', 'Contract', 'Temporary'}:
            raise ValueError('Unsupported employment type')
        remote = item.get('isRemote')
        if remote is not None and type(remote) is not bool:
            raise ValueError('Invalid remote flag')
        address = item.get('address', {})
        if not isinstance(address, dict) or not isinstance(address.get('postalAddress', {}), dict):
            raise ValueError('Invalid address')
        secondary = item.get('secondaryLocations', [])
        if not isinstance(secondary, list):
            raise ValueError('Invalid secondary locations')
        locations = []
        for location in secondary:
            if not isinstance(location, dict) or not isinstance(location.get('address', {}), dict):
                raise ValueError('Invalid secondary location')
            locations.append({'location': field(location, 'location'),
                              'country': field(location.get('address', {}), 'addressCountry')})
        plain, html = field(item, 'descriptionPlain'), field(item, 'descriptionHtml')
        ident = parts[1]
        key = f'ashby:{board}:{ident}'
        lead = {'key': key, 'platform_job_id': ident, 'title': title,
                'location': field(item, 'location'),
                'country': field(address.get('postalAddress', {}), 'addressCountry'),
                'secondary_locations': locations, 'workplace_type': workplace,
                'is_remote': remote, 'employment_type': employment,
                'department': field(item, 'department'), 'team': field(item, 'team'),
                'published_at': field(item, 'publishedAt'), 'url': url,
                'content': plain or html, 'content_format': 'plain' if plain else 'html' if html else ''}
        lead['fingerprint'] = hashlib.sha256(json.dumps(lead, sort_keys=True,
                                             ensure_ascii=False).encode('utf8')).hexdigest()
        if key in leads and leads[key] != lead:
            raise ValueError('Conflicting duplicate post ID')
        leads[key] = lead
    return {'board': board, 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'leads': list(leads.values()), 'records_received': len(jobs)}


def discover(boards: list[str], *, workers: int = 3, include_content: bool = False,
             reader=None, provider: str = 'greenhouse') -> dict:
    """Concurrent reads, deterministic merge, partial failures explicit. No ledger writes."""
    if provider not in {'greenhouse', 'ashby'}:
        raise ContractError('Unsupported public board provider')
    if not boards or len(boards) > 12 or any(not isinstance(b, str) or not TOKEN.fullmatch(b) for b in boards):
        raise ContractError('Use 1-12 explicit board tokens (letters, digits, underscore, hyphen)')
    if type(workers) is not int or not 1 <= workers <= 3:
        raise ContractError('Discovery workers must be 1-3')
    if type(include_content) is not bool:
        raise ContractError('include_content must be boolean')
    unique = list(dict.fromkeys(boards))
    reader = reader or (read_board if provider == 'greenhouse' else read_ashby_board)
    normalizer = normalize if provider == 'greenhouse' else normalize_ashby

    def fetch(board):
        try:
            result = normalizer(board, reader(board))
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
            'source': f'{provider}-public-board', 'boards': results,
            'leads_count': sum(len(r.get('leads', [])) for r in results),
            'failed_boards': sum('error' in r for r in results),
            'notice': 'Untrusted discovery leads only; verify fit, Vietnam eligibility, liveness and application rules. No submissions or ledger changes.'}
