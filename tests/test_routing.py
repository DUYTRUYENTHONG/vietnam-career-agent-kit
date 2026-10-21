"""Fictional host inventories; no paid models or native dispatch."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.contracts import ContractError
from core.routing import DEFAULT_POLICY, route_task


class RoutingTests(unittest.TestCase):
    def packet(self, **changes):
        packet = {'schema_version': '1.0', 'owner_id': 'existing-owner', 'task_kind': 'coding',
                  'risk': 'low', 'complexity': 'simple',
                  'available_models': {v['model']: [v['effort']] for v in DEFAULT_POLICY.values()},
                  'available_skill_names': ['fictional-skill'], 'skill_candidates': ['fictional-skill']}
        return {**packet, **changes}

    def test_tool_tasks_need_no_model_inventory_or_skill_and_preserve_owner(self):
        for kind in ['test', 'build', 'format', 'status', 'metrics']:
            result = route_task({'schema_version': '1.0', 'owner_id': 'existing-owner',
                                 'task_kind': kind, 'risk': 'low', 'complexity': 'simple'})
            self.assertEqual('ok', result.outcome)
            self.assertEqual('tool', result.data['execution'])
            self.assertIsNone(result.data['model'])
            self.assertEqual('existing-owner', result.data['owner_id'])
            self.assertFalse(result.data['dispatch_required'])

    def test_deterministic_policy_roles_and_single_selected_skill(self):
        cases = [('planning', 'low', 'simple', 'planning'),
                 ('consolidated_review', 'low', 'simple', 'planning'),
                 ('coding', 'low', 'simple', 'simple'), ('coding', 'medium', 'routine', 'routine'),
                 ('auth', 'low', 'simple', 'complex'), ('data_migration', 'low', 'simple', 'complex'),
                 ('debugging', 'high', 'simple', 'complex'), ('coding', 'low', 'complex', 'complex')]
        for kind, risk, complexity, role in cases:
            with self.subTest(kind=kind, risk=risk, complexity=complexity):
                result = route_task(self.packet(task_kind=kind, risk=risk, complexity=complexity))
                self.assertEqual('ok', result.outcome)
                self.assertEqual(DEFAULT_POLICY[role]['model'], result.data['model'])
                self.assertEqual('fictional-skill', result.data['skill'])
                self.assertIsNone(result.data['usage_cost_usd'])

    def test_missing_model_effort_skill_and_empty_inventory_never_fall_back(self):
        for changes in [{'available_models': {}}, {'available_models': {'gpt-5.6-luna': ['high']}},
                        {'available_skill_names': []}, {'skill_candidates': []}]:
            result = route_task(self.packet(**changes))
            self.assertEqual('blocked', result.outcome)
            self.assertFalse(result.data['dispatch_required'])

    def test_explicit_policy_can_bind_a_different_host_without_mutation(self):
        policy = copy.deepcopy(DEFAULT_POLICY)
        policy['simple'] = {'model': 'fictional-small', 'effort': 'low'}
        packet = self.packet(policy=policy, available_models={'fictional-small': ['low']})
        before = copy.deepcopy(packet)
        result = route_task(packet)
        self.assertEqual('ok', result.outcome)
        self.assertEqual('fictional-small', result.data['model'])
        self.assertEqual(before, packet)
        self.assertEqual('gpt-5.6-luna', DEFAULT_POLICY['simple']['model'])

    def test_one_simple_code_escalation_and_infrastructure_stop(self):
        failure = {'kind': 'code', 'count': 1, 'model': 'gpt-5.6-luna'}
        result = route_task(self.packet(previous_failure=failure))
        self.assertEqual('gpt-5.6-sol', result.data['model'])
        for change in [{'kind': 'credentials'}, {'kind': 'infrastructure'}, {'count': 2},
                       {'model': 'other'}, {'count': True}]:
            result = route_task(self.packet(previous_failure={**failure, **change}))
            self.assertEqual('blocked', result.outcome)
            self.assertFalse(result.data['dispatch_required'])
        self.assertEqual('blocked', route_task(self.packet(risk='high', previous_failure=failure)).outcome)

    def test_unknown_metadata_and_blank_owner_are_rejected(self):
        for changes in [{'owner_id': ''}, {'task_kind': 'classify-with-llm'}, {'risk': 'invented'},
                        {'unexpected': True}, {'schema_version': '2.0'}]:
            with self.assertRaises(ContractError):
                route_task(self.packet(**changes))

    def test_optional_shapes_remain_strict_even_for_tool_routes(self):
        for changes in [{'available_models': None}, {'available_models': {'some-model': 'high'}},
                        {'policy': {}}, {'skill_candidates': [1]},
                        {'available_skill_names': ['repeated', 'repeated']}]:
            with self.assertRaises(ContractError):
                route_task(self.packet(task_kind='metrics', **changes))

    def test_real_cli_requires_no_private_workspace_and_emits_structured_failures(self):
        cli = Path(__file__).resolve().parents[1] / 'scripts/kit.py'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'packet.json'
            for packet, code in [(self.packet(), 0), (self.packet(available_models={}), 2),
                                 (self.packet(owner_id=''), 2)]:
                path.write_text(json.dumps(packet), encoding='utf8')
                result = subprocess.run([sys.executable, str(cli), 'route-task', '--packet', str(path)],
                                        capture_output=True, encoding='utf8', timeout=15)
                self.assertEqual(code, result.returncode, result.stdout + result.stderr)
                self.assertIn(json.loads(result.stdout)['outcome'], ['ok', 'blocked', 'needs_input'])
            self.assertEqual(['packet.json'], [p.name for p in Path(temp).iterdir()])
