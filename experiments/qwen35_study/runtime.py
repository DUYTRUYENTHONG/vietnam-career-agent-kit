"""Shared text-only NF4 loading for matched study training and inference."""


def load_qwen35(directory):
    import torch
    from transformers import AutoTokenizer, BitsAndBytesConfig, Qwen3_5ForConditionalGeneration
    from peft import prepare_model_for_kbit_training
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required; no CPU fallback')
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    model = Qwen3_5ForConditionalGeneration.from_pretrained(directory,
        local_files_only=True, device_map={'': 0}, dtype=torch.float16,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,
            bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16))
    cfg = model.config.text_config
    if cfg.hidden_size != 2560 or cfg.num_hidden_layers != 32:
        raise ValueError('Expected Qwen3.5-4B architecture')
    # Apply identical normalization/casting to the clean and adapted systems.
    model = prepare_model_for_kbit_training(model)
    return tokenizer, model


def load_secondary(directory):
    """Native Qwen3 tokenizer, same NF4/FP16 compute and normalization policy."""
    import torch
    from transformers import AutoTokenizer, BitsAndBytesConfig, Qwen3ForCausalLM
    from peft import prepare_model_for_kbit_training
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required; no CPU fallback')
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    model = Qwen3ForCausalLM.from_pretrained(directory,
        local_files_only=True, device_map={'': 0}, dtype=torch.float16,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,
            bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16))
    cfg = model.config
    if cfg.model_type != 'qwen3' or cfg.hidden_size != 2560 or cfg.num_hidden_layers != 36:
        raise ValueError('Expected Qwen3-4B-Instruct-2507 architecture')
    model = prepare_model_for_kbit_training(model)
    return tokenizer, model
