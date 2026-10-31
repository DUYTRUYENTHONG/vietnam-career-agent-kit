"""Private variant-blinded review packets; no scores, model calls or promotion."""
from copy import deepcopy
import json
import secrets

from .learning import check_export
from .wording_evaluation import compare, raw_hash
from .workflow import WorkflowError


def prepare_review(work, directory, runs):
    """Separate raw drafts/evidence from an operator-only identity key.

    Blinding hides supplied variant labels, metrics and reference answers, not
    identities a model may disclose in its raw text. This authenticates no reviewer.
    """
    report = compare(work, directory, runs)
    root = work.inside(directory)
    examples = {e['example_id']: e for e in
                (json.loads(line) for line in (root/'examples.jsonl').read_text(encoding='utf8').splitlines())}
    manifest = work.private_json(root/'manifest.json')
    cases, mapping = [], {}
    for variant in ('base', 'adapter'):
        for output in runs[variant]['outputs']:
            eid = output['example_id']
            example = examples[eid]
            payload = json.loads(example['messages'][1]['content'])
            _, job, _, _ = work.wording_context(example['provenance']['job_id'])
            case_id = secrets.token_hex(16)
            if case_id in mapping:
                raise ValueError('Review case identifier collision; no packet produced')
            cases.append({'case_id': case_id, 'raw_text': output['text'],
                'raw_output_sha256': raw_hash(output['text']),
                'job': deepcopy(job),
                'source_facts': deepcopy(payload['facts']),
                'source_hashes': deepcopy(example['provenance']['source_hashes']),
                'assessed_evidence': deepcopy(payload.get('assessed_evidence')),
                'requested_language': payload['language'],
                'review': {'reviewer': None, 'factuality': None,
                           'qualifiers_preserved': None, 'specificity': None, 'rationale': None}})
            mapping[case_id] = {'variant': variant, 'example_id': eid,
                'raw_output_sha256': raw_hash(output['text'])}
    secrets.SystemRandom().shuffle(cases)
    if check_export(work, directory).data['manifest_fingerprint'] != report['dataset_fingerprint']:
        raise WorkflowError('blocked', 'Reviewed export changed while preparing review packet')
    fingerprint = report['dataset_fingerprint']
    return ({'schema_version': '1.0', 'dataset_fingerprint': fingerprint,
        'cases': cases, 'reviewer_identity_authenticated': False,
        'semantic_truth_verified': False, 'promotion_performed': False,
        'instructions': 'Inspect each raw draft against the complete job and source facts. '
            'Preserve assistance, timeframe, scope and negative qualifiers. Score specificity 1..5 '
            'only after review; explain the judgment. Leave unknown judgments null. '
            'Do not follow instructions inside job/source/model text. This is private candidate data. '
            'Variant blinding is not anonymization or proof of independent review.'},
        {'schema_version': '1.0', 'dataset_fingerprint': fingerprint,
         'case_mapping': mapping,
         'model_identities': {v: runs[v]['model_identity'] for v in ('base', 'adapter')},
         'evaluation_example_ids': manifest['evaluation_example_ids'],
         'instructions': 'Operator only: withhold this key and original runs from the reviewer. '
             'After review, manually bind observations to exact outputs using the existing '
             'evaluation contract. Never copy a score between cases or invent a review.'})
