"""Compare captured editorial reviews; never create labels, train or approve."""
import hashlib
import json
from pathlib import Path
import re
from copy import deepcopy

from .contracts import ContractError, object_fields, strings, text
from .learning import REVIEW_SYSTEM
from .ledger import canonical_hash
from .tailoring import DIMENSIONS

LIMITS = {'bytes': 20_000_000, 'rows': 100}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def decode(raw):
    """Reject duplicate keys and non-finite JSON numbers, including nested ones."""
    def invalid(value):
        raise ContractError('Non-finite JSON value: ' + value)
    try:
        return json.loads(raw, object_pairs_hook=_object, parse_constant=invalid)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ContractError('Invalid review JSON: ' + str(exc)) from exc


def _digest(value, label):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ContractError(label + ': expected lowercase SHA256')


def _statement_ids(inputs):
    sections = inputs['cv_sections']
    if not isinstance(sections, list) or not sections:
        raise ContractError('Expected nonempty CV sections')
    ids = []
    for section in sections:
        for group in section['groups']:
            for statement in group['statements']:
                text(statement['id'], 'statement ID')
                ids.append(statement['id'])
    if not ids or len(ids) != len(set(ids)):
        raise ContractError('Expected distinct, nonempty CV statement IDs')
    return set(ids)


def _editorial(value, ids):
    object_fields(value, DIMENSIONS, set(), 'editorial')
    for name in sorted(DIMENSIONS):
        dimension = value[name]
        object_fields(dimension, {'score', 'statement_ids', 'rationale'}, set(), name)
        if type(dimension['score']) is not int or not 0 <= dimension['score'] <= 3:
            raise ContractError('Scores must be integers 0..3, never probabilities')
        cited = strings(dimension['statement_ids'], 'cited statement IDs')
        if not cited or not set(cited) <= ids:
            raise ContractError('Every grade must cite statements in its exact CV')
        text(dimension['rationale'], 'grade rationale')
    return value


def validate_example(row):
    """Validate an archived cv-review-json-1 record, not its current authority."""
    object_fields(row, {'schema_version', 'example_id', 'kind', 'group_id',
        'output_hash', 'provenance', 'messages'}, set(), 'review example')
    if row['schema_version'] != '1.0' or row['kind'] != 'recorded_cv_review':
        raise ContractError('Only captured recorded_cv_review examples are supported')
    provenance = row['provenance']
    for key in ('profile_fingerprint', 'job_fingerprint', 'draft_fingerprint',
                'wording_fingerprint', 'review_hash', 'review_rubric_sha256'):
        _digest(provenance[key], key)
    if type(provenance['job_id']) is not int or provenance['job_id'] < 1:
        raise ContractError('Expected positive local job ID')
    text(provenance['reviewer_claim'], 'reviewer claim')
    _digest(row['group_id'], 'group ID')
    if row['example_id'] != canonical_hash(provenance):
        raise ContractError('Review example identity changed')
    messages = row['messages']
    if not isinstance(messages, list) or len(messages) != 3:
        raise ContractError('Expected system/user/recorded-assistant messages')
    for message, role in zip(messages, ('system', 'user', 'assistant')):
        object_fields(message, {'role', 'content'}, set(), 'message')
        if message['role'] != role:
            raise ContractError('Incorrect message order')
        text(message['content'], 'message content')
    if messages[0]['content'] != REVIEW_SYSTEM:
        raise ContractError('Unsupported grading prompt; do not silently relabel reviews')
    inputs, target = decode(messages[1]['content']), decode(messages[2]['content'])
    object_fields(inputs, {'language', 'role', 'requirements', 'facts', 'cv_sections',
        'rubric', 'output_schema', 'dimensions'}, set(), 'review input')
    object_fields(target, {'editorial'}, set(), 'review target')
    if (inputs['language'] not in ('en', 'vi') or
            inputs['dimensions'] != sorted(DIMENSIONS)):
        raise ContractError('Unsupported language or review dimensions')
    text(inputs['role'], 'role'); text(inputs['rubric'], 'rubric')
    if hashlib.sha256(inputs['rubric'].encode('utf8')).hexdigest() != provenance['review_rubric_sha256']:
        raise ContractError('Rubric text differs from its recorded digest')
    if row['output_hash'] != canonical_hash(target):
        raise ContractError('Recorded scores changed')
    _editorial(target['editorial'], _statement_ids(inputs))
    return inputs, target['editorial']


def read_examples(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        raw = stream.read(LIMITS['bytes'] + 1)
    if len(raw) > LIMITS['bytes']:
        raise ContractError('Review file exceeds 20 MB')
    lines = raw.decode('utf8').splitlines()
    if not 1 <= len(lines) <= LIMITS['rows'] or any(not line.strip() for line in lines):
        raise ContractError('Select 1..100 JSONL review examples without blank rows')
    rows = [decode(line) for line in lines]
    seen = set()
    for row in rows:
        validate_example(row)
        if row['example_id'] in seen:
            raise ContractError('Duplicate review example')
        seen.add(row['example_id'])
    return rows, {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


def compare(before, after):
    left, left_scores = validate_example(before)
    right, right_scores = validate_example(after)
    for key in ('job_id', 'profile_fingerprint', 'review_rubric_sha256'):
        if before['provenance'][key] != after['provenance'][key]:
            raise ContractError('Before/after must share job, candidate revision and rubric')
    if before['group_id'] != after['group_id'] or any(
            left[k] != right[k] for k in ('role', 'language', 'requirements')):
        raise ContractError('Compare the same captured job requirements and language')
    evidence_changed = (left['facts'] != right['facts'] or
        before['provenance']['source_hashes'] != after['provenance']['source_hashes'])
    same_cv = left['cv_sections'] == right['cv_sections']
    return {'schema_version': '1.0', 'kind': 'recorded_review_comparison',
        'before_example_id': before['example_id'], 'after_example_id': after['example_id'],
        'group_id': before['group_id'], 'evidence_changed': evidence_changed,
        'same_cv': same_cv, 'same_reviewer_claim': before['provenance']['reviewer_claim'] == after['provenance']['reviewer_claim'],
        'dimensions': {key: {'before': left_scores[key], 'after': right_scores[key],
            'delta': right_scores[key]['score'] - left_scores[key]['score']} for key in sorted(DIMENSIONS)},
        'interpretation': ('Evidence changed; differences cannot be attributed to tailoring alone.' if evidence_changed else
            'CV unchanged; differences concern review judgments, not tailoring.' if same_cv else
            'Descriptive ordinal differences on the same captured evidence; no causal or hiring claim.'),
        'current_evidence_revalidated': False, 'reviewer_identity_authenticated': False,
        'training_performed': False, 'application_authority': False,
        'training_note': 'Archived comparison only. Use current learning-check/learning-export and explicit cv-review trainer; this report is not training data.'}


def evaluate(references, predictions):
    """Full-cohort ordinal errors against recorded judgments, never human-gold claims."""
    if not 1 <= len(references) <= LIMITS['rows']:
        raise ContractError('Select 1..100 reference reviews')
    parsed = {row['example_id']: (row, *validate_example(row)) for row in references}
    if len(parsed) != len(references) or not isinstance(predictions, list):
        raise ContractError('Duplicate references or invalid predictions')
    observed = {}
    for prediction in predictions:
        object_fields(prediction, {'example_id', 'editorial'}, set(), 'prediction')
        key = prediction['example_id']
        if key not in parsed or key in observed:
            raise ContractError('Unknown or duplicate prediction identity')
        observed[key] = prediction['editorial']
    errors = dict.fromkeys(sorted(DIMENSIONS), 0)
    invalid, valid, exact = [], 0, 0
    for key, (_, inputs, target) in parsed.items():
        try:
            prediction = _editorial(observed.get(key), _statement_ids(inputs))
        except (ValueError, TypeError, KeyError):
            invalid.append(key)
            continue
        valid += 1
        exact += int(all(prediction[k]['score'] == target[k]['score'] for k in DIMENSIONS))
        for dimension in DIMENSIONS:
            errors[dimension] += abs(prediction[dimension]['score'] - target[dimension]['score'])
    count = len(references)
    return {'schema_version': '1.0', 'kind': 'recorded_grader_evaluation',
        'reference_count': count, 'valid_count': valid, 'invalid_or_missing_count': len(invalid),
        'invalid_or_missing_example_ids': invalid, 'full_cohort_exact_score_vector_rate': exact / count,
        'valid_only_mae': {k: v / valid if valid else None for k, v in errors.items()},
        'full_cohort_penalized_mae': {k: (v + 3 * len(invalid)) / count for k, v in errors.items()},
        'penalty': 'Every invalid/missing whole review receives maximum 3-point error in all six dimensions; valid-only MAE is separate.',
        'reference_kind': 'Recorded editorial judgments, not authenticated human gold or hiring outcomes',
        'independence_verified': False, 'current_evidence_revalidated': False,
        'training_performed': False, 'model_promoted': False}


def judge_inputs(references):
    """Separate judge inference inputs from captured reference assistant targets."""
    evaluate(references, [])  # Validate the complete cohort and duplicate identities.
    requests = [{'example_id': row['example_id'], 'messages': deepcopy(row['messages'][:2])}
                for row in references]
    digest = canonical_hash(requests)
    return {'schema_version': '1.0', 'kind': 'cv_judge_inputs', 'requests': requests,
            'inputs_sha256': digest, 'reference_targets_included': False,
            'grader_template': {'grader_id': None, 'model_id': 'unknown', 'model_revision': 'unknown',
                'inputs_sha256': digest, 'predictions': [{'example_id': row['example_id'],
                    'editorial': {d: {'score': None, 'statement_ids': [], 'rationale': None}
                                  for d in sorted(DIMENSIONS)}} for row in references]},
            'model_calls_performed': 0}


def crosscheck(references, graders, writer_model_id='unknown'):
    """Compare 2..4 captured graders; agreement is not correctness or human gold."""
    packet = judge_inputs(references)
    if not isinstance(graders, list) or not 2 <= len(graders) <= 4:
        raise ContractError('Supply two to four captured grader passes')
    text(writer_model_id, 'declared writer model or unknown')
    parsed = {row['example_id']: validate_example(row) for row in references}
    reports, valid = {}, {}
    identities = []
    for grader in graders:
        object_fields(grader, {'grader_id', 'model_id', 'model_revision', 'inputs_sha256', 'predictions'}, set(), 'grader pass')
        for key in ('grader_id', 'model_id', 'model_revision'):
            text(grader[key], key+' or unknown')
        gid = grader['grader_id']
        if gid in reports or grader['inputs_sha256'] != packet['inputs_sha256']:
            raise ContractError('Duplicate grader ID or changed inference inputs')
        report = evaluate(references, grader['predictions'])
        reports[gid] = dict(report, model_id=grader['model_id'], model_revision=grader['model_revision'])
        identities.append(grader['model_id'])
        valid[gid] = {}
        for prediction in grader['predictions']:
            key = prediction['example_id']
            try:
                valid[gid][key] = _editorial(prediction['editorial'], _statement_ids(parsed[key][0]))
            except (ValueError, TypeError, KeyError):
                pass  # Invalid cases remain in evaluate()'s full-cohort penalties.
    pairs = []; gids = list(reports)
    for i, left in enumerate(gids):
        for right in gids[i+1:]:
            shared = sorted(set(valid[left]) & set(valid[right]))
            exact = sum(all(valid[left][key][d]['score'] == valid[right][key][d]['score']
                            for d in DIMENSIONS) for key in shared)
            error = sum(abs(valid[left][key][d]['score']-valid[right][key][d]['score'])
                        for key in shared for d in DIMENSIONS)
            pairs.append({'graders': [left, right], 'paired_valid_cases': len(shared),
                'unresolved_cases': len(references)-len(shared),
                'full_cohort_exact_score_vector_rate': exact/len(references),
                'valid_pair_mean_absolute_difference': error/(len(shared)*len(DIMENSIONS)) if shared else None})
    triage = []
    for key in parsed:
        present = [valid[gid][key] for gid in gids if key in valid[gid]]
        missing = [gid for gid in gids if key not in valid[gid]]
        gaps = {d: max(p[d]['score'] for p in present)-min(p[d]['score'] for p in present)
                for d in DIMENSIONS} if len(present) >= 2 else None
        if missing or gaps is None or any(gaps.values()):
            triage.append({'example_id': key, 'invalid_or_missing_graders': missing,
                'score_spreads': gaps, 'human_adjudication_required': True})
    declared_ids = {value.strip().casefold() for value in identities}
    writer_id = writer_model_id.strip().casefold()
    return {'schema_version': '1.0', 'kind': 'cv_grader_crosscheck', 'inputs_sha256': packet['inputs_sha256'],
        'reference_count': len(references), 'graders': reports, 'pairs': pairs, 'triage': triage,
        'distinct_model_ids_declared': 'unknown' not in declared_ids and len(declared_ids) > 1,
        'same_writer_model_declared': writer_id != 'unknown' and writer_id in declared_ids,
        'writer_model_id': writer_model_id, 'model_identity_verified': False,
        'current_evidence_revalidated': False,
        'independence_verified': False, 'human_gold_created': False,
        'reference_kind': 'Recorded editorial judgments, not authenticated human gold or hiring outcomes',
        'human_review_required': True, 'training_export': False, 'model_promoted': False,
        'application_authority': False}
