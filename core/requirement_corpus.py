"""Private captured-JD corpus preparation; no network, inference or tracker writes."""
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from time import perf_counter
import unicodedata
from urllib.parse import urlsplit

MAX_RECORDS = 1000
MAX_BYTES = 20_000_000
SOURCE_KINDS = {'full_jd', 'excerpt', 'assessment_summary', 'unknown'}
KINDS = {'required', 'preferred', 'unknown'}
REPO = Path(__file__).resolve().parents[1]


def _sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def _text(value, name, maximum=1_000_000):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf8')) > maximum:
        raise ValueError(name+': nonblank bounded UTF-8 text required')
    if any(unicodedata.category(c) == 'Cc' and c not in '\r\n\t' for c in value):
        raise ValueError(name+': unsupported control character')
    return value


def _clean(text):
    # No case/punctuation/number rewriting or semantic filtering.
    return '\n'.join(' '.join(line.split()) for line in
                     unicodedata.normalize('NFC', text).splitlines()).strip()


def _timestamp(value, name):
    if value is not None:
        _text(value, name, 100)
        try:
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as error:
            raise ValueError(name+': ISO timestamp required') from error
        if stamp.tzinfo is None:
            raise ValueError(name+': timezone required; unknown should be null')


def build_corpus(records):
    """Validate the whole batch, retaining all provenance and pending labels."""
    started = perf_counter()
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_RECORDS:
        raise ValueError('Select 1..1000 explicit captured records')
    total = len(json.dumps(records, ensure_ascii=False, allow_nan=False).encode('utf8'))
    if total > MAX_BYTES:
        raise ValueError('Corpus input exceeds 20 MB; use separate bounded batches')
    records = deepcopy(records)
    seen, documents, requirements = set(), {}, {}
    reference_bytes = 0
    required = {'id', 'employer', 'job_key', 'source_url', 'raw_text', 'source_kind'}
    optional = {'captured_utc', 'source_updated_utc', 'requirements'}
    for record in records:
        if not isinstance(record, dict) or not required <= record.keys() or record.keys()-required-optional:
            raise ValueError('Snapshot fields differ from requirements-corpus-v1')
        for key in ('id', 'employer', 'job_key', 'source_url'):
            _text(record[key], key, 4000)
        _text(record['raw_text'], 'raw_text')
        if record['id'] in seen:
            raise ValueError('Duplicate snapshot id: '+record['id'])
        seen.add(record['id'])
        url = urlsplit(record['source_url'])
        if url.scheme != 'https' or not url.hostname or url.username is not None or url.password is not None:
            raise ValueError('Use an explicit HTTPS source URL without credentials')
        if not isinstance(record['source_kind'], str) or record['source_kind'] not in SOURCE_KINDS:
            raise ValueError('Unknown source_kind; do not infer a complete primary JD')
        for name in ('captured_utc', 'source_updated_utc'):
            _timestamp(record.get(name), name)
        text = _clean(record['raw_text'])
        digest = _sha(text)
        source = {key: record[key] for key in ('id', 'employer', 'job_key', 'source_url', 'source_kind')}
        source.update(captured_utc=record.get('captured_utc'),
                      source_updated_utc=record.get('source_updated_utc'),
                      raw_text_sha256=_sha(record['raw_text']))
        document = documents.setdefault(digest, {'id': digest, 'text': text,
                                                 'sources': []})
        document['sources'].append(source)
        candidates = record.get('requirements', [])
        if not isinstance(candidates, list) or len(candidates) > 500:
            raise ValueError('requirements: select at most 500 explicit extracted quotes')
        ids = set()
        for req in candidates:
            if not isinstance(req, dict) or set(req) != {'id', 'quote', 'kind'}:
                raise ValueError('Each extraction requires exactly id, quote and kind')
            _text(req['id'], 'requirement.id', 4000)
            _text(req['quote'], 'requirement.quote')
            if req['id'] in ids or not isinstance(req['kind'], str) or req['kind'] not in KINDS:
                raise ValueError('Duplicate requirement id or unsupported kind')
            ids.add(req['id'])
            if req['quote'] not in record['raw_text']:
                raise ValueError('Extraction quote is absent from its exact raw snapshot')
            cleaned = _clean(req['quote'])
            row = requirements.setdefault(_sha(cleaned), {
                'id': _sha(cleaned), 'text': cleaned, 'sources': [], 'kinds': [],
                'review_status': 'pending_extraction_review'})
            reference = {**source, 'requirement_id': req['id'], 'quote': req['quote'],
                         'kind': req['kind'], 'document_id': digest}
            reference_bytes += len(json.dumps(reference, ensure_ascii=False).encode('utf8'))
            if reference_bytes > MAX_BYTES:
                raise ValueError('Expanded requirement provenance exceeds 20 MB; split this batch')
            row['sources'].append(reference)
            if req['kind'] not in row['kinds']:
                row['kinds'].append(req['kind'])
    for row in requirements.values():
        row['kinds'].sort()
        row['classification_conflict'] = len(row['kinds']) > 1
    return {'raw_records': records, 'documents': list(documents.values()),
            'requirements': list(requirements.values()), 'summary': {
                'schema_version': 'requirements-corpus-v1', 'input_records': len(records),
                'input_bytes': total, 'unique_documents': len(documents),
                'requirement_provenance_bytes': reference_bytes,
                'duplicate_documents': len(records)-len(documents),
                'unique_requirement_candidates': len(requirements),
                'unannotated_records': sum(not r.get('requirements') for r in records),
                'caller_labeled_full_jd_records': sum(r['source_kind']=='full_jd' for r in records),
                'processing_ms': (perf_counter()-started)*1000,
                'model_calls': 0, 'model_tokens': None, 'training_ready': False,
                'extraction_review': 'pending', 'candidate_facts_created': False,
                'training_performed': False, 'upload_performed': False,
                'scope': 'Exact text deduplication only; no semantic or complete-extraction guarantee. '
                         'Source kinds/classifications are caller claims. Raw text may contain private '
                         'identifiers. Cleaning is not anonymization or training approval.'}}


def collect_legacy(database, *, limit=MAX_RECORDS):
    """One fixed read-only jobs projection; no init, migration, facts or approvals."""
    if type(limit) is not int or not 1 <= limit <= MAX_RECORDS:
        raise ValueError('Legacy record limit must be 1..1000')
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError('Select one existing legacy ledger file')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        rows = db.execute('SELECT id,employer,platform,platform_job_id,req_id,title,url,raw_jd,updated_utc '
                          'FROM jobs ORDER BY id LIMIT ?', (limit+1,)).fetchall()
    if len(rows) > limit:
        raise ValueError('Legacy ledger exceeds the selected bound; no records silently omitted')
    return [{'id': 'legacy-job-'+str(r['id']), 'employer': r['employer'],
             'job_key': r['platform']+':'+r['platform_job_id'], 'source_url': r['url'],
             'raw_text': r['raw_jd'], 'source_kind': 'unknown', 'captured_utc': None,
             'source_updated_utc': r['updated_utc']} for r in rows]


def apply_extractions(records, packet):
    """Attach host-selected quote candidates only to their exact raw captures."""
    build_corpus(records)  # Validate identities before matching any annotation.
    if (not isinstance(packet, dict) or set(packet) != {'schema_version', 'records'}
            or packet['schema_version'] != 'requirements-extractions-v1'
            or not isinstance(packet['records'], list)
            or not 1 <= len(packet['records']) <= MAX_RECORDS):
        raise ValueError('Use requirements-extractions-v1 with 1..1000 explicit records')
    if len(json.dumps(packet, ensure_ascii=False, allow_nan=False).encode('utf8')) > MAX_BYTES:
        raise ValueError('Extraction sidecar exceeds 20 MB')
    result = deepcopy(records)
    by_id = {r['id']: r for r in result}
    seen = set()
    for item in packet['records']:
        if not isinstance(item, dict) or set(item) != {'id', 'raw_text_sha256', 'requirements'}:
            raise ValueError('Extraction record requires id, raw_text_sha256 and requirements')
        _text(item['id'], 'extraction.id', 4000)
        if item['id'] in seen or item['id'] not in by_id:
            raise ValueError('Duplicate or unknown extraction snapshot id')
        seen.add(item['id'])
        record = by_id[item['id']]
        if item['raw_text_sha256'] != _sha(record['raw_text']):
            raise ValueError('Extraction is stale: raw snapshot hash differs')
        if record.get('requirements'):
            raise ValueError('Do not replace existing extractions; use a new explicit snapshot')
        if not isinstance(item['requirements'], list) or not item['requirements']:
            raise ValueError('Select explicit nonempty quote candidates')
        record['requirements'] = deepcopy(item['requirements'])
    build_corpus(result)  # Exact quote and kind validation; no source-kind promotion.
    return result


def write_corpus(corpus, output):
    """Exclusive private run; manifest is the completion marker, never overwritten."""
    target = Path(output).resolve()
    if target == REPO or target.is_relative_to(REPO):
        raise ValueError('Corpus output must be outside the public checkout')
    # Serialize before any directory/file write; invalid content produces no export.
    contents = {name: ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False)+'\n' for r in rows)
                for name, rows in [('raw_snapshots.jsonl', corpus['raw_records']),
                                   ('documents.jsonl', corpus['documents']),
                                   ('requirement_candidates.jsonl', corpus['requirements'])]}
    manifest = {**corpus['summary'], 'created_utc': datetime.now(timezone.utc).isoformat(),
                'files': {name: _sha(text) for name, text in contents.items()}}
    manifest_text = json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2)+'\n'
    target.mkdir(parents=True, exist_ok=False)
    for name, text in contents.items():
        with (target/name).open('x', encoding='utf8', newline='') as stream:
            stream.write(text)
    with (target/'manifest.json').open('x', encoding='utf8', newline='') as stream:
        stream.write(manifest_text)
    return manifest
