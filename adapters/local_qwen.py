"""Explicit local Qwen inference. Output is untrusted pending wording, not approval."""
import os
from pathlib import Path
from time import perf_counter


def generate(model_directory, messages, *, adapter_directory=None, max_new_tokens=512):
    """CPU baseline with bounded prompt/generation and no model download/upload.

    The caller owns prompt construction, source validation and independent review.
    This returns raw text/observed inference metrics, never imports or sends a CV.
    """
    if (type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 2048 or
            not isinstance(messages, list) or not 1 <= len(messages) <= 10 or
            any(not isinstance(m, dict) or set(m) != {'role', 'content'} or
                m['role'] not in ('system', 'user', 'assistant') or
                not isinstance(m['content'], str) for m in messages) or
            sum(len(m['content']) for m in messages) > 30000):
        raise ValueError('Use bounded text chat messages and 1..2048 output tokens')
    model_path = Path(model_directory).resolve(strict=True)
    if not model_path.is_dir():
        raise ValueError('Use a local model directory')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(str(model_path), local_files_only=True,
                                                trust_remote_code=False, use_safetensors=True)
    if adapter_directory is not None:
        adapter_path = Path(adapter_directory).resolve(strict=True)
        if not (adapter_path/'adapter_model.safetensors').is_file():
            raise ValueError('Use a local safetensors LoRA adapter; pickle fallback is not accepted')
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(adapter_path), local_files_only=True)
    prompt = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                            enable_thinking=False, return_tensors='pt')
    if prompt.shape[-1]+max_new_tokens > 8192:
        raise ValueError('Prompt/output exceeds the 8192-token local pilot bound; no truncation')
    model.to('cpu')
    prompt = prompt.to('cpu')
    model.eval()
    started = perf_counter()
    with torch.no_grad():
        result = model.generate(input_ids=prompt, attention_mask=torch.ones_like(prompt),
            max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    elapsed = (perf_counter()-started)*1000
    output = result[0, prompt.shape[-1]:]
    return {'text': tokenizer.decode(output, skip_special_tokens=True),
            'input_tokens': int(prompt.shape[-1]), 'output_tokens': int(output.numel()),
            'generation_ms': elapsed, 'load_time_included': False, 'device': 'cpu',
            'review_required': True, 'semantic_truth_verified': False,
            'provider_calls': 0, 'sent': False, 'authority_granted': False}
