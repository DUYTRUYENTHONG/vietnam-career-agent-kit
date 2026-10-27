"""Deterministic host dispatch planning. No model calls or implicit fallback."""
from .contracts import ContractError, Outcome, choice, object_fields, strings, text, version

ROLES = {'planning', 'simple', 'routine', 'complex'}
DEFAULT_POLICY = {
    'planning': {'model': 'gpt-6-astra', 'effort': 'high'},
    'simple': {'model': 'gpt-5.6-luna', 'effort': 'low'},
    'routine': {'model': 'gpt-5.6-terra', 'effort': 'medium'},
    'complex': {'model': 'gpt-5.6-sol', 'effort': 'high'},
}
TOOL_TASKS = {'test', 'build', 'format', 'status', 'metrics'}
TASKS = TOOL_TASKS | {'planning', 'consolidated_review', 'coding', 'auth',
                      'data_migration', 'debugging', 'business'}


def route_task(packet):
    """Use caller-reported host inventory; selection never changes a running agent."""
    object_fields(packet, {'schema_version', 'owner_id', 'task_kind', 'risk', 'complexity'},
                  {'available_models', 'available_skill_names', 'skill_candidates',
                   'policy', 'previous_failure'}, 'routing packet')
    version(packet, 'routing packet')
    text(packet['owner_id'], 'owner_id')
    kind = choice(packet['task_kind'], TASKS, 'task_kind')
    risk = choice(packet['risk'], {'low', 'medium', 'high'}, 'risk')
    complexity = choice(packet['complexity'], {'simple', 'routine', 'complex'}, 'complexity')
    policy = packet.get('policy', DEFAULT_POLICY)
    object_fields(policy, ROLES, set(), 'routing policy')
    for role, selection in policy.items():
        object_fields(selection, {'model', 'effort'}, set(), 'policy.' + role)
        text(selection['model'], 'policy.' + role + '.model')
        text(selection['effort'], 'policy.' + role + '.effort')
    models = packet.get('available_models', {})
    if not isinstance(models, dict):
        raise ContractError('available_models: expected a model/effort object')
    for model, efforts in models.items():
        text(model, 'available_models key')
        strings(efforts, 'available_models.' + model)
    candidates = strings(packet.get('skill_candidates', []), 'skill_candidates')
    available = strings(packet.get('available_skill_names', []), 'available_skill_names')
    data = {'owner_id': packet['owner_id'], 'execution': None, 'model': None,
            'effort': None, 'skill': None, 'dispatch_required': False,
            'usage_cost_usd': None, 'inventory_basis': 'caller-reported host capabilities'}

    def blocked(reason):
        return Outcome('blocked', data, [reason])

    failure = packet.get('previous_failure')
    if failure is not None:
        object_fields(failure, {'kind', 'count', 'model'}, set(), 'previous_failure')
        choice(failure['kind'], {'credentials', 'infrastructure', 'code'}, 'previous_failure.kind')
        text(failure['model'], 'previous_failure.model')
        if type(failure['count']) is not int or failure['count'] < 1:
            return blocked('previous_failure.count must be a positive integer')
        if failure['kind'] != 'code':
            return blocked('Resolve ' + failure['kind'] + ' before retrying; no model escalation')
        if failure['count'] >= 2:
            return blocked('Retry budget exhausted; report the failure')
    if kind in TOOL_TASKS:
        if failure:
            return blocked('Use the tool error to diagnose the failure; no automatic model retry')
        return Outcome('ok', {**data, 'execution': 'tool'}, [])

    role = ('planning' if kind in {'planning', 'consolidated_review'} else
            'complex' if risk == 'high' or complexity == 'complex' or kind in {'auth', 'data_migration'} else
            'simple' if risk == 'low' and complexity == 'simple' else 'routine')
    if failure:
        if role != 'simple' or failure['model'] != policy['simple']['model']:
            return blocked('Only one failed simple code task may escalate to the configured complex route')
        role = 'complex'
    selection = policy[role]
    data.update(role=role, model=selection['model'], effort=selection['effort'])
    if selection['effort'] not in models.get(selection['model'], []):
        return blocked('Requested model/effort unavailable: ' + selection['model'] + '/' + selection['effort'] +
                       '; configure an explicit policy alternative, never silently substitute')
    skill = next((name for name in candidates if name in available), None)
    if skill is None:
        return blocked('No requested skill is available; discovery does not install a skill')
    data.update(execution='agent', skill=skill, dispatch_required=True,
                review_gate='early-risk-review' if risk == 'high' else 'feature-or-release')
    return Outcome('ok', data, [], 'Plan only; apply through an explicit supported host override.')
