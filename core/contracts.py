"""Strict versioned preparation inputs. Semantic truth still needs human review."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Literal
import unicodedata

from .ledger import PackageError, _https

VERSION = '1.0'
OutcomeName = Literal['ok', 'blocked', 'needs_input', 'manual_required', 'failed', 'submission_unknown']


class ContractError(ValueError):
    """An invalid input with an actionable field locator."""


@dataclass(frozen=True)
class Outcome:
    outcome: OutcomeName
    data: dict[str, Any]
    issues: list[str]
    message: str = ''
    schema_version: str = VERSION

    def json(self) -> dict[str, Any]:
        return asdict(self)


def object_fields(value: Any, required: set[str], optional: set[str], label: str) -> dict:
    if not isinstance(value, dict):
        raise ContractError(f'{label}: expected an object')
    missing, unknown = required - value.keys(), value.keys() - required - optional
    if missing or unknown:
        raise ContractError(f'{label}: missing {sorted(missing)}, unsupported {sorted(unknown)}')
    return value


def text(value: Any, label: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or ('\x00' in value) or (not empty and not value.strip()):
        raise ContractError(f'{label}: expected a nonblank string' if not empty else f'{label}: expected a string')
    return value


def choice(value: Any, choices: set, label: str) -> Any:
    if not isinstance(value, (str, type(None))) or value not in choices:
        raise ContractError(f'{label}: choose one of {sorted(str(x) for x in choices)}')
    return value


def boolean(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ContractError(f'{label}: expected true or false')
    return value


def strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f'{label}: expected a list')
    for item in value:
        text(item, label)
    if len(set(value)) != len(value):
        raise ContractError(f'{label}: duplicate values')
    return value


def version(value: dict, label: str) -> None:
    if value.get('schema_version') != VERSION:
        raise ContractError(f'{label}.schema_version: only {VERSION} is supported; migrate explicitly')


def salary(value: Any, label: str) -> None:
    object_fields(value, {'amount', 'currency', 'period', 'gross_net', 'bonus'}, set(), label)
    amount = value['amount']
    if amount is not None and (type(amount) not in (int, float) or not 0 <= amount < float('inf')):
        raise ContractError(f'{label}.amount: expected a finite nonnegative number or null')
    choice(value['currency'], {None, 'VND', 'USD'}, label+'.currency')
    choice(value['period'], {None, 'monthly', 'annual'}, label+'.period')
    choice(value['gross_net'], {None, 'gross', 'net'}, label+'.gross_net')
    if value['bonus'] is not None:
        text(value['bonus'], label+'.bonus')


PREFERENCE_LISTS = {'target_roles', 'preferred_cities', 'work_models', 'employment_types',
                    'excluded_employers', 'excluded_industries', 'existing_applications'}
PREFERENCE_TEXT = {'seniority', 'relocation', 'remote_eligibility', 'notice_period',
                   'availability', 'work_authorization', 'document_language'}


def validate_profile(raw: Any) -> dict:
    value = deepcopy(object_fields(raw, {'schema_version', 'candidate_id', 'name', 'language',
                                         'preferences', 'facts'}, {'contacts'}, 'profile'))
    version(value, 'profile')
    for name in ('candidate_id', 'name'):
        text(value[name], 'profile.'+name)
    choice(value['language'], {'en', 'vi'}, 'profile.language')
    prefs = object_fields(value['preferences'], set(), PREFERENCE_LISTS | PREFERENCE_TEXT | {'salary'}, 'preferences')
    for name in PREFERENCE_LISTS:
        if name in prefs and prefs[name] is not None:
            strings(prefs[name], 'preferences.'+name)
    for name in PREFERENCE_TEXT:
        if name in prefs and prefs[name] is not None:
            text(prefs[name], 'preferences.'+name)
    if prefs.get('salary') is not None:
        salary(prefs['salary'], 'preferences.salary')
    if 'contacts' in value:
        contacts = object_fields(value['contacts'], set(), {'email', 'phone', 'portfolio'}, 'contacts')
        for name, content in contacts.items():
            if content is not None:
                text(content, 'contacts.'+name)
    if not isinstance(value['facts'], list) or not value['facts']:
        raise ContractError('profile.facts: provide at least one source-backed fact')
    ids = set()
    for fact in value['facts']:
        object_fields(fact, {'id', 'field', 'value', 'claim', 'source_id', 'quote', 'locator', 'status'},
                      {'conflict_key'}, 'fact')
        for name in ('id', 'field', 'value', 'claim', 'source_id', 'quote', 'locator'):
            text(fact[name], 'fact.'+name)
        choice(fact['status'], {'confirmed', 'pending', 'rejected'}, 'fact.status')
        if fact['claim'] != fact['quote']:
            raise ContractError('fact.claim: Slice 1 requires the exact source quote; paraphrases are not new evidence')
        if fact.get('conflict_key') is not None:
            text(fact['conflict_key'], 'fact.conflict_key')
        if fact['id'] in ids:
            raise ContractError('fact.id: duplicate '+fact['id'])
        ids.add(fact['id'])
    return value


def validate_job(raw: Any) -> dict:
    value = deepcopy(object_fields(raw, {'schema_version', 'platform', 'platform_job_id', 'employer',
        'req_id', 'title', 'url', 'city', 'country', 'work_model', 'employment_type', 'document_language',
        'raw_jd', 'liveness', 'readable', 'requirements', 'salary'}, {'industry', 'posted', 'deadline'}, 'job'))
    version(value, 'job')
    for name in ('platform', 'platform_job_id', 'employer', 'title', 'city', 'country', 'raw_jd'):
        text(value[name], 'job.'+name)
    text(value['req_id'], 'job.req_id', empty=True)
    try:
        _https(value['url'], 'job.url')
    except PackageError as error:
        raise ContractError(str(error)) from error
    choice(value['work_model'], {None, 'onsite', 'hybrid', 'remote'}, 'job.work_model')
    choice(value['employment_type'], {None, 'full_time', 'part_time', 'contract', 'internship'}, 'job.employment_type')
    choice(value['document_language'], {None, 'en', 'vi'}, 'job.document_language')
    choice(value['liveness'], {'active', 'closed', 'unverified'}, 'job.liveness')
    boolean(value['readable'], 'job.readable')
    salary(value['salary'], 'job.salary')
    for name in ('industry', 'posted', 'deadline'):
        if value.get(name) is not None:
            text(value[name], 'job.'+name)
    if not isinstance(value['requirements'], list) or not value['requirements']:
        raise ContractError('job.requirements: a search snippet/empty requirement list is not a complete JD')
    ids = set()
    for req in value['requirements']:
        object_fields(req, {'id', 'text', 'field', 'value', 'mandatory', 'hard'}, set(), 'requirement')
        for name in ('id', 'text', 'field', 'value'):
            text(req[name], 'requirement.'+name)
        for name in ('mandatory', 'hard'):
            boolean(req[name], 'requirement.'+name)
        if req['id'] in ids:
            raise ContractError('requirement.id: duplicate '+req['id'])
        ids.add(req['id'])
    if not value['readable']:
        value['liveness'] = 'unverified'
    return value


def normalize_city(value: str) -> str:
    folded = unicodedata.normalize('NFD', value.casefold()).replace('đ', 'd')
    key = ' '.join(''.join(c for c in folded if not unicodedata.combining(c)).replace('tp.', '').strip().split())
    return {'hcm':'ho chi minh city','hcmc':'ho chi minh city','ho chi minh':'ho chi minh city',
            'saigon':'ho chi minh city','ha noi':'hanoi','da nang':'da nang'}.get(key, key)
