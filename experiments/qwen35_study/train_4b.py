"""Explicit local Qwen3.5-4B study run. No network, installation or promotion."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.evidence_pairing import checked, strict_json
from adapters.qwen35_pairing import checkpoint_binding
from experiments.qwen35_study.runtime import load_qwen35
from experiments.qwen35_study.gradients import gradient_health, require_finite_gradients

MODEL = 'Qwen/Qwen3.5-4B'
REVISION = '851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'


def encode_example(row: dict, tokenizer, max_length: int) -> dict:
    messages = row['messages']
    if [m['role'] for m in messages] != ['system', 'user', 'assistant']:
        raise ValueError('Expected system/user/assistant only')
    user = strict_json(messages[1]['content'])
    if set(user) != {'requirement', 'facts'}:
        raise ValueError('User input must exclude labels, rationales and metadata')
    facts = user['facts']
    if any(set(f) != {'id', 'text'} for f in facts):
        raise ValueError('Only fact IDs and quotes are model inputs')
    ids = [f['id'] for f in facts]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate fact IDs')
    answer = checked(strict_json(messages[-1]['content']), {f['id']: f for f in facts})
    prefix = tokenizer.apply_chat_template(messages[:2], tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    prompt = tokenizer.encode(prefix, add_special_tokens=False)
    completion = tokenizer.encode(json.dumps(answer, ensure_ascii=False,
        separators=(',', ':')), add_special_tokens=False) + [tokenizer.eos_token_id]
    if len(prompt) + len(completion) > max_length:
        raise ValueError('Sequence exceeds budget; no truncation permitted')
    return {'input_ids': prompt + completion,
            'attention_mask': [1] * (len(prompt) + len(completion)),
            'labels': [-100] * len(prompt) + completion}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--model-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--budget-file', type=Path,
                        help='Shared study budget JSON: cap_seconds and spent_seconds')
    parser.add_argument('--seed', type=int, choices=(17, 42, 2026), default=42)
    parser.add_argument('--learning-rate', type=float, choices=(5e-5, 1e-4), default=5e-5)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--initial-scale', type=float, choices=(1.0, 65536.0), default=65536.0)
    args = parser.parse_args()
    raw = args.data.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.sha256:
        raise ValueError('Dataset hash mismatch')
    rows = [strict_json(s) for s in raw.decode('utf8').splitlines() if s.strip()]
    if len(rows) != 10000:
        raise ValueError('Study requires exactly10000 declared training rows')
    if args.output.exists():
        raise ValueError('Use a fresh output directory')
    if not args.run:
        print(json.dumps({'mode': 'preflight_only', 'rows': len(rows),
            'planned_optimizer_steps': 1250, 'training_started': False}))
        return
    if not args.budget_file:
        raise ValueError('A shared study budget file is required for training')
    budget = strict_json(args.budget_file.read_text(encoding='utf8'))
    cap, spent = budget['cap_seconds'], budget['spent_seconds']
    if (type(cap) not in (int, float) or type(spent) not in (int, float)
            or not math.isfinite(cap) or not math.isfinite(spent)
            or not 0 < cap <= 43200 or not 0 <= spent < cap):
        raise ValueError('Invalid or exhausted study budget')
    import torch
    from transformers import (AutoTokenizer, Trainer, TrainingArguments, TrainerCallback,
        DataCollatorForSeq2Seq, set_seed)
    from peft import LoraConfig, get_peft_model
    if not torch.cuda.is_available():
        raise RuntimeError('Compatible CUDA GPU required; no CPU or paid fallback')
    lock = args.budget_file.with_suffix('.running')
    with lock.open('x', encoding='utf8') as stream:
        stream.write(str(args.output))
    set_seed(args.seed)
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    result = {'model': MODEL, 'revision': REVISION, 'dataset_sha256': args.sha256,
        'training_completed': False, 'quality_accepted': False, 'promoted': False,
        'gpu': torch.cuda.get_device_name(0), 'seed': args.seed,
        'input_tokens': 0, 'assistant_tokens': 0, 'planned_steps': 1250,
        'amp_initial_scale': args.initial_scale, 'verified_optimizer_steps': 0}
    trainer = None
    try:
        result['checkpoint_binding'] = checkpoint_binding(args.model_dir)
        tokenizer = AutoTokenizer.from_pretrained(args.model_dir, local_files_only=True)
        tokenizer.pad_token = tokenizer.eos_token
        data = [encode_example(row, tokenizer, 2048) for row in rows]
        loaded_tokenizer, model = load_qwen35(args.model_dir)
        if loaded_tokenizer.get_vocab() != tokenizer.get_vocab():
            raise ValueError('Tokenizer changed during preparation')
        targets = [n for n, _ in model.named_modules()
            if n.endswith(('.q_proj', '.v_proj')) and 'visual' not in n]
        if not targets:
            raise ValueError('No text attention targets found')
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16,
            lora_dropout=0.05, bias='none', target_modules=targets,
            task_type='CAUSAL_LM'))
        result['trainable_parameters'] = model.get_nb_trainable_parameters()[0]

        class Budget(TrainerCallback):
            def on_pre_optimizer_step(self, args, state, control, model=None, **kwargs):
                health = gradient_health(model.parameters(), torch)
                result['last_gradient_health'] = health
                require_finite_gradients(health)

            def on_optimizer_step(self, args, state, control, **kwargs):
                if trainer.accelerator.optimizer_step_was_skipped:
                    raise ValueError('Skipped optimizer update; stop and retain evidence')
                result['verified_optimizer_steps'] += 1

            def on_step_end(self, args, state, control, **kwargs):
                if time.perf_counter() - started >= cap - spent:
                    raise TimeoutError('Study budget reached; preserve checkpoints')

        class CountedTrainer(Trainer):
            def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
                result['input_tokens'] += int(inputs['attention_mask'].sum().item())
                result['assistant_tokens'] += int((inputs['labels'] != -100).sum().item())
                value = super().compute_loss(model, inputs,
                    return_outputs=return_outputs, **kwargs)
                loss = value[0] if return_outputs else value
                if not torch.isfinite(loss).item():
                    raise ValueError('Nonfinite training loss')
                return value

        training = TrainingArguments(output_dir=str(args.output / 'checkpoints'),
            per_device_train_batch_size=1, gradient_accumulation_steps=8,
            learning_rate=args.learning_rate, num_train_epochs=1,
            warmup_ratio=0.1, lr_scheduler_type='cosine', fp16=True, bf16=False,
            gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
            logging_steps=25, save_steps=250, save_total_limit=3,
            report_to='none', seed=args.seed, data_seed=args.seed,
            dataloader_num_workers=0, remove_unused_columns=False)
        trainer = CountedTrainer(model=model, args=training, train_dataset=data,
            data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True,
                label_pad_token_id=-100), callbacks=[Budget()])
        if trainer.accelerator.scaler is None:
            raise ValueError('Expected native FP16 GradScaler')
        trainer.accelerator.scaler = torch.amp.GradScaler('cuda', init_scale=args.initial_scale)
        torch.cuda.synchronize()
        train_start = time.perf_counter()
        trainer.train()
        torch.cuda.synchronize()
        result['training_ms'] = (time.perf_counter() - train_start) * 1000
        trainer.save_model(str(args.output / 'adapter'))
        tokenizer.save_pretrained(args.output / 'adapter')
        result['adapter_binding'] = checkpoint_binding(args.output / 'adapter')
        result['training_completed'] = True
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        result['optimizer_steps'] = result['verified_optimizer_steps']
        result['trainer_global_steps'] = trainer.state.global_step if trainer else 0
        result['wall_ms'] = (time.perf_counter() - started) * 1000
        budget['spent_seconds'] = spent + result['wall_ms'] / 1000
        result['study_budget'] = budget
        (args.output / 'training_record.json').write_text(
            json.dumps(result, indent=2, allow_nan=False), encoding='utf8')
        args.budget_file.write_text(json.dumps(budget, indent=2), encoding='utf8')
        lock.unlink()


if __name__ == '__main__':
    main()
