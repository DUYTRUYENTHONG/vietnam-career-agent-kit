"""Read-only connectivity diagnostic for caller-declared dataset groups.

Group completeness and semantic identity are caller review obligations. No
dataset, source, approval or split is inferred, edited or certified here.
"""
import hashlib
import json
import unicodedata

MAX_ROWS = 10_000
MAX_GROUPS = 64
PARTITIONS = {'train', 'development', 'test'}


def _label(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 256 or
            value != ' '.join(unicodedata.normalize('NFC', value).split())):
        raise ValueError('Labels must be normalized nonempty strings of at most 256 characters')
    return value


def audit_splits(document):
    """Find transitive cross-partition connections without interpreting labels."""
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'rows'} or
            document['schema_version'] != '1.0'):
        raise ValueError('Expected explicit split-group contract 1.0')
    rows = document['rows']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError('Select 1..10,000 group observations')
    validated, ids = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', 'partition', 'groups'}:
            raise ValueError('Expected id, partition and groups only')
        rid = _label(row['id'])
        if rid in ids:
            raise ValueError('Duplicate row ID')
        ids.add(rid)
        partition = row['partition']
        if not isinstance(partition, str) or partition not in PARTITIONS:
            raise ValueError('Partition must be train, development or test')
        groups = row['groups']
        if not isinstance(groups, list) or not 1 <= len(groups) <= MAX_GROUPS:
            raise ValueError('Each row needs 1..64 explicit groups')
        labels = [_label(g) for g in groups]
        if len(set(labels)) != len(labels):
            raise ValueError('Duplicate group within row')
        validated.append((rid, partition, labels))

    # Iterative path compression avoids recursion limits on long bridge chains.
    parent = list(range(len(validated)))
    size = [1] * len(parent)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owners = {}
    for i, (_, _, groups) in enumerate(validated):
        for group in groups:
            other = owners.setdefault(group, i)
            a, b = find(i), find(other)
            if a != b:
                if size[a] < size[b]:
                    a, b = b, a
                parent[b] = a
                size[a] += size[b]

    components = {}
    for i, (rid, partition, _) in enumerate(validated):
        component = components.setdefault(find(i), {'row_ids': [], 'partitions': set()})
        component['row_ids'].append(rid)
        component['partitions'].add(partition)
    conflicts = sorted(({'row_ids': sorted(c['row_ids']), 'partitions': sorted(c['partitions'])}
                        for c in components.values() if len(c['partitions']) > 1),
                       key=lambda c: c['row_ids'])
    digest = hashlib.sha256(json.dumps(document, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode('utf8')).hexdigest()
    return {'schema_version': '1.0', 'status': 'review_required', 'row_count': len(rows),
            'component_count': len(components), 'cross_partition_component_count': len(conflicts),
            'cross_partition_components': conflicts, 'input_sha256': digest,
            'split_independence_verified': False, 'training_authorized': False,
            'training_performed': False, 'provider_calls': 0,
            'scope': 'Caller-declared group connectivity only. Missing or incorrect groups can '
                     'hide leakage. No automatic split, source/label review, training or promotion.'}
