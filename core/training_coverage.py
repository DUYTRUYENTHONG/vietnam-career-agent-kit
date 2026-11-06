"""Read-only identity/text coverage for explicit external candidate_fact pilots.

This diagnostic does not validate evidence, labels, eligibility or training consent.
"""
import hashlib
import json
import unicodedata

MAX_ROWS = 10_000


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Fact IDs and text must be nonempty strings')
    return ' '.join(unicodedata.normalize('NFC', value).split())


def _fact(value):
    if not isinstance(value, dict):
        raise ValueError('Expected a fact object')
    fid = value.get('id')
    if _text(fid) != fid or len(fid) > 256:
        raise ValueError('Fact IDs must be normalized strings of at most 256 characters')
    return fid, _text(value.get('text'))


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode('utf8')).hexdigest()


def _rows(rows, aliases):
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError('Rows must be a list of at most 10,000 examples')
    result = {}
    for row in rows:
        messages = row.get('messages') if isinstance(row, dict) else None
        if (not isinstance(messages, list) or len(messages) != 3 or
                any(not isinstance(m, dict) or m.get('role') != role or
                    not isinstance(m.get('content'), str)
                    for m, role in zip(messages, ('system', 'user', 'assistant')))):
            raise ValueError('Expected three ordered system/user/assistant messages')
        try:
            payload = json.loads(messages[1]['content'])
        except (ValueError, RecursionError):
            raise ValueError('User content must be a JSON candidate_fact object') from None
        if not isinstance(payload, dict):
            raise ValueError('User content must be a JSON candidate_fact object')
        fid, text = _fact(payload.get('candidate_fact'))
        result.setdefault(aliases.get(fid, fid), set()).add(text)
    return result


def audit_coverage(expected, training, evaluation=None, aliases=None):
    """Compare explicit IDs, never fuzzy-match text or infer approval from coverage."""
    if not isinstance(expected, list) or not 1 <= len(expected) <= MAX_ROWS:
        raise ValueError('Select 1..10,000 explicit expected facts')
    facts = {}
    for row in expected:
        fid, text = _fact(row)
        if fid in facts:
            raise ValueError('Duplicate expected fact ID')
        facts[fid] = text
    aliases = {} if aliases is None else aliases
    if not isinstance(aliases, dict):
        raise ValueError('Aliases must be an explicit one-to-one object')
    targets = set()
    for source, target in aliases.items():
        if (not isinstance(source, str) or not isinstance(target, str) or
                _text(source) != source or len(source) > 256 or source in facts or
                target not in facts or target in targets):
            raise ValueError('Aliases must map distinct external IDs to distinct expected IDs')
        targets.add(target)
    if not isinstance(training, list) or not training:
        raise ValueError('Select a nonempty training list')
    evaluation = [] if evaluation is None else evaluation
    if not isinstance(evaluation, list) or len(training) + len(evaluation) > MAX_ROWS:
        raise ValueError('Combined example count must not exceed 10,000')
    train = _rows(training, aliases)
    heldout = _rows(evaluation, aliases)
    wanted, train_ids, eval_ids = set(facts), set(train), set(heldout)
    all_ids = train_ids | eval_ids
    variants = {fid: train.get(fid, set()) | heldout.get(fid, set()) for fid in all_ids}
    return {
        'schema_version': '1.0', 'status': 'review_required',
        'expected_fact_count': len(facts), 'training_rows': len(training),
        'evaluation_rows': len(evaluation), 'training_unique_fact_count': len(train),
        'evaluation_unique_fact_count': len(heldout),
        'absent_from_training': sorted(wanted - train_ids),
        'absent_from_both': sorted(wanted - all_ids),
        'evaluation_only': sorted((wanted & eval_ids) - train_ids),
        'unexpected_ids': sorted(all_ids - wanted),
        'text_differences': sorted(fid for fid in wanted & all_ids
                                   if variants[fid] != {facts[fid]}),
        'multiple_text_variants': sorted(fid for fid in all_ids if len(variants[fid]) > 1),
        'train_evaluation_fact_overlap': sorted(train_ids & eval_ids),
        'input_bindings': {'expected_sha256': _digest(expected),
                           'training_sha256': _digest(training),
                           'evaluation_sha256': _digest(evaluation),
                           'aliases_sha256': _digest(aliases)},
        'training_authorized': False, 'training_performed': False, 'provider_calls': 0,
        'scope': 'ID and NFC/whitespace-normalized text coverage only. Text differences need '
                 'semantic review; fact overlap is not proof of employer leakage. No source, '
                 'approval, label-quality, split-independence or model-promotion validation.'}
