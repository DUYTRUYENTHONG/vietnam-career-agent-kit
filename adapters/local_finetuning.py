"""Opt-in offline LoRA experiment over an exact current reviewed CV export.

No model downloads, provider calls, ledger mutations or automatic promotion.
Heavy dependencies are imported only by the explicitly invoked training runner.
"""
import argparse
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
from time import perf_counter

from core.learning import check_export
from core.ledger import canonical_hash
from core.documents import Documents
from core.workflow import WorkflowError


def prepare(work, directory, model_directory, output):
    """Validate current reviews and load their exact immutable train/eval rows."""
    checked = check_export(work, directory).data
    if not checked['ready_for_split']:
        raise ValueError('Need at least two independent reviewed groups; export has no held-out split')
    model = Path(model_directory).resolve(strict=True)
    if not model.is_dir() or not (model/'config.json').is_file():
        raise ValueError('Select an existing local causal-language-model directory')
    target = work.inside(output)
    root = work.inside('training')
    if target == root or not target.is_relative_to(root) or target.exists():
        raise ValueError('Use a new private training/ subdirectory; never overwrite a run')
    source = work.inside(directory)
    rows = {}
    for split, filename in [('train', 'train.jsonl'), ('evaluation', 'evaluation.jsonl')]:
        rows[split] = [json.loads(line)['messages'] for line in
                       (source/filename).read_text(encoding='utf8').splitlines()]
    # Recheck after reading so edited/stale bytes cannot silently enter training.
    if check_export(work, directory).data['manifest_fingerprint'] != checked['manifest_fingerprint']:
        raise ValueError('Dataset changed during preparation')
    return model, target, rows, checked['manifest_fingerprint']


def encode(tokenizer, messages, max_length):
    """Mask the prompt; fail on truncation or a non-prefix-compatible template."""
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=True,
        add_generation_prompt=True, enable_thinking=False)
    tokens = tokenizer.apply_chat_template(messages, tokenize=True,
        add_generation_prompt=False, enable_thinking=False)
    if (not prefix or tokens[:len(prefix)] != prefix or len(tokens) <= len(prefix)
            or len(tokens) > max_length):
        raise ValueError('Example exceeds token limit or template cannot isolate assistant output; no truncation')
    return {'input_ids': tokens, 'labels': [-100]*len(prefix)+tokens[len(prefix):]}


def histogram(rows):
    lengths = sorted(len(row['input_ids']) for row in rows)
    return {'count': len(lengths), 'min': lengths[0], 'max': lengths[-1],
            'median': lengths[len(lengths)//2], 'total': sum(lengths)}


def finite_loss(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Non-finite model loss; run cannot be completed')
    return value


def model_hashes(directory):
    hashes = {}
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix in ('.json', '.safetensors', '.txt', '.jinja'):
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    digest.update(chunk)
            hashes[path.name] = digest.hexdigest()
    return hashes


def train(work, directory, model_directory, output, *, target_modules,
          epochs=2, learning_rate=0.0002, max_length=2048, device='cpu'):
    """Small batch-one LoRA baseline, assistant-token-weighted held-out NLL.

    This is not a production trainer, QLoRA implementation or quality approval.
    Device is explicit CPU/CUDA only; no claim of Intel accelerator support.
    """
    if (type(epochs) is not int or not 1 <= epochs <= 10 or
            type(max_length) is not int or not 128 <= max_length <= 8192 or
            type(learning_rate) not in (int, float) or not 0 < learning_rate <= .01 or
            device not in ('cpu', 'cuda') or not isinstance(target_modules, list) or
            not target_modules or any(not isinstance(x, str) or not x.strip() for x in target_modules)):
        raise ValueError('Invalid bounded training configuration')
    model_path, target, rows, fingerprint = prepare(work, directory, model_directory, output)
    # Enforce offline library behavior before importing optional dependencies.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model
    if device == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA selected but unavailable')
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
    encoded = {split: [encode(tokenizer, row, max_length) for row in values]
               for split, values in rows.items()}
    torch.manual_seed(42)
    identity = model_hashes(model_path)
    model = AutoModelForCausalLM.from_pretrained(str(model_path), local_files_only=True,
                                                trust_remote_code=False, use_safetensors=True)
    model.to(device)
    model.config.use_cache = False
    settings = {'schema_version': '1.0', 'dataset_fingerprint': fingerprint,
        'model_config_hash': canonical_hash(json.loads((model_path/'config.json').read_text(encoding='utf8'))),
        'base_model_directory': str(model_path), 'epochs': epochs, 'learning_rate': learning_rate,
        'base_model_files': identity,
        'max_length': max_length, 'device': device, 'seed': 42, 'batch_size': 1,
        'warmup_fraction': .1, 'lora_rank': 8, 'lora_alpha': 16, 'lora_dropout': .05,
        'target_modules': target_modules,
        'versions': {p: version(p) for p in ('torch', 'transformers', 'peft')},
        'token_lengths': {split: histogram(values) for split, values in encoded.items()},
        'training_performed': False, 'promoted': False, 'provider_calls': 0}
    # Revalidate before reserving a run; failures leave no successful completion marker.
    if check_export(work, directory).data['manifest_fingerprint'] != fingerprint:
        raise ValueError('Dataset changed before training')
    target.mkdir(parents=True, exist_ok=False)
    (target/'config.json').write_text(json.dumps(settings, indent=2), encoding='utf8')

    def batch(row):
        return {k: torch.tensor([v], device=device) for k, v in row.items()}

    def synchronize():
        if device == 'cuda':
            torch.cuda.synchronize()

    def evaluate():
        model.eval()
        total, count = 0.0, 0
        synchronize(); started = perf_counter()
        with torch.no_grad():
            for row in encoded['evaluation']:
                tokens = sum(x != -100 for x in row['labels'][1:])
                total += finite_loss(model(**batch(row)).loss.item())*tokens
                count += tokens
        synchronize()
        loss = finite_loss(total/count)
        return {'assistant_token_nll': loss, 'perplexity': math.exp(loss) if loss < 700 else None,
                'assistant_tokens': count, 'teacher_forced_evaluation_ms': (perf_counter()-started)*1000}

    baseline = evaluate()
    model = get_peft_model(model, LoraConfig(task_type='CAUSAL_LM', r=8,
        lora_alpha=16, lora_dropout=.05, target_modules=target_modules, bias='none'))
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                  lr=learning_rate, weight_decay=.01)
    steps = epochs*len(encoded['train'])
    warmup = max(1, math.ceil(steps*.1))
    losses = []
    synchronize(); started = perf_counter()
    for epoch in range(epochs):
        model.train()
        for i, row in enumerate(encoded['train']):
            step = epoch*len(encoded['train'])+i+1
            rate = min(step/warmup, max(0.0, (steps-step+1)/max(1, steps-warmup)))
            for group in optimizer.param_groups:
                group['lr'] = learning_rate*rate
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch(row)).loss
            finite_loss(loss.item())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        losses.append({'epoch': epoch+1, 'evaluation': evaluate()})
    synchronize(); duration = (perf_counter()-started)*1000
    # Check for revoked/changed source reviews before labelling any saved run complete.
    if check_export(work, directory).data['manifest_fingerprint'] != fingerprint:
        raise ValueError('Evidence changed during training; run remains incomplete')
    model.save_pretrained(str(target/'adapter'), safe_serialization=True)
    tokenizer.save_pretrained(str(target/'adapter'))
    result = {**settings, 'training_performed': True, 'training_ms': duration,
        'training_ms_includes_epoch_evaluation': True, 'optimizer_steps': steps,
        'trainable_parameters': sum(p.numel() for p in model.parameters() if p.requires_grad),
        'baseline': baseline, 'epochs_evaluation': losses,
        'task_quality_evaluation': 'pending independent factual/specificity review; no automatic promotion',
        'generation_latency_ms': None, 'host_tokens': None}
    (target/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--directory', required=True, help='Existing reviewed datasets/ export')
    parser.add_argument('--model-directory', required=True)
    parser.add_argument('--output', required=True, help='New training/ subdirectory')
    parser.add_argument('--target-module', action='append', required=True)
    parser.add_argument('--epochs', type=int, default=2)
    parser.add_argument('--max-length', type=int, default=2048)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    args = parser.parse_args()
    try:
        train(Documents(args.data_dir), args.directory, args.model_directory, args.output,
              target_modules=args.target_module, epochs=args.epochs,
              max_length=args.max_length, device=args.device)
    except (ValueError, WorkflowError, ImportError, OSError) as exc:
        parser.exit(1, f'Training not completed: {exc}\n')
    print('Local run completed; inspect private result.json. Model is not promoted or approved.')


if __name__ == '__main__':
    main()
