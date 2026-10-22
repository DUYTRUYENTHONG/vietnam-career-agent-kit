"""Versioned public-research contracts. No candidate or application authority."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime, timezone
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from core.contracts import ContractError, object_fields

VERSION = '1.0'
PARSER_VERSION = 'public-markdown-1'
# These sources remain manual even when labelled as a generic employer source.
MANUAL_HOSTS = ('linkedin.com', 'itviec.com', 'topcv.vn', 'vietnamworks.com',
                'careerviet.vn', 'saramin.vn', 'topdev.vn')


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: str
    search: bool = False
    scrape: bool = False
    batch_extraction: bool = False
    goal_interaction: bool = False
    browser_sessions: bool = False
    persistent_profiles: bool = False
    uploads: bool = False
    screenshots: bool = False
    cancellation: bool = False
    idempotency: bool = False
    schema_version: str = VERSION


@dataclass(frozen=True)
class DiscoveryHit:
    url: str
    title: str
    snippet: str
    source_id: str
    schema_version: str = VERSION


@dataclass(frozen=True)
class ProviderUsage:
    credits: float | None = None
    tokens: int | None = None
    billed_cost: float | None = None
    provider_seconds: float | None = None
    schema_version: str = VERSION


@dataclass(frozen=True)
class ProviderTask:
    trace_id: str
    operation: str
    state: str
    remote_id: str | None
    schema_version: str = VERSION


@dataclass(frozen=True)
class PageEvidence:
    original_url: str
    final_url: str | None
    source_id: str
    provider: str
    retrieved_utc: str
    content_sha256: str
    markdown: str
    normalized_fields: dict[str, Any]
    missing_fields: list[str]
    extraction_status: str
    liveness: str = 'unverified'
    provider_cache_timestamp: str | None = None
    source_timestamp: str | None = None
    parser_version: str = PARSER_VERSION
    schema_version: str = VERSION


class ProviderError(Exception):
    """Safe diagnostic: never include provider bodies, URLs, keys or paths."""
    def __init__(self, code: str, *, possibly_accepted: bool = False,
                 retry_after: float | None = None):
        super().__init__(code)
        self.code = code
        self.possibly_accepted = possibly_accepted
        self.retry_after = retry_after

    def json(self) -> dict:
        return {'schema_version':VERSION, 'code':self.code,
                'possibly_accepted':self.possibly_accepted, 'retry_after':self.retry_after}


def timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError, AttributeError) as error:
        raise ContractError('Expected timezone-aware UTC expiry') from error


def canonical_url(value: str) -> str:
    """Keep meaningful query parameters; discard only the non-request fragment."""
    if not isinstance(value, str) or len(value) > 2048 or re.search(r'[\x00-\x20\\]', value):
        raise ContractError('Invalid public URL')
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ContractError('Invalid public port') from error
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
            parsed.password or port not in (None, 443) or parsed.hostname.endswith('.')):
        raise ContractError('Public research requires credential-free HTTPS on port 443')
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        normalized = re.sub(r'[^a-z]', '', key.lower())
        if any(word in normalized for word in ('token','secret','password','signature','apikey','auth','session','email','credential')) or '@' in item:
            raise ContractError('Access-bearing or identifying query parameter')
    return urlunsplit(('https', parsed.hostname.lower(), parsed.path or '/', parsed.query, ''))


def public_host(host: str, resolver=socket.getaddrinfo) -> None:
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise ContractError('Private destinations are unsupported')
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in resolver(host, 443, type=socket.SOCK_STREAM)]
        except OSError as error:
            raise ContractError('Public destination DNS could not be verified') from error
    if not addresses or any(not address.is_global for address in addresses):
        raise ContractError('Private, loopback and metadata destinations are unsupported')


@dataclass(frozen=True)
class ResearchPlan:
    """Finite reviewed public scope; contains no candidate identity or files."""
    payload: dict[str, Any]
    schema_version: str = VERSION

    @classmethod
    def parse(cls, raw: Any) -> ResearchPlan:
        value = deepcopy(object_fields(raw, {'schema_version', 'plan_id', 'provider_account', 'expires_utc',
            'roles', 'locations', 'sources', 'urls', 'limits', 'freshness'}, set(), 'research plan'))
        if value['schema_version'] != VERSION:
            raise ContractError('Unsupported research plan version')
        for name in ('plan_id', 'provider_account'):
            if not isinstance(value[name], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value[name]):
                raise ContractError('Use opaque plan/account identifiers')
        timestamp(value['expires_utc'])
        for name in ('roles', 'locations'):
            items = value[name]
            if (not isinstance(items, list) or not 1 <= len(items) <= 4 or
                    any(not isinstance(s, str) or not s.strip() or len(s) > 100 or
                        re.search(r'[@\r\n]|https?://', s) for s in items)):
                raise ContractError('Use 1-4 non-identifying public role/location terms')
        limits = object_fields(value['limits'], {'requests', 'pages', 'workers', 'domain_workers',
            'runtime_seconds', 'credit_reservation'}, set(), 'research limits')
        for name, maximum in [('requests', 100), ('pages', 24), ('workers', 4),
                              ('domain_workers', 1), ('runtime_seconds', 300), ('credit_reservation', 1000)]:
            if type(limits[name]) is not int or not 1 <= limits[name] <= maximum:
                raise ContractError('Invalid bounded research limit: '+name)
        freshness = object_fields(value['freshness'], {'search_seconds', 'page_seconds', 'provider_max_age_ms'},
                                  set(), 'freshness')
        for name, maximum in [('search_seconds', 3600), ('page_seconds', 21600), ('provider_max_age_ms', 21600000)]:
            if type(freshness[name]) is not int or not 0 <= freshness[name] <= maximum:
                raise ContractError('Invalid freshness policy')
        if not isinstance(value['sources'], list) or not 1 <= len(value['sources']) <= 12:
            raise ContractError('Use 1-12 explicitly reviewed public sources')
        hosts = set()
        for source in value['sources']:
            object_fields(source, {'source_id', 'host', 'permission_reference', 'expires_utc', 'public_read_allowed'},
                          set(), 'source permission')
            if source['source_id'] not in {'employer-careers', 'public-feed', 'university-alumni', 'greenhouse-public-board'}:
                raise ContractError('Source is manual or unsupported; provider hopping is prohibited')
            host = urlsplit(canonical_url('https://'+source['host'])).hostname
            if host != source['host'] or host in hosts or any(host == h or host.endswith('.'+h) for h in MANUAL_HOSTS):
                raise ContractError('Duplicate, invalid or manual-only source host')
            if source['public_read_allowed'] is not True or not isinstance(source['permission_reference'], str) or not source['permission_reference'].strip():
                raise ContractError('Source permission must be reviewed independently of provider access')
            timestamp(source['expires_utc'])
            hosts.add(host)
        if not isinstance(value['urls'], list) or len(value['urls']) > limits['pages']:
            raise ContractError('Too many selected extraction URLs')
        for url in value['urls']:
            if urlsplit(canonical_url(url)).hostname not in hosts:
                raise ContractError('Extraction URL is outside reviewed source scope')
        return cls(value)

    def queries(self) -> list[str]:
        roles, locations = self.payload['roles'], self.payload['locations']
        return [f'{role} {location} {suffix}' for role in roles for location in locations
                for suffix in ('jobs careers', 'tuyển dụng việc làm')]

    def source(self, url: str, *, resolve: bool = True, resolver=socket.getaddrinfo) -> dict:
        host = urlsplit(canonical_url(url)).hostname
        now = datetime.now(timezone.utc)
        if timestamp(self.payload['expires_utc']) <= now:
            raise ContractError('Research plan expired')
        source = next((s for s in self.payload['sources'] if s['host'] == host), None)
        if source is None or timestamp(source['expires_utc']) <= now:
            raise ContractError('Source is outside current permission scope')
        if resolve:
            public_host(host, resolver)
        return source
