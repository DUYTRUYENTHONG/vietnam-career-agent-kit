"""Durable, bounded first-layer review through the caller's existing agent host.

No model SDK, shell callback, scheduler, network request or human-label writer.
"""
import os
from . import cv_review_agents as agents, tailor_benchmark as b


def _child(folder, name):
    target = folder/name
    b.require(target.resolve().is_relative_to(folder.resolve()), 'Automation artifact escapes cycle')
    return target


def _write(path, value):
    with path.open('xb') as stream:
        stream.write(b.json_bytes(value)); stream.flush(); os.fsync(stream.fileno())


def start(root, requests, cycle, reuse=None):
    folder, manifest = b.verify_bundle(root, requests, 'cv_ai_review_requests')
    agents.assess(root, requests, [])  # Current source bytes must still match.
    rows = b.read_rows(folder/'requests.jsonl')
    b.require([r['role'] for r in rows] == list(agents.ROLES), 'Expected one ordered request per role')
    inputs = b.read_json(folder/'inputs.json')
    b.require(all(r['input_sha256'] == b.binding(inputs) for r in rows), 'Request inputs differ')
    cache = []
    cache_manifest = None
    if reuse:
        cache_folder, cache_manifest = b.verify_bundle(root, reuse, 'cv_ai_review_advisory_bundle')
        advisory = b.read_json(cache_folder/'advisory.json')
        b.require(advisory['requests_sha256'] == b.binding(manifest), 'Cached review uses different requests/prompts')
        cache = b.read_rows(cache_folder/'captured_model_reviews.jsonl')
        checked = agents.assess(root, requests, cache)
        b.require(not checked['missing_roles'] and b.binding(checked) == b.binding(advisory),
                  'Cached advisory is incomplete or differs from captured reviews')
    config = {'requests': requests, 'requests_sha256': b.binding(manifest),
        'request_hashes': {r['role']: b.binding(r) for r in rows},
        'cache_manifest_sha256': b.binding(cache_manifest) if cache_manifest else None,
        'max_host_handoffs': 3, 'runtime': 'existing-agent-host', 'automatic_retry': False}
    return b.bundle(root, cycle, {'config.json': b.json_bytes(config),
        'cached_responses.json': b.json_bytes(cache)}, {'schema_version': '1.0',
        'kind': 'cv_review_host_cycle', 'cached_responses_sha256': b.binding(cache),
        'model_service_added': False, 'application_authority': False})


def advance(root, cycle, response=None, issue=True):
    """Acknowledge one captured reply, then durably hand off at most one next role.

    Repeated calls with an outstanding handoff return waiting without replaying
    its messages. The host must reconcile the original call, not rerun it.
    """
    folder, cycle_manifest = b.verify_bundle(root, cycle, 'cv_review_host_cycle')
    config = b.read_json(folder/'config.json')
    requests_folder, manifest = b.verify_bundle(root, config['requests'], 'cv_ai_review_requests')
    b.require(b.binding(manifest) == config['requests_sha256'], 'Bound reviewer requests changed')
    request_rows = b.read_rows(requests_folder/'requests.jsonl')
    b.require([r['role'] for r in request_rows] == list(agents.ROLES) and all(
        b.binding(r) == config['request_hashes'][r['role']] for r in request_rows), 'Request identities changed')
    agents.assess(root, config['requests'], [])
    lock = _child(folder, 'write.lock')
    with lock.open('x', encoding='utf8'):
        pass
    try:
        cached = b.read_json(folder/'cached_responses.json')
        b.require(b.binding(cached) == cycle_manifest['cached_responses_sha256'], 'Cached response bytes changed')
        responses = list(cached)
        pending = None
        for index, request in enumerate(request_rows, 1):
            issued = _child(folder, f'issued-{index}.json'); saved = _child(folder, f'response-{index}.json')
            if saved.exists():
                b.require(issued.exists(), 'Response without a durable handoff')
            if issued.exists():
                envelope = b.read_json(issued)
                b.require(envelope == {'request_sha256': b.binding(request), 'role': request['role']},
                          'Issued handoff differs from bound request')
                b.require(not pending and len(responses) == index-1, 'Handoff sequence is inconsistent')
                if saved.exists():
                    captured = b.read_json(saved)
                    b.require(captured['response_sha256'] == b.binding(captured['response']) and
                        captured['response']['role'] == request['role'], 'Captured reply changed')
                    responses.append(captured['response'])
                else:
                    pending = request
        agents.assess(root, config['requests'], responses)
        b.require(not _child(folder, 'failed.json').exists(), 'Cycle stopped on invalid review; no automatic retry')
        if isinstance(response, dict):
            accepted = next((r for r in responses if r['role'] == response.get('role')), None)
            if accepted is not None:
                b.require(b.binding(response) == b.binding(accepted), 'Conflicting replay cannot overwrite an accepted reply')
                response = None  # Recover a lost acknowledgement without replaying a model call.
        if response is not None:
            b.require(pending is not None, 'No pending handoff can accept a reply')
            try:
                b.require(response.get('role') == pending['role'], 'Reply does not match pending role')
                agents.assess(root, config['requests'], responses+[response])
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                _write(_child(folder, 'failed.json'), {'reason': str(exc), 'rejected_response': response,
                                              'automatic_retry': False})
                raise
            _write(_child(folder, f'response-{len(responses)+1}.json'),
                   {'response': response, 'response_sha256': b.binding(response)})
            responses.append(response); pending = None
        if len(responses) == 3:
            result = agents.assess(root, config['requests'], responses)
            if _child(folder, 'advisory').exists():
                target, _ = b.verify_bundle(root, cycle+'/advisory', 'cv_ai_review_advisory_bundle')
                b.require(b.binding(b.read_json(target/'advisory.json')) == b.binding(result), 'Saved advisory changed')
            else:
                agents.collect(root, config['requests'], responses, cycle+'/advisory')
            return {'status': 'complete', 'advisory': cycle+'/advisory/advisory.json',
                    'cached_roles': len(cached), 'human_resolution_required': True,
                    'human_gold_created': False, 'application_authority': False}
        if pending:
            return {'status': 'waiting_for_original_reply', 'role': pending['role'],
                    'request_sha256': b.binding(pending), 'reissue_permitted': False}
        if not issue:
            return {'status': 'ready', 'next_role': agents.ROLES[len(responses)]}
        request = request_rows[len(responses)]
        _write(_child(folder, f'issued-{len(responses)+1}.json'),
               {'request_sha256': b.binding(request), 'role': request['role']})
        return {'status': 'host_review_required', 'request': request,
                'runtime': 'existing-agent-host', 'automatic_retry': False}
    finally:
        lock.unlink()


def run_with_host(root, cycle, respond):
    """Optional in-process adapter: trusted host callback, at most three new calls.

    An exception leaves the role issued, so a later invocation cannot call it
    again automatically. Callback is supplied by the host, never loaded from data.
    """
    outcome = advance(root, cycle)
    while outcome['status'] == 'host_review_required':
        response = respond(outcome['request'])
        outcome = advance(root, cycle, response)
    return outcome
