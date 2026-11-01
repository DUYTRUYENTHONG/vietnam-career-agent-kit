"""Normalize an explicitly selected Codex exec JSONL export without chat payloads.

No host invocation, native session discovery, model calls or database access.
The supported shape is the documented fresh-thread `codex exec --json` stream.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .manifests import timestamp
from .performance import identifier

MAX_BYTES = 10_000_000
MAX_LINE_BYTES = 1_000_000
MAX_EVENTS = 20_000
MAX_TURNS = 1_000
USAGE_FIELDS = {
    'input_tokens': 'input_tokens', 'output_tokens': 'output_tokens',
    'cached_input_tokens': 'cached_input_tokens',
    'reasoning_output_tokens': 'reasoning_tokens',
}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are not supported')
        result[key] = value
    return result


def _constant(_value):
    raise ValueError('Non-finite JSON values are not supported')


def _usage(value):
    if value is None:
        value = {}
    if not isinstance(value, dict) or set(value) - USAGE_FIELDS.keys():
        raise ValueError('Unsupported Codex usage shape; cumulative counters are not imported')
    usage = {'kind': 'per_turn'}
    for original, normalized in USAGE_FIELDS.items():
        count = value.get(original)
        if count is not None and (type(count) is not int or not 0 <= count <= 10**12):
            raise ValueError('Usage requires bounded nonnegative integer tokens or null')
        usage[normalized] = count
    for subset, total in [('cached_input_tokens', 'input_tokens'), ('reasoning_tokens', 'output_tokens')]:
        if usage[subset] is not None and usage[total] is not None and usage[subset] > usage[total]:
            raise ValueError('Usage subset exceeds its reported total')
    return usage


def _turns(raw):
    """Validate the entire stream before creating any output."""
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('Select a nonempty export of at most 10 MB')
    try:
        # JSONL uses physical LF boundaries. Unicode separators can legally
        # occur inside JSON strings and must not split a message/tool record.
        lines = raw.decode('utf-8-sig').split('\n')
        if lines[-1] == '':
            lines.pop()
    except UnicodeError as error:
        raise ValueError('The export must be UTF-8 JSON Lines') from error
    if len(lines) > MAX_EVENTS:
        raise ValueError('Export exceeds the 20000-line bound')
    thread_hash, active, turns, seen_events = None, False, [], 0
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if len(line.encode('utf-8')) > MAX_LINE_BYTES:
            raise ValueError('Export line exceeds 1 MB')
        try:
            event = json.loads(line, object_pairs_hook=_object, parse_constant=_constant)
        except (ValueError, RecursionError) as error:
            raise ValueError(f'Invalid JSONL event at line {number}') from error
        if not isinstance(event, dict):
            raise ValueError('Each JSONL event must be an object')
        kind = event.get('type')
        if kind == 'thread.started':
            thread = event.get('thread_id')
            if seen_events or not isinstance(thread, str) or not 1 <= len(thread) <= 128:
                raise ValueError('Select one complete fresh-thread export, not concatenated/resumed streams')
            thread_hash = hashlib.sha256(thread.encode()).hexdigest()
        elif not thread_hash:
            raise ValueError('The export must begin with thread.started')
        elif kind == 'turn.started':
            if active:
                raise ValueError('Overlapping turns are not supported')
            active = True
        elif kind in ('turn.completed', 'turn.failed'):
            if not active:
                raise ValueError('Terminal event has no matching turn.started')
            turns.append({'ordinal': len(turns)+1, 'terminal_type': kind,
                'usage': _usage(event.get('usage'))})
            if len(turns) > MAX_TURNS:
                raise ValueError('Export exceeds the 1000-turn bound')
            active = False
        elif kind not in ('item.started', 'item.updated', 'item.completed', 'error'):
            raise ValueError('Unsupported event type; select documented codex exec JSONL')
        # Never retain item text, reasoning, commands, files, error text or tool results.
        seen_events += 1
    if active or not turns:
        raise ValueError('Export is incomplete or has no terminal turn; no measurements prepared')
    return thread_hash, turns


def normalize_export(input_path, output_dir, *, task_id, workload_id, phase,
                     observed_utc, model_id=None, effort=None):
    """Write sanitized source/observation pairs into one explicit new directory.

    `observed_utc` and any model/effort are caller metadata, not values inferred
    from file timestamps, prompts, a model alias or the currently running agent.
    Existing performance-record remains the separate opt-in storage operation.
    """
    for label, value in [('task_id', task_id), ('workload_id', workload_id), ('phase', phase)]:
        identifier(value, label)
    identifier(model_id, 'model_id', True)
    identifier(effort, 'effort', True)
    if model_id is None and effort is not None:
        raise ValueError('Unknown model cannot have an inferred effort')
    timestamp(observed_utc, 'observed_utc')
    selected, destination = Path(input_path), Path(output_dir).resolve()
    if destination.exists():
        raise ValueError('Output directory already exists; preserve it and reuse its observations')
    if not selected.is_file() or not 0 < selected.stat().st_size <= MAX_BYTES:
        raise ValueError('Select a nonempty export of at most 10 MB')
    with selected.open('rb') as stream:
        raw = stream.read(MAX_BYTES+1)
    thread_hash, turns = _turns(raw)
    raw_hash = hashlib.sha256(raw).hexdigest()
    files, observations = {}, []
    for turn in turns:
        stem = f"turn-{turn['ordinal']:04d}"
        proof_path = destination/(stem+'.source.json')
        proof = {'normalizer_format': '1.0', 'source_format': 'codex_exec_jsonl',
            'raw_export_sha256': raw_hash, 'thread_id_sha256': thread_hash,
            **turn, 'model_metadata_origin': 'unavailable' if model_id is None else
                'caller_supplied_not_provider_authenticated',
            'caller_metadata': {'model_id': model_id, 'effort': effort, 'observed_utc': observed_utc},
            'payload_policy': 'allowlisted usage only; chat/tool/error payloads omitted'}
        proof_bytes = (json.dumps(proof, ensure_ascii=False, indent=2)+'\n').encode('utf8')
        event = {'schema_version': '1.0',
            'event_id': f"codex-{thread_hash}-{turn['ordinal']}",
            'task_id': task_id, 'workload_id': workload_id, 'phase': phase,
            'provider_id': 'codex-cli', 'model_id': model_id, 'effort': effort,
            'measurement_scope': 'agent_turn', 'status': 'success' if
                turn['terminal_type'] == 'turn.completed' else 'failed',
            'accepted': False, 'observed_utc': observed_utc, 'duration_ms': None,
            'usage': turn['usage'], 'cost': None,
            'source': {'kind': 'host_export', 'path': str(proof_path),
                'sha256': hashlib.sha256(proof_bytes).hexdigest()}}
        path = destination/(stem+'.observation.json')
        files[proof_path] = proof_bytes
        files[path] = (json.dumps(event, ensure_ascii=False, indent=2)+'\n').encode('utf8')
        observations.append(str(path))
    result = {'format_version': '1.0', 'raw_export_sha256': raw_hash,
        'observations': observations, 'database_opened': False, 'model_calls': 0,
        'acceptance': 'No quality acceptance inferred; review before performance-record',
        'duration_and_cost': 'Unreported; not derived from timestamps or prices'}
    # The manifest is written last. A write failure leaves an incomplete new
    # directory for inspection; nothing is automatically recorded or retried.
    destination.mkdir(parents=True, exist_ok=False)
    for path, content in files.items():
        with path.open('xb') as output:
            output.write(content)
    with (destination/'Manifest.json').open('x', encoding='utf8') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write('\n')
    return result
