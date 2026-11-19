"""Offline evidence retrieval and reviewed CV planning. Scores are not entailment."""
from collections import Counter
from copy import deepcopy
import json
import math
import re
import unicodedata
from pathlib import Path

from . import tailor_benchmark as b


METHODS = ('bm25-v1', 'bm25-v2')
STOPWORDS = set('a an the of to in or and with for on as at is be from by using years experience understanding basic solid related field'.split())


def implementation_hash():
    return b.digest(Path(__file__).read_bytes())


def tokens(value, method='bm25-v2'):
    normalized = unicodedata.normalize('NFC', value).casefold()
    if method == 'bm25-v2':
        for phrase, alias in [('machine learning', 'ml'), ('deep learning', 'dl'),
                              ('natural language processing', 'nlp')]:
            normalized = re.sub(r'\b'+phrase+r'\b', alias, normalized)
    words = re.findall(r'[\w+#]+', normalized)
    if method == 'bm25-v1':
        return words
    aliases = {'apis': 'api', 'tests': 'test', 'testing': 'test'}
    return [aliases.get(word, word) for word in words if word not in STOPWORDS]


def retrieve(case, limit=5, method='bm25-v2'):
    """BM25 over exact evidence, with stable ties; zero-overlap facts are excluded."""
    b.require(type(limit) is int and 1 <= limit <= 20, 'Retrieval limit must be 1..20')
    b.require(method in METHODS, 'Unknown frozen retrieval method')
    bags = {f['id']: Counter(tokens(f['text'], method)) for f in case['facts']}
    average = sum(sum(v.values()) for v in bags.values())/max(1, len(bags)) or 1
    scores = dict.fromkeys(bags, 0.0)
    for term in set(tokens(case['requirement']['text'], method)):
        count = sum(term in v for v in bags.values())
        if not count:
            continue
        idf = math.log1p((len(bags)-count+.5)/(count+.5))
        for fid, bag in bags.items():
            tf = bag[term]
            scores[fid] += idf*tf*2.2/(tf+1.2*(.25+.75*sum(bag.values())/average))
    return [{'fact_id': fid, 'retrieval_score': score} for fid, score in
            sorted(scores.items(), key=lambda x: (-x[1], x[0])) if score > 0][:limit]


def prepare(root, cases, output, limit=5, method='bm25-v2'):
    b.validate_cases(root, cases)
    b.require(len({c['profile_group'] for c in cases}) == 1 and
        len({c['source_group'] for c in cases}) == 1 and
        len({c['requirement']['id'] for c in cases}) == len(cases),
        'Prepare one vacancy with distinct requirement IDs; never combine employer groups')
    rows = []
    for case in cases:
        rows.append({'case_id': case['case_id'], 'case_sha256': b.binding(case),
            'requirement_id': case['requirement']['id'], 'candidates': retrieve(case, limit, method),
            'mandatory': None, 'hard': None, 'priority': None, 'status': None,
            'fact_ids': [], 'reviewer_id': None, 'reviewer_type': None,
            'source_checked': False, 'rationale': None})
    return b.bundle(root, output, {'cases.jsonl': b.rows_bytes(cases),
        'matching_review.jsonl': b.rows_bytes(rows)}, {'schema_version': '1.0',
        'kind': 'cv_planning_preparation', 'retrieval': method,
        'retrieval_implementation_sha256': implementation_hash(),
        'top_k': limit, 'coverage_reviewed': False, 'application_authority': False})


def reviewed_matches(cases, rows):
    expected = {c['case_id']: c for c in cases}; matches = {}
    for row in rows:
        b.object_fields(row, {'case_id', 'case_sha256', 'requirement_id', 'candidates',
            'mandatory', 'hard', 'priority', 'status', 'fact_ids', 'reviewer_id',
            'reviewer_type', 'source_checked', 'rationale'}, set(), 'matching review')
        cid = row['case_id']
        b.require(cid in expected and cid not in matches, 'Unknown/duplicate matching case')
        case = expected[cid]
        b.require(row['case_sha256'] == b.binding(case) and
            row['requirement_id'] == case['requirement']['id'], 'Match source changed')
        b.require(row['reviewer_type'] == 'human' and row['source_checked'] is True,
                  'Actual human requirement/evidence review required')
        b.text(row['reviewer_id'], 'reviewer ID'); b.text(row['rationale'], 'match rationale')
        b.require(type(row['mandatory']) is bool and type(row['hard']) is bool and
            (not row['hard'] or row['mandatory']), 'Review explicit mandatory/hard flags')
        b.require(type(row['priority']) is int and 1 <= row['priority'] <= 3,
                  'Review priority 1..3')
        b.require(row['status'] in ('demonstrated', 'partial', 'missing', 'unknown'),
                  'Review coverage status explicitly')
        ids = b.strings(row['fact_ids'], 'reviewed fact IDs')
        b.require(set(ids) <= {f['id'] for f in case['facts']}, 'Unknown matching fact')
        b.require(bool(ids) == (row['status'] in ('demonstrated', 'partial')),
                  'Coverage status and evidence disagree')
        matches[cid] = row
    b.require(set(matches) == set(expected), 'Review every requirement; do not omit gaps')
    return matches


def plan(root, preparation, reviews, output, max_bullets=12):
    b.require(type(max_bullets) is int and 1 <= max_bullets <= 30, 'Bullet budget must be 1..30')
    folder, manifest = b.verify_bundle(root, preparation, 'cv_planning_preparation')
    cases = b.validate_cases(root, b.read_rows(folder/'cases.jsonl'))
    b.require(len({c['source_group'] for c in cases}) == 1 and
        len({c['requirement']['id'] for c in cases}) == len(cases), 'Plan one vacancy with distinct requirements')
    b.require(len({c['profile_group'] for c in cases}) == 1, 'Plan one candidate at a time')
    matches = reviewed_matches(cases, reviews)
    facts = {}
    for case in cases:
        for fact in case['facts']:
            b.require(fact['id'] not in facts or b.binding(facts[fact['id']]) == b.binding(fact),
                      'Fact IDs must have consistent scope and source throughout the plan')
            facts[fact['id']] = fact
    remaining = set(matches); selected = []
    while len(selected) < max_bullets:
        choices = []
        for fid in sorted(facts):
            if fid in selected:
                continue
            covered = [cid for cid in remaining if fid in matches[cid]['fact_ids']]
            weight = sum(matches[cid]['priority']*(4 if matches[cid]['mandatory'] else 1)*
                         (2 if matches[cid]['status'] == 'demonstrated' else 1) for cid in covered)
            choices.append((weight, fid, covered))
        if not choices:
            break
        weight, fid, covered = sorted(choices, key=lambda x: (-x[0], x[1]))[0]
        if weight == 0:
            break
        selected.append(fid); remaining.difference_update(covered)
    matrix = []
    for case in cases:
        row = matches[case['case_id']]
        matrix.append({k: row[k] for k in ('case_id', 'requirement_id', 'mandatory',
            'hard', 'priority', 'status', 'fact_ids', 'rationale')} | {
            'requirement': case['requirement']['text'],
            'selected_fact_ids': [fid for fid in selected if fid in row['fact_ids']],
            'omitted_by_budget': bool(row['fact_ids']) and not set(selected)&set(row['fact_ids'])})
    result = {'schema_version': '1.0', 'kind': 'reviewed_cv_content_plan',
        'preparation_sha256': b.binding(manifest), 'reviews_sha256': b.binding(reviews),
        'max_bullets': max_bullets, 'selection_method': 'reviewed-weighted-coverage-v1',
        'fact_ids_semantics': 'Each reviewed ID is an individually sufficient alternative for its stated coverage status',
        'ordered_evidence': [facts[fid] for fid in selected], 'requirement_matrix': matrix,
        'mandatory_attention': [r['case_id'] for r in matrix if r['mandatory'] and
            (r['status'] != 'demonstrated' or r['omitted_by_budget'])],
        'document_review_required': True, 'reviewer_identity_authenticated': False,
        'training_export': False, 'application_authority': False}
    return b.bundle(root, output, {'plan.json': b.json_bytes(result),
        'matching_review.jsonl': b.rows_bytes(reviews)}, {'schema_version': '1.0',
        'kind': 'cv_content_plan_bundle', 'application_authority': False})


def retrieval_report(root, frozen, limit=5, method='bm25-v2'):
    folder, manifest = b.verify_bundle(root, frozen, 'tailor_benchmark_frozen')
    cases = b.validate_cases(root, b.read_rows(folder/'cases.jsonl'))
    gold = {g['case_id']: g for g in b.read_rows(folder/'gold.jsonl')}
    rows = []
    for case in cases:
        ids = [r['fact_id'] for r in retrieve(case, limit, method)]
        acceptable = set(gold[case['case_id']]['acceptable_fact_ids'])
        rows.append({'case_id': case['case_id'], 'ranked_fact_ids': ids,
            'has_supported_evidence': bool(acceptable),
            'hit': bool(acceptable & set(ids)) if acceptable else None,
            'acceptable_evidence_recall': len(acceptable & set(ids))/len(acceptable) if acceptable else None})
    supported = [r for r in rows if r['has_supported_evidence']]
    return {'kind': 'retrieval_diagnostic', 'cohort_sha256': manifest['cohort_sha256'],
        'top_k': limit, 'retrieval': method, 'retrieval_implementation_sha256': implementation_hash(),
        'cases': len(rows), 'supported_cases': len(supported),
        'hit_rate_at_k': sum(r['hit'] for r in supported)/len(supported) if supported else None,
        'mean_acceptable_evidence_recall_at_k': sum(r['acceptable_evidence_recall'] for r in supported)/len(supported) if supported else None,
        'rows': rows, 'semantic_precision_measured': False,
        'model_run': False, 'application_authority': False}


def retrieval_variant(root, frozen, output, limit=5, method='bm25-v2'):
    """Freeze full-evidence vs top-K with identical system prompts; never read gold to rank."""
    folder, manifest = b.verify_bundle(root, frozen, 'tailor_benchmark_frozen')
    cases = b.validate_cases(root, b.read_rows(folder/'cases.jsonl'))
    inputs = b.read_rows(folder/'generation_inputs.jsonl')
    b.require([r['case_id'] for r in inputs] == [c['case_id'] for c in cases], 'Input order changed')
    for case, row in zip(cases, inputs):
        original = deepcopy(row['conditions']['base_evidence'])
        data = b.decode(original[1]['content'])
        expected = [{k: f[k] for k in ('id', 'text', 'scope', 'qualifiers')} for f in case['facts']]
        b.require(data['facts'] == expected, 'Retrieval comparator must start with all exact facts')
        ranked = {r['fact_id'] for r in retrieve(case, limit, method)}
        candidate = deepcopy(original)
        data['facts'] = [f for f in data['facts'] if f['id'] in ranked]
        candidate[1]['content'] = json.dumps(data, ensure_ascii=False)
        row['conditions'] = {'base_original': original, 'base_evidence': candidate,
                             'adapter_evidence': deepcopy(candidate)}
    files = {name: (folder/name).read_bytes() for name in manifest['files']}
    files['generation_inputs.jsonl'] = b.rows_bytes(inputs)
    metadata = {k: v for k, v in manifest.items() if k != 'files'}
    metadata.update(parent_manifest_sha256=b.binding(manifest), experiment='retrieval', top_k=limit,
        retrieval=method, retrieval_implementation_sha256=implementation_hash())
    return b.bundle(root, output, files, metadata)
