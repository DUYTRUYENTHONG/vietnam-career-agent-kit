"""Opt-in offline paired CPU generation over an existing reviewed CV export.

Uses the provisioned base and its selected training run. Never trains, downloads,
repairs model output, invents reviews, imports wording or promotes a model.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter

from adapters.local_finetuning import model_hashes
from adapters.local_qwen import generate
from core.documents import Documents
from core.learning import check_export
from core.ledger import canonical_hash
from core.wording_evaluation import compare


def _save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def run(work, directory, model_directory, training_directory, output, *,
        max_examples=10, max_new_tokens=512):
    """Generate every held-out example twice; incomplete runs cannot resume.

    Hashes bind local bytes, not training authenticity or semantic correctness.
    Filesystem checks are not an atomic snapshot or a sandbox for model libraries.
    Existing inference is CPU/greedy; each call loads its model independently.
    """
    started = perf_counter()
    if (type(max_examples) is not int or not 1 <= max_examples <= 50 or
            type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 2048):
        raise ValueError('Use 1..50 maximum examples and 1..2048 output tokens')
    target = work.inside(output)
    evaluation_root = work.inside('evaluations')
    if target == evaluation_root or not target.is_relative_to(evaluation_root) or target.exists():
        raise ValueError('Use a new private evaluations/ subdirectory; never overwrite or resume')
    checked = check_export(work, directory).data
    if not checked['ready_for_split']:
        raise ValueError('A current reviewed held-out split is required')
    source = work.inside(directory)
    manifest = work.private_json(source/'manifest.json')
    all_examples = [json.loads(line) for line in (source/'examples.jsonl').read_text(encoding='utf8').splitlines()]
    examples = [row for row in all_examples if row['example_id'] in manifest['evaluation_example_ids']]
    if not 1 <= len(examples) <= max_examples:
        raise ValueError('Held-out example count exceeds explicit cap; no silent subset')
    if ({e['example_id'] for e in examples} != set(manifest['evaluation_example_ids']) or
            len(examples) != len(manifest['evaluation_example_ids'])):
        raise ValueError('Held-out IDs differ from the reviewed manifest')
    prompts = []
    for example in examples:
        messages = example['messages']
        if ([m.get('role') for m in messages] != ['system', 'user', 'assistant'] or
                any(set(m) != {'role', 'content'} or not isinstance(m['content'], str) for m in messages) or
                sum(len(m['content']) for m in messages[:-1]) > 30000):
            raise ValueError('Use bounded reviewed system/user prompts and a separate reference answer')
        prompts.append((example['example_id'], deepcopy(messages[:-1])))
    model = Path(model_directory).resolve(strict=True)
    if not model.is_dir() or not (model/'config.json').is_file():
        raise ValueError('Select an existing local causal-language model')
    base_files = model_hashes(model)
    if not any(name.endswith('.safetensors') for name in base_files):
        raise ValueError('Local safetensors base weights are required')
    training = work.inside(training_directory)
    if training == work.inside('training') or not training.is_relative_to(work.inside('training')):
        raise ValueError('Select an existing private training/ run')
    result_path = work.inside(training/'result.json')
    result = work.private_json(result_path)
    if (result.get('training_performed') is not True or
            result.get('task', 'cv-wording') != 'cv-wording' or
            result.get('dataset_fingerprint') != checked['manifest_fingerprint'] or
            result.get('base_model_files') != base_files):
        raise ValueError('Training task, reviewed export or exact base-model files differ')
    adapter = work.inside(training/'adapter')
    if not (adapter/'adapter_model.safetensors').is_file() or not (adapter/'adapter_config.json').is_file():
        raise ValueError('Select a completed local safetensors adapter')
    for path in adapter.iterdir():
        work.inside(path)  # Reject adapter-file symlinks escaping the private root.
    adapter_files = model_hashes(adapter)
    result_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
    fingerprint = checked['manifest_fingerprint']
    def current():
        if check_export(work, directory).data != checked:
            raise ValueError('Reviewed export changed during generation')
    current()
    provenance = {'schema_version': '1.0', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'dataset_fingerprint': fingerprint, 'dataset_directory': str(source),
        'base_model_files': base_files, 'adapter_files': adapter_files,
        'training_result_sha256': result_hash, 'training_directory': str(training),
        'max_examples': max_examples, 'max_new_tokens': max_new_tokens,
        'device': 'cpu', 'decoding': 'greedy', 'thinking': False,
        'reference_answers_sent_to_model': False,
        'prompts': [{'example_id': eid, 'messages_sha256': canonical_hash(messages)} for eid, messages in prompts],
        'model_loads_per_example': 2, 'provider_calls': 0,
        'independent_review_performed': False, 'promotion_performed': False, 'sent': False}
    target.mkdir(parents=True, exist_ok=False)
    _save(target/'provenance.json', provenance)
    base_identity = 'local-base-files-sha256:'+canonical_hash(base_files)
    runs = {name: {'model_identity': base_identity + (
        '+adapter-files-sha256:'+canonical_hash(adapter_files) if name == 'adapter' else ''),
        'dataset_fingerprint': fingerprint, 'outputs': []} for name in ('base', 'adapter')}
    timings = []
    try:
        for eid, messages in prompts:
            for variant in ('base', 'adapter'):
                current()
                call_started = perf_counter()
                generated = generate(model, deepcopy(messages),
                    adapter_directory=adapter if variant == 'adapter' else None,
                    max_new_tokens=max_new_tokens)
                timings.append({'variant': variant, 'example_id': eid,
                    'call_wall_ms_including_load': (perf_counter()-call_started)*1000})
                if (not isinstance(generated.get('text'), str) or
                        len(generated['text'].encode('utf8')) > 200_000):
                    raise ValueError('Generated text exceeds the existing bounded evaluation contract')
                metrics = {key: generated[key] for key in
                    ('input_tokens', 'output_tokens', 'generation_ms', 'load_time_included')}
                runs[variant]['outputs'].append({'example_id': eid, 'text': generated['text'], 'metrics': metrics})
                # Private crash evidence only; no resume/retry and no completed marker.
                (target/'partial.json').write_text(json.dumps(runs, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
        current()
        if (model_hashes(model) != base_files or model_hashes(adapter) != adapter_files or
                hashlib.sha256(result_path.read_bytes()).hexdigest() != result_hash):
            raise ValueError('Base, adapter or training record changed during generation')
        report = compare(work, directory, runs)
        _save(target/'runs.json', runs)
        _save(target/'comparison.json', report)
        completion = {'schema_version': '1.0', 'heldout_examples': len(prompts),
            'dataset_fingerprint': fingerprint, 'total_wall_ms': (perf_counter()-started)*1000,
            'calls': timings, 'runtime_completed': True, 'semantic_truth_verified': False,
            'independent_review_performed': False, 'promotion_performed': False,
            'authority_granted': False, 'provider_calls': 0, 'sent': False,
            'artifacts_sha256': {name: hashlib.sha256((target/name).read_bytes()).hexdigest()
                for name in ('provenance.json', 'runs.json', 'comparison.json')}}
        _save(target/'completed.json', completion)
        return completion
    except Exception as error:
        _save(target/'failure.json', {'error_type': type(error).__name__, 'error': str(error),
            'completed_calls': timings, 'runtime_completed': False, 'promotion_performed': False, 'sent': False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--model-directory', required=True)
    parser.add_argument('--training-directory', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-examples', type=int, default=10)
    parser.add_argument('--max-new-tokens', type=int, default=512)
    args = parser.parse_args()
    result = run(Documents(args.data_dir), args.dataset, args.model_directory,
                 args.training_directory, args.output, max_examples=args.max_examples,
                 max_new_tokens=args.max_new_tokens)
    print(json.dumps({key: result[key] for key in ('heldout_examples', 'runtime_completed', 'promotion_performed', 'sent')}))


if __name__ == '__main__':
    main()
