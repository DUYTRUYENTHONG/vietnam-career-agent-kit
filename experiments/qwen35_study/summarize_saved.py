"""Recompute descriptive historical scores; never label these sealed test results."""
import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path


def correct(row):
    pred = row.get('prediction') or {}
    return int(not row.get('error') and pred.get('label') == row['gold']['label']
               and set(pred.get('fact_ids', [])) == set(row['gold']['fact_ids']))


def indexed(rows):
    result = {(r['case'], r['requirement_id']): r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate evaluation identity')
    return result


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    mid = (k / n + z*z / (2*n)) / (1 + z*z/n)
    radius = z * math.sqrt(k/n*(1-k/n)/n + z*z/(4*n*n)) / (1+z*z/n)
    return [mid-radius, mid+radius]


def paired(base, system, draws=10000, seed=20261107):
    b, s = indexed(base), indexed(system)
    if set(b) != set(s) or any(b[k]['gold'] != s[k]['gold'] for k in b):
        raise ValueError('Mismatched evaluation inputs/gold')
    groups = defaultdict(list)
    for k in sorted(b):
        groups[k[0]].append(correct(s[k]) - correct(b[k]))
    values = list(groups.values())
    rng = random.Random(seed)
    samples = []
    for _ in range(draws):
        picked = rng.choices(values, k=len(values))
        samples.append(sum(sum(g) for g in picked) / sum(len(g) for g in picked))
    samples.sort()
    return {'delta': sum(sum(g) for g in values)/len(base),
            'cluster_percentile_95_ci': [samples[int(.025*draws)], samples[int(.975*draws)-1]],
            'clusters': len(values), 'cluster_unit': 'synthetic case; profile independence assumed',
            'draws': draws, 'seed': seed}


def summary(rows):
    indexed(rows)
    n = len(rows)
    negative = [r for r in rows if r['gold']['label'] in ('unknown', 'contradicted')]
    false = sum((r.get('prediction') or {}).get('label') in ('direct', 'partial') for r in negative)
    return {'n': n, 'joint_correct': sum(map(correct, rows)),
            'accuracy': sum(map(correct, rows))/n, 'false_support': false,
            'false_support_denominator': len(negative),
            'false_support_wilson_95_ci': wilson(false, len(negative)),
            'false_support_ci_scope': 'row-level descriptive; correlated cases limit interpretation',
            'invalid': sum(not r.get('prediction') or bool(r.get('error')) for r in rows)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    files = {'BM25': 'results/challenge64/bm25.json',
             'TF-IDF supervised': 'results/challenge64/supervised-text.json',
             'Frozen embedding verifier': 'verifier/challenge64.json',
             '4B zero-shot Q4': 'results/challenge64/qwen35-4b-q4.json',
             '4B four-shot Q4': 'results/challenge64/qwen35-4b-q4-fourshot.json'}
    records = {name: json.loads((a.bundle/path).read_text()) for name, path in files.items()}
    base = records['4B zero-shot Q4']['rows']
    output = {'scope': 'historical synthetic regression; no new inference or independent human test',
              'source_sha256': {path: hashlib.sha256((a.bundle/path).read_bytes()).hexdigest()
                                for path in files.values()}, 'systems': {}}
    for name, record in records.items():
        output['systems'][name] = {**summary(record['rows']),
                                  **paired(base, record['rows'])}
    with a.output.open('x', encoding='utf8') as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
    table = ['| System | Correct /64 | Delta pp | Case-cluster 95% CI pp | False support /32 |',
             '|---|---:|---:|---:|---:|']
    for name, v in output['systems'].items():
        low, high = [100*x for x in v['cluster_percentile_95_ci']]
        table.append(f"| {name} | {v['joint_correct']}/64 | {100*v['delta']:.3f} | [{low:.2f}, {high:.2f}] | {v['false_support']}/32 |")
    a.output.with_suffix('.md').write_text('\n'.join(table)+'\n', encoding='utf8')


if __name__ == '__main__':
    main()
