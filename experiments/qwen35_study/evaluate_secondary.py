"""Qwen3-4B-Instruct-2507 comparison. Synthetic evaluation, never auto-promoted."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from adapters.qwen35_pairing import checkpoint_binding
from core.evidence_pairing import strict_json
from scripts.evidence_bench import examples, load_cases, metrics
from experiments.qwen35_study.generation import generate_row
from experiments.qwen35_study.runtime import load_secondary

MODEL = 'Qwen/Qwen3-4B-Instruct-2507'
REVISION = 'cdbee75f17c01a7cc42f958dc650907174af0554'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'model-dir', 'budget-file', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--partition', choices=('development', 'test'), default='development')
    parser.add_argument('--acknowledge-exposed-regression', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.partition == 'test' and not args.acknowledge_exposed_regression:
        raise ValueError('Public test is exposed regression; acknowledge that scope')
    selected = examples(load_cases(args.dataset), args.partition)
    if not selected or args.output.exists():
        raise ValueError('Need nonempty partition and fresh output directory')
    binding = checkpoint_binding(args.model_dir)
    config = strict_json((args.model_dir / 'config.json').read_text(encoding='utf8'))
    if (config.get('model_type') != 'qwen3' or config.get('hidden_size') != 2560
            or config.get('num_hidden_layers') != 36):
        raise ValueError('Expected Qwen3-4B-Instruct-2507 architecture')
    if not args.run:
        print(json.dumps({'mode': 'preflight_only', 'rows': len(selected),
                         'inference_started': False, 'model': MODEL}))
        return
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('Free CUDA GPU required; no CPU fallback')
    budget = strict_json(args.budget_file.read_text(encoding='utf8'))
    cap, spent = budget['cap_seconds'], budget['spent_seconds']
    if (type(cap) not in (int, float) or type(spent) not in (int, float)
            or not math.isfinite(cap) or not math.isfinite(spent)
            or not 0 <= spent < cap <= 43200):
        raise ValueError('Invalid or exhausted study budget')
    lock = args.budget_file.with_suffix('.running')
    with lock.open('x', encoding='utf8') as stream:
        stream.write(str(args.output))
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    report = {'scope': 'synthetic development or exposed regression only',
        'model': MODEL, 'requested_revision': REVISION, 'partition': args.partition,
        'checkpoint_binding': binding, 'dataset_sha256': hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        'gpu': torch.cuda.get_device_name(0), 'rows': [], 'complete': False,
        'quality_accepted': False, 'precision': 'NF4-double-quant-FP16',
        'native_tokenizer': True, 'max_input_tokens': 2048, 'max_new_tokens': 128,
        'attempts_per_example': 1, 'decoding': 'greedy-thinking-disabled'}
    try:
        tokenizer, model = load_secondary(args.model_dir)
        model.eval()
        model.gradient_checkpointing_disable()
        for case, requirement, facts, gold in selected:
            if time.perf_counter() - start >= cap - spent:
                raise TimeoutError('Study budget exhausted')
            row = generate_row(model, tokenizer, torch, case, requirement, facts, gold)
            report['rows'].append(row)
            with (args.output / 'raw.jsonl').open('a', encoding='utf8') as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        report['metrics'] = metrics(report['rows'])
        report['complete'] = True
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        report['wall_ms'] = (time.perf_counter() - start) * 1000
        budget['spent_seconds'] = spent + report['wall_ms'] / 1000
        report['study_budget'] = budget
        (args.output / 'comparison.json').write_text(json.dumps(report,
            ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
        args.budget_file.write_text(json.dumps(budget, indent=2), encoding='utf8')
        lock.unlink()


if __name__ == '__main__':
    main()
