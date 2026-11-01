"""Offline declared-base checks before optional local inference dependencies.

These checks bind local metadata, not publisher authenticity, tensor compatibility,
training quality or permission to use generated CV wording.
"""
import hashlib
import json
from pathlib import Path
import re


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate model metadata key')
        value[key] = item
    return value


def _json(path):
    try:
        with path.open('rb') as stream:
            raw = stream.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('Model metadata exceeds 1 MiB')
        value = json.loads(raw.decode('utf8'), object_pairs_hook=_object)
        if not isinstance(value, dict):
            raise ValueError('Model metadata must be an object')
        return value
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError('Missing or invalid local model metadata') from error


def _hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def preflight_adapter(model_directory, adapter_directory):
    """Require an exact local base path or a fully hash-checked download manifest.

    No imports of Torch/Transformers/PEFT, network calls or filesystem writes.
    A moved local base is not silently treated as its historical path alias.
    The paired runner retains its stronger exact training/export byte checks.
    """
    try:
        base = Path(model_directory).resolve(strict=True)
        adapter = Path(adapter_directory).resolve(strict=True)
    except OSError as error:
        raise ValueError('Select existing local base and adapter directories') from error
    if (not base.is_dir() or not adapter.is_dir() or
            not (base/'config.json').is_file() or
            not (adapter/'adapter_model.safetensors').is_file()):
        raise ValueError('Local base config and adapter safetensors are required')
    config = _json(adapter/'adapter_config.json')
    reference = config.get('base_model_name_or_path')
    if (config.get('peft_type') != 'LORA' or config.get('task_type') != 'CAUSAL_LM' or
            not isinstance(reference, str) or not reference.strip()):
        raise ValueError('A causal LoRA adapter with a declared base is required')
    declared = Path(reference)
    if declared.is_absolute():
        if declared.resolve() != base:
            raise ValueError('Adapter declared local base differs from selected base')
        return adapter
    try:
        manifest = _json(base/'download-manifest.json')
    except ValueError as error:
        raise ValueError('Adapter base needs a matching local download manifest') from error
    if manifest.get('model') != reference:
        raise ValueError('Adapter base differs from the local download manifest')
    revision = manifest.get('revision')
    if not isinstance(revision, str) or not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('Local base manifest requires a pinned revision')
    if config.get('revision') not in (None, revision):
        raise ValueError('Adapter revision differs from the pinned base revision')
    files = manifest.get('files')
    if (not isinstance(files, dict) or not 1 <= len(files) <= 1000 or
            'config.json' not in files or
            not any(name.endswith('.safetensors') for name in files)):
        raise ValueError('Local base manifest must bind config and safetensors')
    for name, expected in files.items():
        if (not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..') or
                not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected)):
            raise ValueError('Invalid base manifest file identity')
        path = base/name
        if not path.is_file() or path.resolve().parent != base or _hash(path) != expected:
            raise ValueError('Local base manifest file hash differs or file is missing')
    # Transformers prefers a monolithic checkpoint over the shard index. Bind
    # every loader-relevant file, not just whichever files the manifest lists.
    for path in base.iterdir():
        if (path.name != 'download-manifest.json' and path.is_file() and
                path.suffix.lower() in ('.json', '.safetensors', '.txt', '.jinja') and
                path.name not in files):
            raise ValueError('Unlisted base checkpoint or tokenizer metadata')
    if 'model.safetensors' not in files:
        index_name = 'model.safetensors.index.json'
        if index_name not in files:
            raise ValueError('Unsupported base checkpoint layout')
        index = _json(base/index_name)
        mapping = index.get('weight_map')
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError('Base shard index must declare a weight map')
        for shard in mapping.values():
            if (not isinstance(shard, str) or not shard.endswith('.safetensors') or
                    not re.fullmatch(r'[A-Za-z0-9_.-]+', shard) or shard not in files):
                raise ValueError('Base shard index references an unverified shard')
    return adapter
