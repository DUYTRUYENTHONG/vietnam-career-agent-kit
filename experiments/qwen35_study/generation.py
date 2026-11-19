"""Identical one-attempt generation contract for all study systems."""
import time

from core.evidence_pairing import checked, messages, strict_json


def generate_row(model, tokenizer, torch, case, requirement, facts, gold):
    prompt = tokenizer.apply_chat_template(messages(requirement, facts),
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
    encoded = tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
    if encoded.input_ids.shape[1] > 2048:
        raise ValueError('Over-budget input; no truncation')
    torch.cuda.synchronize()
    started = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(**encoded, max_new_tokens=128,
            do_sample=False, use_cache=True, pad_token_id=tokenizer.eos_token_id)
    torch.cuda.synchronize()
    ms = (time.perf_counter() - started) * 1000
    suffix = generated[0, encoded.input_ids.shape[1]:]
    raw = tokenizer.decode(suffix, skip_special_tokens=True).strip()
    try:
        prediction = checked(strict_json(raw), facts)
        error = None
    except (ValueError, TypeError) as exc:
        prediction, error = None, str(exc)
    return {'case': case, 'requirement_id': requirement['id'], 'gold': gold,
        'prediction': prediction, 'error': error, 'raw': raw,
        'input_tokens': int(encoded.input_ids.shape[1]),
        'output_tokens': int(suffix.numel()), 'generation_ms': ms,
        'includes_loading_or_tokenization': False, 'attempts': 1}
