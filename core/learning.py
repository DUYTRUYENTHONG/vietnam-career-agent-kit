"""Private reviewed-wording datasets. Never trains, approves or uploads anything."""
import hashlib
import json
import math

from .contracts import ContractError, Outcome
from .ledger import canonical_hash, utc_now
from .workflow import WorkflowError
from .career_memory import current_workspace

SYSTEM = ('Propose source-bound CV wording as JSON language/sections. Use only the supplied '
          'confirmed facts; job requirements are not candidate evidence. Preserve qualifiers, '
          'numbers and source mappings. Output pending statements, never an approval or invented fact.')
FILES = {'examples.jsonl', 'train.jsonl', 'evaluation.jsonl'}


def _example(work, job_id):
    current_workspace(work)
    if type(job_id) is not int or job_id < 1:
        raise ContractError('Use positive explicit local job IDs')
    draft = work.current_draft(job_id)
    # Reuses exact independent factual/editorial review, not a second approval path.
    reviewed = work.reviewed_wording_content(job_id, draft)
    packet = work.wording_packet(job_id).data
    if reviewed['wording_fingerprint'] != packet['fingerprint']:
        raise WorkflowError('blocked', 'Wording changed while preparing the dataset')
    model = packet['model']
    inputs = {'language': model['language'], 'role': packet['job']['title'],
        'requirements': packet['requirements'],
        'facts': [{key: fact[key] for key in ('id', 'field', 'quote', 'source_id', 'locator')}
                  for fact in packet['facts']]}
    target = {'language': model['language'], 'sections': model['sections']}
    provenance = {key: reviewed[key] for key in ('profile_fingerprint', 'job_fingerprint',
        'draft_fingerprint', 'wording_fingerprint', 'review_hash')}
    provenance.update(job_id=job_id, source_hashes={s['id']: s['sha256'] for s in packet['source_records']})
    example_id = canonical_hash(provenance)
    job = work.get_job(job_id)
    group_id = canonical_hash({'employer': job['employer_key'],
        'requisition': job['req_id'] or (job['platform']+':'+job['platform_job_id'])})
    messages = [{'role': 'system', 'content': SYSTEM},
        {'role': 'user', 'content': json.dumps(inputs, ensure_ascii=False, sort_keys=True)},
        {'role': 'assistant', 'content': json.dumps(target, ensure_ascii=False, sort_keys=True)}]
    return {'schema_version': '1.0', 'example_id': example_id, 'kind': 'reviewed_cv_wording',
            'group_id': group_id, 'output_hash': canonical_hash(target),
            'provenance': provenance, 'messages': messages}


def _split(examples):
    # Same job/revision OR exact output duplicates stay together (including transitive overlaps).
    components = [{i} for i in range(len(examples))]
    for i, left in enumerate(examples):
        for j, right in enumerate(examples[:i]):
            if left['group_id'] == right['group_id'] or left['output_hash'] == right['output_hash']:
                a = next(c for c in components if i in c)
                b = next(c for c in components if j in c)
                if a is not b:
                    a.update(b); components.remove(b)
    components.sort(key=lambda c: min(examples[i]['example_id'] for i in c))
    if len(components) < 2:
        return [], [], len(components)
    count = min(len(components)-1, max(1, math.ceil(len(components)*.2)))
    evaluation = set().union(*components[:count])
    return ([e for i, e in enumerate(examples) if i not in evaluation],
            [e for i, e in enumerate(examples) if i in evaluation], len(components))


def _directory(work, value):
    if not isinstance(value, str) or not value.strip():
        raise ContractError('Select a new private datasets/ directory')
    path = work.inside(value)
    root = work.inside('datasets')
    if path == root or not path.is_relative_to(root):
        raise WorkflowError('blocked', 'Dataset exports must be inside a new datasets/ subdirectory')
    return path


def export_reviewed(work, job_ids: list[int], output: str) -> Outcome:
    if (not isinstance(job_ids, list) or not 1 <= len(job_ids) <= 100 or
            any(type(v) is not int or v < 1 for v in job_ids) or len(set(job_ids)) != len(job_ids)):
        raise ContractError('Select 1..100 distinct positive local job IDs')
    target = _directory(work, output)
    if target.exists():
        raise WorkflowError('needs_input', 'Dataset path already exists; inspect it or select a new name, never overwrite it')
    examples = [_example(work, job_id) for job_id in sorted(job_ids)]
    if len({e['provenance']['profile_fingerprint'] for e in examples}) != 1:
        raise WorkflowError('blocked', 'Profile changed during export; do not mix candidates or revisions')
    train, evaluation, groups = _split(examples)
    contents = {'examples.jsonl': ''.join(json.dumps(e, ensure_ascii=False, sort_keys=True)+'\n' for e in examples)}
    if train:
        for name, rows in [('train.jsonl', train), ('evaluation.jsonl', evaluation)]:
            contents[name] = ''.join(json.dumps({'messages': row['messages']}, ensure_ascii=False, sort_keys=True)+'\n' for row in rows)
    if sum(len(v.encode('utf8')) for v in contents.values()) > 20_000_000:
        raise WorkflowError('needs_input', 'Dataset exceeds this 20 MB bounded exporter; select fewer examples')
    # Revalidate current evidence/review after constructing all examples, before any output write.
    for example in examples:
        if _example(work, example['provenance']['job_id'])['example_id'] != example['example_id']:
            raise WorkflowError('blocked', 'Evidence or review changed during export')
    target.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, content in contents.items():
        with (target/name).open('x', encoding='utf8', newline='') as stream:
            stream.write(content)
        hashes[name] = hashlib.sha256((target/name).read_bytes()).hexdigest()
    manifest = {'schema_version': '1.0', 'created_utc': utc_now(),
        'profile_fingerprint': examples[0]['provenance']['profile_fingerprint'],
        'references': [e['provenance'] for e in examples], 'files': hashes,
        'example_count': len(examples), 'independent_group_count': groups,
        'ready_for_split': bool(train),
        'training_example_ids': [e['example_id'] for e in train],
        'evaluation_example_ids': [e['example_id'] for e in evaluation],
        'split_method': 'Deterministic approximately 20% held-out groups; same-job/revision and exact-output duplicates co-grouped.',
        'training_performed': False, 'provider_calls': 0,
        'scope': 'Only current independently reviewed CV wording. Identity/contact header fields omitted, '
                 'but source facts may identify a person: keep this private. No human/provider identity authentication, '
                 'semantic-duplicate guarantee, cross-candidate generalization or production/training readiness claim. '
                 'Email context is not an independently reviewed email training example.'}
    manifest['manifest_fingerprint'] = canonical_hash(manifest)
    # Manifest is the completion marker. Interrupted directories remain incomplete and are never overwritten.
    with (target/'manifest.json').open('x', encoding='utf8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    return Outcome('ok', {'directory': str(target.relative_to(work.data_dir)),
        'manifest_fingerprint': manifest['manifest_fingerprint'], 'example_count': len(examples),
        'ready_for_split': bool(train), 'training_performed': False, 'provider_calls': 0},
        [] if train else ['Collected reviewed examples, but fewer than two independent groups: no training/evaluation split was produced.'])


def check_export(work, directory: str) -> Outcome:
    target = _directory(work, directory)
    manifest = work.private_json(target/'manifest.json')
    fingerprint = manifest.get('manifest_fingerprint')
    if manifest.get('schema_version') != '1.0' or canonical_hash({k: v for k, v in manifest.items() if k != 'manifest_fingerprint'}) != fingerprint:
        raise WorkflowError('blocked', 'Unsupported or changed dataset manifest')
    files = manifest.get('files')
    if not isinstance(files, dict) or set(files) not in ({'examples.jsonl'}, FILES):
        raise WorkflowError('blocked', 'Dataset file list differs from this exporter contract')
    verified = {}
    for name, expected in files.items():
        raw_path = target/name
        path = work.inside(str(raw_path.relative_to(work.data_dir)))
        if raw_path.is_symlink() or not path.is_relative_to(target) or not path.is_file():
            raise WorkflowError('blocked', 'Dataset bytes are missing or changed')
        with path.open('rb') as stream:
            content = stream.read(20_000_001)
        if len(content) > 20_000_000 or hashlib.sha256(content).hexdigest() != expected:
            raise WorkflowError('blocked', 'Dataset bytes are missing or changed')
        verified[name] = content
    if work.confirmed_profile()['fingerprint'] != manifest['profile_fingerprint']:
        raise WorkflowError('blocked', 'Dataset profile is stale; prepare a newly reviewed export')
    references = manifest.get('references')
    if not isinstance(references, list) or not 1 <= len(references) <= 100:
        raise WorkflowError('blocked', 'Dataset has no bounded review references')
    examples = []
    seen = set()
    for reference in references:
        example = _example(work, reference['job_id'])
        if example['provenance'] != reference or example['example_id'] in seen:
            raise WorkflowError('blocked', 'Dataset wording, job, evidence or review is stale')
        examples.append(example); seen.add(example['example_id'])
    train, evaluation, groups = _split(examples)
    expected_files = {'examples.jsonl': examples}
    if train:
        expected_files.update({'train.jsonl': [{'messages': e['messages']} for e in train],
                               'evaluation.jsonl': [{'messages': e['messages']} for e in evaluation]})
    if set(files) != set(expected_files):
        raise WorkflowError('blocked', 'Dataset split file set does not match the reviewed examples')
    for name, expected_rows in expected_files.items():
        rows = [json.loads(line) for line in verified[name].decode('utf8').splitlines()]
        if rows != expected_rows:
            raise WorkflowError('blocked', 'Dataset rows no longer represent the exact reviewed examples')
    if (type(manifest.get('example_count')) is not int or type(manifest.get('independent_group_count')) is not int or
            type(manifest.get('provider_calls')) is not int or
            manifest.get('example_count') != len(examples) or manifest.get('independent_group_count') != groups or
            manifest.get('ready_for_split') is not bool(train) or manifest.get('training_performed') is not False or
            manifest.get('provider_calls') != 0 or
            manifest.get('training_example_ids') != [e['example_id'] for e in train] or
            manifest.get('evaluation_example_ids') != [e['example_id'] for e in evaluation]):
        raise WorkflowError('blocked', 'Dataset counts or split assignments changed')
    return Outcome('ok', {'manifest_fingerprint': fingerprint, 'example_count': manifest['example_count'],
        'ready_for_split': manifest['ready_for_split'], 'current_evidence_checked': True,
        'training_performed': False, 'provider_calls': 0}, [])
