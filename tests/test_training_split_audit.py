"""Fictional explicit-group diagnostics; no candidate data or models."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.training_split_audit import audit_splits


def sample():
    return {'schema_version': '1.0', 'rows': [
        {'id': 'A', 'partition': 'train', 'groups': ['employer:one', 'project:shared']},
        {'id': 'B', 'partition': 'development', 'groups': ['employer:two', 'project:shared']},
        {'id': 'C', 'partition': 'test', 'groups': ['employer:two']},
        {'id': 'D', 'partition': 'test', 'groups': ['employer:three']}]}


class SplitAuditTests(unittest.TestCase):
    def test_transitive_connection_not_just_direct_overlap(self):
        data = sample()
        original = copy.deepcopy(data)
        report = audit_splits(data)
        self.assertEqual(1, report['cross_partition_component_count'])
        self.assertEqual(['A', 'B', 'C'], report['cross_partition_components'][0]['row_ids'])
        self.assertEqual(['development', 'test', 'train'],
                         report['cross_partition_components'][0]['partitions'])
        self.assertEqual(data, original)
        self.assertFalse(report['training_authorized'])
        self.assertNotIn('project:shared', json.dumps(report))

    def test_disjoint_groups_are_not_an_independence_certificate(self):
        data = sample()
        for r in data['rows']:
            r['groups'] = ['own:' + r['id']]
        report = audit_splits(data)
        self.assertEqual(0, report['cross_partition_component_count'])
        self.assertEqual('review_required', report['status'])
        self.assertFalse(report['split_independence_verified'])

    def test_duplicate_ids_missing_groups_unknown_partition_and_extra_keys_rejected(self):
        variants = []
        for key, value in [('id', 'B'), ('groups', []), ('groups', ['x', 'x']),
                           ('partition', 'unknown'), ('groups', ['  x']), ('text', 'private')]:
            data = sample()
            data['rows'][0][key] = value
            variants.append(data)
        variants.extend([{'schema_version': '2.0', 'rows': []},
                         {'schema_version': '1.0', 'rows': []}, None])
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValueError):
                audit_splits(data)

    def test_row_and_group_bounds(self):
        data = sample()
        data['rows'] = data['rows'] * 2501
        with self.assertRaises(ValueError):
            audit_splits(data)

    def test_long_transitive_chain_and_deterministic_order(self):
        rows = [{'id': 'R' + str(n), 'partition': 'train' if n < 1999 else 'test',
                 'groups': ['edge:' + str(n), 'edge:' + str(n + 1)]}
                for n in range(2000)]
        report = audit_splits({'schema_version': '1.0', 'rows': rows})
        self.assertEqual(1, report['component_count'])
        self.assertEqual(2000, len(report['cross_partition_components'][0]['row_ids']))
        reverse = audit_splits({'schema_version': '1.0', 'rows': list(reversed(rows))})
        self.assertEqual(report['cross_partition_components'], reverse['cross_partition_components'])
        data = sample()
        data['rows'][0]['groups'] = ['x' + str(n) for n in range(65)]
        with self.assertRaises(ValueError):
            audit_splits(data)

    def test_cli_binds_input_and_leaves_directory_unchanged(self):
        import hashlib
        script = Path(__file__).resolve().parents[1] / 'scripts/audit_training_splits.py'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'groups.json'
            path.write_text(json.dumps(sample()), encoding='utf8')
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(script), '--groups', str(path)],
                                    capture_output=True, text=True, encoding='utf8')
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(hashlib.sha256(before).hexdigest(),
                             json.loads(result.stdout)['input_file_sha256'])
            self.assertEqual([path], list(Path(directory).iterdir()))
            self.assertEqual(before, path.read_bytes())
            path.write_text('private malformed content', encoding='utf8')
            result = subprocess.run([sys.executable, str(script), '--groups', str(path)],
                                    capture_output=True, text=True, encoding='utf8')
            self.assertEqual(1, result.returncode)
            self.assertEqual('needs_input', json.loads(result.stdout)['status'])
            self.assertNotIn('private malformed', result.stdout + result.stderr)
            self.assertNotIn(directory, result.stdout + result.stderr)
