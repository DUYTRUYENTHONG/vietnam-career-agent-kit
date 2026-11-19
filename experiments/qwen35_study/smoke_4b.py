"""One real4B LoRA update; discard weights and never claim a completed training run."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from adapters.qwen35_pairing import checkpoint_binding
from core.evidence_pairing import strict_json
from experiments.qwen35_study.runtime import load_qwen35
from experiments.qwen35_study.train_4b import MODEL, REVISION, encode_example
from experiments.qwen35_study.gradients import gradient_health, require_finite_gradients


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data', 'model-dir', 'output', 'budget-file'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--initial-scale', type=float, choices=(1.0, 65536.0), default=65536.0)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    raw = args.data.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.sha256:
        raise ValueError('Dataset hash mismatch')
    rows = [strict_json(line) for line in raw.decode('utf8').splitlines() if line.strip()]
    if len(rows) != 10000 or args.output.exists():
        raise ValueError('Need10000rows and fresh output directory')
    binding = checkpoint_binding(args.model_dir)
    if not args.run:
        print(json.dumps({'mode': 'preflight_only', 'rows': len(rows), 'model_loaded': False}))
        return
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
    started = time.perf_counter()
    record = {'scope': 'one optimizer update on first training row; weights discarded',
        'model': MODEL, 'revision': REVISION, 'dataset_sha256': args.sha256,
        'checkpoint_binding': binding, 'training_completed': False,
        'smoke_passed': False, 'quality_accepted': False, 'optimizer_steps': 0,
        'seed': 42, 'precision': 'NF4-double-quant-FP16', 'weights_saved': False,
        'amp_initial_scale': args.initial_scale}
    try:
        import torch
        from transformers import set_seed
        from peft import LoraConfig, get_peft_model
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required; no CPU fallback')
        record['torch'] = torch.__version__
        record['gpu'] = torch.cuda.get_device_name(0)
        record['cuda'] = torch.version.cuda
        set_seed(42)
        torch.cuda.reset_peak_memory_stats()
        tokenizer, model = load_qwen35(args.model_dir)
        targets = [n for n, _ in model.named_modules()
                   if n.endswith(('.q_proj', '.v_proj')) and 'visual' not in n]
        if not targets:
            raise ValueError('No text attention LoRA targets')
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
            lora_dropout=0.05, bias='none', target_modules=targets, task_type='CAUSAL_LM'))
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        model.train()
        encoded = encode_example(rows[0], tokenizer, 2048)
        batch = {name: torch.tensor([value], device='cuda') for name, value in encoded.items()}
        record['input_tokens'] = sum(encoded['attention_mask'])
        record['assistant_tokens'] = sum(x != -100 for x in encoded['labels'])
        trainable = {name: p for name, p in model.named_parameters() if p.requires_grad}
        before = {name: p.detach().float().cpu().clone() for name, p in trainable.items()}
        record['trainable_parameters'] = sum(p.numel() for p in trainable.values())
        optimizer = torch.optim.AdamW(trainable.values(), lr=5e-5, weight_decay=0.0)
        scaler = torch.amp.GradScaler('cuda', init_scale=args.initial_scale)
        if time.perf_counter() - started >= cap - spent:
            raise TimeoutError('Study budget exhausted before smoke update')
        torch.cuda.synchronize()
        update_started = time.perf_counter()
        with torch.autocast('cuda', dtype=torch.float16):
            loss = model(**batch).loss
        if not torch.isfinite(loss).item():
            raise ValueError('Nonfinite smoke loss')
        record['loss'] = float(loss.detach().float().item())
        record['amp_scale_before_backward'] = float(scaler.get_scale())
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        record.update(gradient_health(trainable.values(), torch))
        require_finite_gradients(record)
        scaler.step(optimizer)
        scaler.update()
        torch.cuda.synchronize()
        record['update_ms'] = (time.perf_counter() - update_started) * 1000
        record['changed_adapter_tensors'] = sum(not torch.equal(before[n], p.detach().float().cpu())
                                                for n, p in trainable.items())
        record['peak_allocated_gpu_bytes'] = torch.cuda.max_memory_allocated()
        record['optimizer_steps'] = 1
        if not record['changed_adapter_tensors']:
            raise ValueError('No adapter parameter changed')
        record['smoke_passed'] = True
    except Exception as exc:
        record['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        record['wall_ms'] = (time.perf_counter() - started) * 1000
        budget['spent_seconds'] = spent + record['wall_ms']/1000
        record['study_budget'] = budget
        (args.output / 'smoke_record.json').write_text(json.dumps(record, indent=2,
            allow_nan=False), encoding='utf8')
        args.budget_file.write_text(json.dumps(budget, indent=2), encoding='utf8')
        lock.unlink()
        print(json.dumps(record, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
