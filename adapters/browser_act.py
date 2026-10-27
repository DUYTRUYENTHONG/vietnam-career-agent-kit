"""Offline BrowserAct session plans for already-issued execution requests.

No browser, subprocess, installer, approval proof or receipt is created here.
The host must recheck authority immediately before acting on a plan.
"""
import hashlib
import json
import re

from core.contracts import ContractError, Outcome
from core.workflow import WorkflowError


def plan_session(work, run_id, request_id, browser_id):
    """Reuse canonical authorization; expose no candidate values or write commands."""
    if not isinstance(browser_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', browser_id):
        raise ContractError('browser_id must be a configured BrowserAct identifier, not a command or URL')
    with work._db() as db:
        row = db.execute(
            'SELECT r.owner,r.payload AS run_payload,a.payload AS request_payload '
            'FROM execution_runs r JOIN execution_actions a ON a.run_id=r.id '
            'WHERE r.id=? AND a.id=? AND a.receipt IS NULL', (run_id, request_id)).fetchone()
    if row is None or row['owner'] != work.actor:
        raise WorkflowError('blocked', 'No pending request owned by this coordinator')
    request = json.loads(row['request_payload'])
    if request['bridge_id'] != 'browser-act':
        raise WorkflowError('blocked', 'Review a manifest binding browser-act before changing browser bridges')
    parallel = 'lanes' in json.loads(row['run_payload'])
    check = 'check-parallel-action' if parallel else 'check-action'
    if parallel:
        work.check_parallel_action(run_id, request_id)
    else:
        work.check_action(run_id, request_id)
    identity = json.dumps([work.actor, run_id, request['job_id']], separators=(',', ':'))
    session = 'vca-' + hashlib.sha256(identity.encode()).hexdigest()[:24]
    binding = 'browser-act:' + session
    if request['binding_id'] is not None and request['binding_id'] != binding:
        raise WorkflowError('blocked', 'Observed application binding differs from this BrowserAct session')
    action = request['action']
    prefix = ['browser-act', '--session', session, '--no-auto-dialog']
    commands = []
    if action == 'inspect':
        commands.append(prefix + ['browser', 'open', browser_id, request['destination']])
    if action in {'inspect', 'review', 'verify'}:
        commands.append(prefix + ['state'])
    data = {
        'plan_version': '1.0', 'run_id': run_id, 'request_id': request_id,
        'job_id': request['job_id'], 'action': action, 'bridge_id': 'browser-act',
        'session': session, 'binding_id': binding, 'commands': commands,
        'preflight': [check, '--run-id', run_id, '--request-id', request_id],
        'browser_executed': False, 'submission_driver_implemented': False,
        'compatibility': 'Instruction-only; offline planning contract tested',
    }
    issues = ['Host must verify session ownership, actual URL/employer/requisition and its own permissions. '
              'Recheck the listed preflight immediately before acting; this plan is not an execution token.']
    if not commands:
        issues.append('BrowserAct fill/upload/submit translation is not implemented. Use an independently '
                      'tested host bridge or hand off this pending request; do not fabricate a receipt or replay it.')
    return Outcome('ok' if commands else 'manual_required', data, issues)
