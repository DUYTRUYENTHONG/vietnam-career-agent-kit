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


def _observed_metrics_summary(results):
    """Summarize already-validated rows, including structurally invalid outputs.

    Complete totals are separate from coverage; unknown is never inferred as zero.
    Loading-inclusive/mixed timing is not generation-only throughput.
    """
    n = len(results)
    summary = {'examples': n}
    for key in ('input_tokens', 'output_tokens', 'generation_ms'):
        values = [r['metrics'][key] for r in results
                  if r['metrics'] is not None and r['metrics'][key] is not None]
        summary[key+'_observed_examples'] = len(values)
        total = None
        if n and len(values) == n:
            try:
                total = math.fsum(values) if key == 'generation_ms' else sum(values)
                if not math.isfinite(total):
                    raise ValueError('Metric totals must remain finite')
            except OverflowError as error:
                raise ValueError('Metric totals must remain finite') from error
        summary[key+'_total'] = total
    flags = {r['metrics']['load_time_included'] for r in results
             if r['metrics'] is not None and r['metrics']['generation_ms'] is not None}
    scope = ('incomplete' if summary['generation_ms_total'] is None else
             'mixed' if len(flags) != 1 else
             'includes_model_loading' if True in flags else 'generation_only')
    summary['timing_scope'] = scope
    rate = None
    if (scope == 'generation_only' and summary['output_tokens_total'] is not None
            and summary['generation_ms_total'] > 0):
        try:
            rate = (summary['output_tokens_total']/summary['generation_ms_total'])*1000.0
            if not math.isfinite(rate):
                raise ValueError('Derived token throughput must remain finite')
        except OverflowError as error:
            raise ValueError('Derived token throughput must remain finite') from error
    summary['generation_output_tokens_per_second'] = rate
    return summary


def _candidate_sections(candidate, example, task):
    """Adapt an explicitly selected bullet to the canonical v2 validator."""
    if task == 'cv-wording':
        object_fields(candidate, {'language', 'sections'}, set(), 'generated wording')
        return candidate
    object_fields(candidate, {'language', 'section_kind', 'context_fact_id', 'statement'}, set(), 'generated bullet')
    inputs = strict_json(example['messages'][1]['content'])
    statement = candidate['statement']
    if not isinstance(statement, dict):
        raise ValueError('Generated bullet statement must be an object')
    if (any(candidate[key] != inputs[key] for key in ('language', 'section_kind', 'context_fact_id')) or
            statement.get('id') != inputs['statement_id'] or
            statement.get('source_fact_ids') != [inputs['statement_fact_id']] or
            statement.get('requirement_ids') != [r['id'] for r in inputs['requirements']]):
        raise ValueError('Generated bullet differs from its selected language, placement, statement, fact or requirements')
    return {'language': candidate['language'], 'sections': [{'kind': candidate['section_kind'],
        'groups': [{'context_fact_id': candidate['context_fact_id'], 'statements': [statement]}]}]}


def compare(work, directory, runs, *, task='cv-wording'):
    """Validate recorded base/adapter outputs against CURRENT reviewed held-out JDs.

    Semantic scores are optional caller-provided independent-review observations,
    not automated entailment or authenticated human reviews. Input/output records
    are private; this function changes no drafts, reviews, facts or ledger rows.
    """
    checked = check_export(work, directory).data
    manifest = work.private_json(work.inside(directory)/'manifest.json')
    if task not in ('cv-wording', 'cv-bullet-wording'):
        raise ValueError('Select cv-wording or cv-bullet-wording explicitly')
    if manifest.get('task', 'cv-wording') != task:
        raise ValueError('Dataset task mismatch; full-CV wording is the default, bullet wording needs explicit selection')
    if not checked['ready_for_split']:
        raise ValueError('A reviewed held-out split is required')
    root = work.inside(directory)
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
                validated_candidate = _candidate_sections(candidate, example, task)
                job_id = example['provenance']['job_id']
                profile, job, _, assessment = work.wording_context(job_id)
                model = {**validated_candidate, 'schema_version': '2.0', 'candidate_id': profile['profile']['candidate_id'],
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
                    try:
                        invalid = value is not None and (not valid or value < 0 or not math.isfinite(value))
                    except OverflowError:
                        invalid = True
                    if invalid:
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
            'observed_metrics_summary': _observed_metrics_summary(results),
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
    return {'task': task, 'dataset_fingerprint': checked['manifest_fingerprint'], 'heldout_examples': len(heldout),
        'adapter_minus_base': deltas,
        'runs': summaries, 'reviewer_identity_authenticated': False, 'semantic_truth_verified': False,
        'promotion_performed': False, 'authority_granted': False, 'provider_calls': 0, 'sent': False,
        'limitations': 'Recorded model identities/metrics/reviews are caller supplied. Exact match and linkage checks are not semantic truth. Held-out job/output grouping does not guarantee semantic independence or generalization.'}
