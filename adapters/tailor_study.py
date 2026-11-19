"""Optional pinned Qwen3.5 GPU experiment; never imported by the core CLI.

Use only after human benchmark/training review and exact cloud disclosure scope.
The free-compute flag is a caller attestation, not provider billing verification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time

from core import tailor_benchmark as b


def training_rows(root, rows, evaluation_cases):
    b.require(isinstance(rows, list) and rows, 'No reviewed training rows')
    seen = set(); evaluation_groups = {c['source_group'] for c in evaluation_cases}
    for row in rows:
        b.object_fields(row, {'case', 'target', 'reviews'}, set(), 'training row')
        case = row['case']; b.validate_cases(root, [case])
        b.require(case['case_id'] not in seen, 'Duplicate training case')
        seen.add(case['case_id'])
        b.require(case['source_group'] not in evaluation_groups,
                  'Training and evaluation employer/source family overlap')
        target = json.dumps(row['target'], ensure_ascii=False)
        b.validate_output(target, case)
        reviewers = set()
        b.require(isinstance(row['reviews'], list) and len(row['reviews']) >= 2,
                  'Two actual human training-target reviews required')
        for review in row['reviews']:
            b.object_fields(review, {'reviewer_id', 'reviewer_type', 'source_checked',
                'entailed', 'qualifiers_preserved', 'target_sha256'}, set(), 'training review')
            b.text(review['reviewer_id'], 'training reviewer ID')
            b.require(review['reviewer_id'] not in reviewers, 'Distinct training reviewers required')
            reviewers.add(review['reviewer_id'])
            b.require(review['reviewer_type'] == 'human' and review['source_checked'] is True and
                review['entailed'] is True and review['qualifiers_preserved'] is True and
                review['target_sha256'] == b.binding(row['target']),
                'Training target is not independently reviewed/currently bound')
    return rows


def checkpoint(directory):
    folder = Path(directory).resolve(strict=True)
    manifest = b.read_json(folder/'download-manifest.json')
    b.require(manifest.get('model_id') == b.RUNTIME_PROTOCOL['model_id'] and
              manifest.get('revision') == b.RUNTIME_PROTOCOL['revision'], 'Wrong pinned base checkpoint')
    files = manifest.get('files')
    b.require(isinstance(files, dict) and files and any(n.endswith('.safetensors') for n in files),
              'Bind complete local checkpoint files')
    observed = {}
    for name, expected in files.items():
        path = b.inside(folder, name)
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                h.update(chunk)
        b.require(h.hexdigest() == expected, 'Changed local checkpoint member: '+name)
        observed[name] = expected
    relevant = {p.relative_to(folder).as_posix() for p in folder.rglob('*')
        if p.is_file() and p.suffix in {'.json', '.safetensors', '.model', '.jinja', '.tiktoken', '.txt'}
        and p.name != 'download-manifest.json'}
    b.require(relevant <= set(files), 'Unbound loader-relevant checkpoint files')
    tok = {k: v for k, v in observed.items() if 'token' in k or 'vocab' in k or 'merges' in k or 'chat_template' in k}
    b.require(tok, 'Bind tokenizer and chat template files')
    return b.binding(tok)


def worker(args):
    folder, fm = b.verify_bundle(args.root, args.frozen, 'tailor_benchmark_frozen')
    cases = b.validate_cases(args.root, b.read_rows(folder/'cases.jsonl'))
    inputs = b.read_rows(folder/'generation_inputs.jsonl')
    b.require(len(inputs) == len(cases) and all(
        inp['case_id'] == case['case_id'] and inp['case_sha256'] == b.binding(case)
        for inp, case in zip(inputs, cases)), 'Frozen input order or coverage changed')
    training_system = inputs[0]['conditions']['adapter_evidence'][0]['content']
    b.require(all(inp['conditions']['adapter_evidence'][0]['content'] == training_system
                  for inp in inputs), 'Keep one fixed training system prompt')
    training = training_rows(args.root, b.read_rows(b.inside(args.root, args.training)), cases) if args.training else None
    b.require((args.comparison == 'training') == bool(training), 'Training comparison requires reviewed data; prompt comparison must not train')
    tokenizer_hash = checkpoint(args.model_directory)
    # No SDK imports or model load until source, review, split and checkpoint gates pass.
    import torch
    from transformers import AutoTokenizer, BitsAndBytesConfig, Qwen3_5ForConditionalGeneration
    b.require(torch.cuda.is_available() and 'T4' in torch.cuda.get_device_name(0),
              'Free T4 required; no CPU/paid/other-device fallback')
    torch.manual_seed(42); random.seed(42)
    tokenizer = AutoTokenizer.from_pretrained(args.model_directory, local_files_only=True, trust_remote_code=False)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(args.model_directory,
        local_files_only=True, trust_remote_code=False, device_map={'': 0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True))
    if training:
        # Preparation may cast nonquantized layers: apply it before baseline
        # measurement so that preparation itself is not an adapter advantage.
        from peft import prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(model)
    model.eval()
    destination = b.inside(args.root, args.output)
    measurements = destination/'generations.jsonl'

    def encode(messages, generation):
        ids = tokenizer.apply_chat_template(messages, tokenize=True,
            add_generation_prompt=generation, enable_thinking=False)
        b.require(len(ids) <= b.RUNTIME_PROTOCOL['max_input_tokens'], 'Context exceeds protocol; no truncation')
        return ids

    def generate(arm, adapter_hash=None):
        for c, inp in zip(cases, inputs):
            b.require(c['case_id'] == inp['case_id'] and b.binding(c) == inp['case_sha256'], 'Input order/binding changed')
            ids = encode(inp['conditions'][arm], True)
            batch = torch.tensor([ids], device='cuda'); mask = torch.ones_like(batch)
            torch.cuda.synchronize(); start = time.perf_counter()
            with torch.inference_mode():
                output = model.generate(input_ids=batch, attention_mask=mask, do_sample=False,
                    max_new_tokens=b.RUNTIME_PROTOCOL['max_new_tokens'], use_cache=True,
                    pad_token_id=tokenizer.eos_token_id)
            torch.cuda.synchronize(); elapsed = (time.perf_counter()-start)*1000
            suffix = output[0, len(ids):]
            row = {'case_id': c['case_id'], 'condition': arm, 'case_sha256': b.binding(c),
                'messages_sha256': b.binding(inp['conditions'][arm]),
                'raw_output': tokenizer.decode(suffix, skip_special_tokens=True),
                'metrics': {'input_tokens': len(ids), 'output_tokens': suffix.numel(), 'generation_ms': elapsed},
                'runtime': dict(b.RUNTIME_PROTOCOL, tokenizer_sha256=tokenizer_hash, adapter_sha256=adapter_hash)}
            with measurements.open('a', encoding='utf8', newline='\n') as stream:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n'); stream.flush(); os.fsync(stream.fileno())

    generate('base_original'); generate('base_evidence')
    if training:
        from peft import LoraConfig, get_peft_model
        targets = [n for n, _ in model.named_modules() if n.endswith(('.q_proj', '.v_proj'))
                   and 'visual' not in n and 'vision' not in n]
        b.require(targets, 'No reviewed text attention targets resolved')
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=.05,
            target_modules=targets, bias='none', task_type='CAUSAL_LM'))
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        model.config.use_cache = False
        for p in model.parameters():
            if p.requires_grad:
                p.data = p.data.float()
        examples = []
        for row in training:
            training_messages = b.messages(row['case'], 'adapter_evidence')
            training_messages[0]['content'] = training_system
            prefix = encode(training_messages, True)
            suffix = tokenizer.encode(json.dumps(row['target'], ensure_ascii=False), add_special_tokens=False)+[tokenizer.eos_token_id]
            b.require(len(prefix)+len(suffix) <= b.RUNTIME_PROTOCOL['max_input_tokens'], 'Training sequence too long; no truncation')
            examples.append((prefix+suffix, [-100]*len(prefix)+suffix))
        model.train(); optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=5e-5)
        scaler = torch.amp.GradScaler('cuda', init_scale=1.0)
        total = 2*math.ceil(len(examples)/4); update = 0; losses = []
        for _ in range(2):
            random.shuffle(examples)
            for start in range(0, len(examples), 4):
                window = examples[start:start+4]; optimizer.zero_grad(set_to_none=True)
                for ids, labels in window:
                    with torch.autocast('cuda', dtype=torch.float16):
                        loss = model(input_ids=torch.tensor([ids], device='cuda'),
                            attention_mask=torch.ones((1, len(ids)), device='cuda'),
                            labels=torch.tensor([labels], device='cuda')).loss/len(window)
                    b.require(torch.isfinite(loss).item(), 'Nonfinite loss; no retry')
                    scaler.scale(loss).backward(); losses.append(float(loss.detach())*len(window))
                scaler.unscale_(optimizer)
                b.require(all(torch.isfinite(p.grad).all().item() for p in model.parameters()
                              if p.requires_grad and p.grad is not None), 'Nonfinite gradient; no retry')
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                ratio = min((update+1)/2, 1.0) if update < 2 else .5*(1+math.cos(math.pi*(update-2)/max(total-2, 1)))
                for group in optimizer.param_groups:
                    group['lr'] = 5e-5*ratio
                scaler.step(optimizer); scaler.update(); update += 1
        saved = destination/'adapter'; model.save_pretrained(saved, safe_serialization=True)
        (destination/'training.json').write_bytes(b.json_bytes({'updates': update, 'epochs': 2,
            'losses': losses, 'target_modules': targets, 'training_sha256': b.binding(training)}))
        files = {p.name: b.digest(p.read_bytes()) for p in saved.iterdir() if p.is_file()}
        adapter_hash = b.binding(files)
        model.eval(); model.config.use_cache = True
        generate('adapter_evidence', adapter_hash)
    (destination/'completed.json').write_bytes(b.json_bytes({'completed': True,
        'frozen_manifest_sha256': b.binding(fm), 'comparison': args.comparison,
        'model_promoted': False, 'application_authority': False}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True); p.add_argument('--frozen', required=True)
    p.add_argument('--model-directory', type=Path, required=True); p.add_argument('--output', required=True)
    p.add_argument('--comparison', choices=['prompt', 'training', 'retrieval'], default='prompt')
    p.add_argument('--training'); p.add_argument('--free-gpu-confirmed', action='store_true')
    p.add_argument('--prior-free-seconds', type=float, required=True)
    p.add_argument('--cumulative-cap-seconds', type=int, required=True)
    p.add_argument('--max-new-seconds', type=int, required=True)
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    b.require(a.free_gpu_confirmed, 'Verify free provider allocation before execution')
    b.require(math.isfinite(a.prior_free_seconds) and a.prior_free_seconds >= 0 and
        0 < a.max_new_seconds <= 7200 and a.prior_free_seconds+a.max_new_seconds <= a.cumulative_cap_seconds,
        'Explicit finite cumulative free budget required; no reset of prior spend')
    if a.worker:
        worker(a); return 0
    b.require(sys.platform == 'linux', 'Experimental free-cloud runner requires Linux T4; no local fallback')
    destination = b.inside(a.root, a.output)
    b.require(not destination.exists(), 'Use new output; no automatic run retry')
    destination.mkdir(parents=True)
    (destination/'started.json').write_bytes(b.json_bytes({'free_allocation_attested': True,
        'provider_billing_verified_by_code': False, 'prior_free_seconds': a.prior_free_seconds,
        'max_new_seconds': a.max_new_seconds, 'cumulative_cap_seconds': a.cumulative_cap_seconds}))
    start = time.monotonic(); status = 'failed'; code = None
    try:
        command = [sys.executable, '-m', 'adapters.tailor_study', *(argv if argv is not None else sys.argv[1:]), '--worker']
        with (destination/'console.log').open('wb') as log:
            proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=a.max_new_seconds)
        code = proc.returncode; status = 'completed' if code == 0 else 'failed'
    except subprocess.TimeoutExpired:
        status = 'timed_out'
    finally:
        elapsed = time.monotonic()-start
        (destination/'budget_result.json').write_bytes(b.json_bytes({'status': status,
            'observed_wrapper_seconds': elapsed, 'cumulative_accounted_seconds': a.prior_free_seconds+elapsed,
            'exit_code': code, 'automatic_retry': False, 'model_promoted': False}))
        files = {q.relative_to(destination).as_posix(): b.digest(q.read_bytes())
                 for q in destination.rglob('*') if q.is_file()}
        (destination/'SHA256.json').write_bytes(b.json_bytes(files))
    return 0 if status == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
