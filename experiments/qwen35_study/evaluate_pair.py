"""Paired NF4 base/adapter synthetic evaluation. Never a sealed human test."""
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
from scripts.evidence_bench import load_cases, examples, metrics
from experiments.qwen35_study.runtime import load_qwen35
from experiments.qwen35_study.generation import generate_row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'model-dir', 'adapter', 'training-record', 'budget-file', 'output'):
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--partition', choices=('development', 'test'), default='development')
    p.add_argument('--acknowledge-exposed-regression', action='store_true')
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    if a.partition == 'test' and not a.acknowledge_exposed_regression:
        raise ValueError('Public test is exposed regression; acknowledge that scope')
    selected = examples(load_cases(a.dataset), a.partition)
    if not selected or a.output.exists():
        raise ValueError('Need nonempty partition and fresh output directory')
    record = strict_json(a.training_record.read_text(encoding='utf8'))
    if not record.get('training_completed') or record.get('model') != 'Qwen/Qwen3.5-4B':
        raise ValueError('Completed actual4B training record required')
    if checkpoint_binding(a.adapter) != record['adapter_binding']:
        raise ValueError('Adapter bytes differ from completed training')
    if checkpoint_binding(a.model_dir) != record['checkpoint_binding']:
        raise ValueError('Base bytes differ from training')
    if not a.run:
        print(json.dumps({'mode': 'preflight_only', 'rows': len(selected), 'inference_started': False}))
        return
    import torch
    from peft import PeftModel
    if not torch.cuda.is_available():
        raise RuntimeError('Free CUDA GPU required; no CPU fallback')
    budget = strict_json(a.budget_file.read_text(encoding='utf8'))
    cap, spent = budget['cap_seconds'], budget['spent_seconds']
    if (type(cap) not in (int, float) or type(spent) not in (int, float)
            or not math.isfinite(cap) or not math.isfinite(spent)
            or not 0 <= spent < cap <= 43200):
        raise ValueError('Invalid or exhausted study budget')
    lock = a.budget_file.with_suffix('.running')
    with lock.open('x') as stream:
        stream.write(str(a.output))
    a.output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    output = {'scope': 'exposed synthetic regression only', 'partition': a.partition,
        'dataset_sha256': hashlib.sha256(a.dataset.read_bytes()).hexdigest(),
        'training_record_sha256': hashlib.sha256(a.training_record.read_bytes()).hexdigest(),
        'checkpoint_binding': record['checkpoint_binding'],
        'adapter_binding': record['adapter_binding'], 'systems': {'base': [], 'adapter': []},
        'quality_accepted': False, 'complete': False}
    try:
        tokenizer, base = load_qwen35(a.model_dir)
        model = PeftModel.from_pretrained(base, a.adapter, local_files_only=True)
        model.eval()
        # Training enables checkpointing; evaluation uses identical cache settings.
        model.gradient_checkpointing_disable()
        for case, requirement, facts, gold in selected:
            for variant in ('base', 'adapter'):
                if time.perf_counter() - start >= cap - spent:
                    raise TimeoutError('Study budget exhausted')
                from contextlib import nullcontext
                context = model.disable_adapter() if variant == 'base' else nullcontext()
                with context:
                    row = generate_row(model, tokenizer, torch, case, requirement, facts, gold)
                output['systems'][variant].append(row)
                with (a.output/'raw.jsonl').open('a', encoding='utf8') as stream:
                    stream.write(json.dumps({'variant': variant, **row}, ensure_ascii=False)+'\n')
        output['metrics'] = {v: metrics(rows) for v, rows in output['systems'].items()}
        output['complete'] = True
    except Exception as exc:
        output['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        output['wall_ms'] = (time.perf_counter()-start)*1000
        budget['spent_seconds'] = spent + output['wall_ms']/1000
        output['study_budget'] = budget
        (a.output/'comparison.json').write_text(json.dumps(output, ensure_ascii=False,
            indent=2, allow_nan=False), encoding='utf8')
        a.budget_file.write_text(json.dumps(budget, indent=2), encoding='utf8')
        lock.unlink()


if __name__ == '__main__':
    main()
