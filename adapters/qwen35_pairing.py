"""Optional offline inference and completion-only LoRA for the evidence-pairing pilot."""
import json
import hashlib
import time
import math
from pathlib import Path
from itertools import combinations
from random import Random
from string import ascii_uppercase, digits

from core.evidence_pairing import messages, strict_json


def checkpoint_binding(directory):
    """Observe local model bytes; this does not authenticate upstream origin."""
    root = Path(directory).resolve(strict=True)
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.suffix in {'.json', '.safetensors', '.model',
                                              '.txt', '.jinja', '.tiktoken'}:
            if not path.resolve().is_relative_to(root):
                raise ValueError('Checkpoint link escapes selected directory')
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            files[path.relative_to(root).as_posix()] = digest.hexdigest()
    if not files or not any(n.endswith('.safetensors') for n in files):
        raise ValueError('Checkpoint requires local safetensors weights')
    return {'files': files, 'upstream_origin_verified': False}


def choice_menu(requirement, facts):
    """A bounded comparison method; supports evidence sets of size one or two."""
    if len(facts) > 4:
        raise ValueError("Choice decoding supports up to four facts; select an explicit retrieval pool")
    options = [{"label": "unknown", "fact_ids": []}]
    for size in (1, 2):
        for group in combinations(sorted(facts), size):
            options.extend({"label": label, "fact_ids": list(group)}
                           for label in ("direct", "partial", "contradicted"))
    Random("menu-v1:" + requirement["text"]).shuffle(options)
    return dict(zip(ascii_uppercase + digits, options))


class LocalQwen:
    def __init__(self, model_dir, *, adapter=None, max_new_tokens=64, device='cpu'):
        import torch
        from transformers import AutoConfig, AutoTokenizer, Qwen3_5ForConditionalGeneration, Qwen3ForCausalLM

        self.torch = torch
        self.max_new_tokens = max_new_tokens
        if device == 'cuda' and not torch.cuda.is_available():
            raise ValueError('Requested CUDA unavailable; no CPU fallback')
        self.device = torch.device(device)
        self.measurements = []
        self.checkpoint_binding = checkpoint_binding(model_dir)
        self.adapter_binding = checkpoint_binding(adapter) if adapter else None
        cfg = AutoConfig.from_pretrained(model_dir, local_files_only=True)
        cls = {"qwen3_5": Qwen3_5ForConditionalGeneration, "qwen3": Qwen3ForCausalLM}.get(cfg.model_type)
        if cls is None:
            raise ValueError("Expected a local Qwen3.5 or Qwen3 checkpoint")
        self.tok = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        dtype = torch.bfloat16 if self.device.type == "cpu" or torch.cuda.is_bf16_supported() else torch.float32
        self.model = cls.from_pretrained(model_dir, local_files_only=True, dtype=dtype).to(self.device)
        if adapter:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter, local_files_only=True)
        self.model.eval()

    def prefix(self, req, facts):
        return self.tok.apply_chat_template(messages(req, facts), tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)

    def predict(self, req, facts):
        prefix = self.prefix(req, facts)
        batch = self.tok(prefix, return_tensors="pt", add_special_tokens=False).to(self.device)
        if self.device.type == 'cuda':
            self.torch.cuda.synchronize()
        start = time.perf_counter()
        with self.torch.inference_mode():
            ids = self.model.generate(**batch, do_sample=False, max_new_tokens=self.max_new_tokens,
                                      pad_token_id=self.tok.eos_token_id)
        if self.device.type == 'cuda':
            self.torch.cuda.synchronize()
        elapsed = (time.perf_counter() - start) * 1000
        suffix = ids[0, batch.input_ids.shape[1]:]
        self.measurements.append({'input_tokens': int(batch.input_ids.shape[1]),
                                  'output_tokens': int(suffix.numel()),
                                  'generation_ms': elapsed, 'includes_loading_or_tokenization': False})
        return strict_json(self.tok.decode(suffix, skip_special_tokens=True).strip())

    def choose(self, req, facts):
        menu = choice_menu(req, facts)
        prompt = messages(req, facts)
        prompt[0]["content"] += " For this variant choose the letter or digit of one complete answer from the menu."
        prompt[1]["content"] += "\nMenu: " + json.dumps(menu, separators=(",", ":"))
        prefix = self.tok.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True,
                                              enable_thinking=False) + "Choice: "
        ids = [self.tok.encode(k, add_special_tokens=False) for k in menu]
        if any(len(i) != 1 for i in ids) or len({i[0] for i in ids}) != len(menu):
            raise ValueError("Menu codes must be distinct single tokens in this tokenizer")
        batch = self.tok(prefix, return_tensors="pt", add_special_tokens=False).to(self.device)
        with self.torch.inference_mode():
            logits = self.model(**batch, logits_to_keep=1).logits[0, -1]
        index = int(logits[[i[0] for i in ids]].argmax())
        return list(menu.values())[index]

    def train(self, rows, directory, epochs, seed, max_length=2048):
        from peft import LoraConfig, get_peft_model

        if directory.exists() or epochs < 1 or not rows:
            raise ValueError("Use a new adapter directory, positive epochs and nonempty training split")
        torch = self.torch
        torch.manual_seed(seed)
        rng = Random(seed)
        # Explicit module paths exclude vision weights in the multimodal checkpoint.
        targets = [n for n, _ in self.model.named_modules()
                   if n.endswith((".q_proj", ".v_proj")) and "visual" not in n and "vision" not in n]
        if not targets:
            raise ValueError("No text attention projection matched")
        model = get_peft_model(self.model, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0,
                               bias="none", target_modules=targets))
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.train()
        optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=0.0001)
        losses = []
        encoded = []
        for req, facts, answer in rows:
            prefix = self.tok.encode(self.prefix(req, facts), add_special_tokens=False)
            target = self.tok.encode(json.dumps(answer, ensure_ascii=False, separators=(",", ":")),
                                     add_special_tokens=False) + [self.tok.eos_token_id]
            if len(prefix) + len(target) > max_length:
                raise ValueError("Training sequence exceeds token budget; review packet")
            encoded.append((prefix + target, [-100] * len(prefix) + target))
        total_steps = epochs * len(encoded)
        warmup_steps = max(1, math.ceil(total_steps * 0.1))
        scheduler = torch.optim.lr_scheduler.LambdaLR(
            optimizer, lambda step: min((step + 1) / warmup_steps, 1.0))
        for _ in range(epochs):
            rng.shuffle(encoded)
            for tokens, labels in encoded:
                inputs = torch.tensor([tokens], device=self.device)
                label_ids = torch.tensor([labels], device=self.device)
                optimizer.zero_grad(set_to_none=True)
                loss = model(input_ids=inputs, labels=label_ids, use_cache=False).loss
                loss.backward()
                optimizer.step()
                scheduler.step()
                losses.append(float(loss.detach()))
        directory.mkdir(parents=True, exist_ok=False)
        model.save_pretrained(directory)
        return {"seed": seed, "epochs": epochs, "steps": len(losses),
                "trainable_parameters": model.get_nb_trainable_parameters()[0],
                "mean_training_loss": sum(losses) / len(losses), "rank": 4, "alpha": 8,
                "learning_rate": 0.0001, "warmup_steps": warmup_steps,
                "quality_accepted": False, "base_comparison_required": True,
                "max_length": max_length, "targets": targets}
