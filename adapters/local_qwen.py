"""Explicit local Qwen inference. Output is untrusted pending wording, not approval."""
import os
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from adapters.local_model_preflight import preflight_adapter


def generate(model_directory, messages, *, adapter_directory=None, max_new_tokens=512):
    """CPU baseline with bounded prompt/generation and no model download/upload.

    The caller owns prompt construction, source validation and independent review.
    This returns raw text/observed inference metrics, never imports or sends a CV.
    """
    with closing(generate_many(model_directory, [messages],
            adapter_directory=adapter_directory, max_new_tokens=max_new_tokens)) as rows:
        return next(rows)


def generate_many(model_directory, message_batches, *, adapter_directory=None, max_new_tokens=512):
    """Yield 1..50 independent CPU generations with one model load per iterator.

    Call close() (or use contextlib.closing) if abandoning this iterator early.
    Prompts are frozen and validated before SDK import. No chat history or KV cache
    is passed between calls. Model-load timing includes SDK import and setup;
    only the first output records it, subsequent outputs use None, not invented 0.
    """
    if not isinstance(message_batches, list) or not 1 <= len(message_batches) <= 50:
        raise ValueError('Use 1..50 bounded chat prompts')
    batches = deepcopy(message_batches)
    for messages in batches:
        _validate_messages(messages, max_new_tokens)
    model_path = Path(model_directory).resolve(strict=True)
    if not model_path.is_dir():
        raise ValueError('Use a local model directory')
    adapter_path = (preflight_adapter(model_path, adapter_directory)
                    if adapter_directory is not None else None)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    load_started = perf_counter()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(str(model_path), local_files_only=True,
                                                trust_remote_code=False, use_safetensors=True)
    try:
        if adapter_path is not None:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, str(adapter_path), local_files_only=True)
        model.to('cpu')
        model.eval()
        load_ms = (perf_counter()-load_started)*1000
        for index, messages in enumerate(batches):
            prompt = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                    enable_thinking=False, return_tensors='pt')
            if prompt.shape[-1]+max_new_tokens > 8192:
                raise ValueError('Prompt/output exceeds the 8192-token local pilot bound; no truncation')
            prompt = prompt.to('cpu')
            started = perf_counter()
            with torch.no_grad():
                result = model.generate(input_ids=prompt, attention_mask=torch.ones_like(prompt),
                    max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tokenizer.eos_token_id)
            elapsed = (perf_counter()-started)*1000
            output = result[0, prompt.shape[-1]:]
            yield {'text': tokenizer.decode(output, skip_special_tokens=True),
                'input_tokens': int(prompt.shape[-1]), 'output_tokens': int(output.numel()),
                'generation_ms': elapsed, 'load_time_included': False, 'device': 'cpu',
                'model_load_ms': load_ms if index == 0 else None,
                'review_required': True, 'semantic_truth_verified': False,
                'provider_calls': 0, 'sent': False, 'authority_granted': False}
    finally:
        # Release this iterator's references before another variant is loaded.
        del model, tokenizer


def _validate_messages(messages, max_new_tokens):
    if (type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 2048 or
            not isinstance(messages, list) or not 1 <= len(messages) <= 10 or
            any(not isinstance(m, dict) or set(m) != {'role', 'content'} or
                m['role'] not in ('system', 'user', 'assistant') or
                not isinstance(m['content'], str) for m in messages) or
            sum(len(m['content']) for m in messages) > 30000):
        raise ValueError('Use bounded text chat messages and 1..2048 output tokens')
