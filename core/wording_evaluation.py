"""Offline paired held-out wording evaluation; no training, import or promotion."""
import hashlib
import json
import math

from .contracts import object_fields, text
from .learning import check_export
from .ledger import canonical_hash
from .tailoring import validate
from .workflow import WorkflowError


def raw_hash(value):
    return hashlib.sha256(value.encode('utf8')).hexdigest()


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = item
        return result
    def nonfinite(_):
        raise ValueError('Nonfinite JSON number')
    return json.loads(value, object_pairs_hook=pairs, parse_constant=nonfinite)


def compare(work, directory, runs):
    """Validate recorded base/adapter outputs against CURRENT reviewed held-out JDs.

    Semantic scores are optional caller-provided independent-review observations,
    not automated entailment or authenticated human reviews. Input/output records
    are private; this function changes no drafts, reviews, facts or ledger rows.
    """
    checked = check_export(work, directory).data
    if not checked['ready_for_split']:
        raise ValueError('A reviewed held-out split is required')
    root = work.inside(directory)
    manifest = work.private_json(root/'manifest.json')
    examples = [json.loads(line) for line in (root/'examples.jsonl').read_text(encoding='utf8').splitlines()]
    heldout = {e['example_id']: e for e in examples if e['example_id'] in manifest['evaluation_example_ids']}
    object_fields(runs, {'base', 'adapter'}, set(), 'paired runs')
    summaries = {}
    for variant in ('base', 'adapter'):
        run = object_fields(runs[variant], {'model_identity', 'dataset_fingerprint', 'outputs'}, set(), variant)
        text(run['model_identity'], 'explicit model revision and adapter identity')
        if run['dataset_fingerprint'] != checked['manifest_fingerprint']:
            raise ValueError('Run dataset fingerprint differs from current reviewed export')
        outputs = run['outputs']
        if not isinstance(outputs, list) or len(outputs) != len(heldout):
            raise ValueError('Every held-out example must appear exactly once in each run')
        results, seen = [], set()
        for output in outputs:
            object_fields(output, {'example_id', 'text'}, {'review', 'metrics'}, 'recorded output')
            eid = output['example_id']
            if not isinstance(eid, str) or eid not in heldout or eid in seen:
                raise ValueError('Duplicate, training or unknown example ID in evaluation')
            seen.add(eid)
            raw = output['text']
            if not isinstance(raw, str) or len(raw.encode('utf8')) > 200_000:
                raise ValueError('Output must be bounded UTF-8 text')
            example = heldout[eid]
            row = {'example_id': eid, 'raw_output_sha256': raw_hash(raw),
                   'contract_valid': False, 'reference_exact_match': False,
                   'review': None, 'metrics': output.get('metrics'), 'issues': []}
            try:
                candidate = strict_json(raw)
                object_fields(candidate, {'language', 'sections'}, set(), 'generated wording')
                job_id = example['provenance']['job_id']
                profile, job, _, assessment = work.wording_context(job_id)
                model = {**candidate, 'schema_version': '2.0', 'candidate_id': profile['profile']['candidate_id'],
                    'job_id': job_id, 'author': 'recorded-generator', 'prompt_version': 'heldout-evaluation-1',
                    'model_configuration': run['model_identity']}
                validate(model, profile['profile'], job, assessment)
                row['contract_valid'] = True
                row['reference_exact_match'] = canonical_hash(candidate) == example['output_hash']
            except (ValueError, TypeError, KeyError, WorkflowError) as error:
                row['issues'].append(str(error))
            metrics = row['metrics']
            if metrics is not None:
                object_fields(metrics, {'input_tokens', 'output_tokens', 'generation_ms', 'load_time_included'}, set(), 'observed metrics')
                for key in ('input_tokens', 'output_tokens', 'generation_ms'):
                    value = metrics[key]
                    valid = (type(value) is int if key != 'generation_ms' else type(value) in (int, float))
                    if value is not None and (not valid or value < 0 or not math.isfinite(value)):
                        raise ValueError('Metrics must be finite nonnegative observations or null')
                if type(metrics['load_time_included']) is not bool:
                    raise ValueError('State whether generation timing includes loading')
            review = output.get('review')
            if review is not None:
                object_fields(review, {'example_id', 'dataset_fingerprint', 'raw_output_sha256', 'reviewer', 'factuality', 'qualifiers_preserved',
                                      'specificity', 'rationale'}, set(), 'independent review')
                for key in ('reviewer', 'rationale'):
                    text(review[key], key)
                if (review['raw_output_sha256'] != row['raw_output_sha256'] or
                        review['example_id'] != eid or review['dataset_fingerprint'] != checked['manifest_fingerprint']):
                    raise ValueError('Review does not bind the exact output, held-out example and dataset')
                if (type(review['factuality']) is not bool or type(review['qualifiers_preserved']) is not bool or
                        type(review['specificity']) is not int or not 1 <= review['specificity'] <= 5):
                    raise ValueError('Use explicit review booleans and a specificity score 1..5')
                row['review'] = dict(review)
            results.append(row)
        n = len(results)
        reviewed = [r for r in results if r['review'] is not None]
        summaries[variant] = {'model_identity': run['model_identity'], 'examples': results,
            'contract_valid_rate': sum(r['contract_valid'] for r in results)/n,
            'reference_exact_match_rate': sum(r['reference_exact_match'] for r in results)/n,
            'review_record_count': len(reviewed),
            'caller_reported_factuality_rate': sum(r['review']['factuality'] for r in reviewed)/n if len(reviewed) == n else None,
            'caller_reported_qualifier_rate': sum(r['review']['qualifiers_preserved'] for r in reviewed)/n if len(reviewed) == n else None,
            'caller_reported_specificity_mean': sum(r['review']['specificity'] for r in reviewed)/n if len(reviewed) == n else None}
    # Prevent an evaluation result from blessing evidence that changed mid-run.
    if check_export(work, directory).data != checked:
        raise WorkflowError('blocked', 'Reviewed export changed during evaluation')
    deltas = {}
    for key in ('contract_valid_rate', 'caller_reported_factuality_rate',
                'caller_reported_qualifier_rate', 'caller_reported_specificity_mean'):
        base, adapter = summaries['base'][key], summaries['adapter'][key]
        deltas[key] = None if base is None or adapter is None else adapter-base
    return {'dataset_fingerprint': checked['manifest_fingerprint'], 'heldout_examples': len(heldout),
        'adapter_minus_base': deltas,
        'runs': summaries, 'reviewer_identity_authenticated': False, 'semantic_truth_verified': False,
        'promotion_performed': False, 'authority_granted': False, 'provider_calls': 0, 'sent': False,
        'limitations': 'Recorded model identities/metrics/reviews are caller supplied. Exact match and linkage checks are not semantic truth. Held-out job/output grouping does not guarantee semantic independence or generalization.'}
