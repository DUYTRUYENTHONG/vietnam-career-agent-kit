#!/usr/bin/env python3
"""Fictional, local retrieval benchmark including source/profile validation. No API."""
import argparse
import json
from pathlib import Path
import platform
import sqlite3
from statistics import median
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.career_memory import retrieve, evaluate
from core.execution import Executor
from scripts.demo_slice1 import demo


def benchmark(fact_count=1000, samples=10):
    if type(fact_count) is not int or not 10 <= fact_count <= 2000 or type(samples) is not int or not 2 <= samples <= 100:
        raise ValueError('Use 10..2000 facts and 2..100 samples')
    with tempfile.TemporaryDirectory(prefix='fictional-memory-') as tmp:
        directory = Path(tmp)/'private'; demo(directory)
        work = Executor(directory)
        profile = work.confirmed_profile()['profile']
        lines = ['Fictional automation evidence item '+str(i)+': measured prototype task code'+str(i)+'.' for i in range(fact_count)]
        lines[0] = 'Built a fictional tiếp thị dashboard prototype with SQL; no production deployment.'
        source = work.atomic_text('benchmark-evidence.md', '\n'.join(lines))
        work.import_cv(source, 'BENCH')
        profile['facts'] = [{'id': 'B'+str(i), 'field': 'capability', 'value': 'benchmark-'+str(i),
            'claim': line, 'quote': line, 'source_id': 'BENCH', 'locator': 'line '+str(i+1), 'status': 'confirmed'}
            for i, line in enumerate(lines)]
        fingerprint = work.import_profile(profile).data['fingerprint']
        # Explicitly fictional only, never a helper for approving real candidate evidence.
        work.confirm_profile(fingerprint, work.atomic_text('fictional-benchmark-review.txt', 'CONFIRM PROFILE '+fingerprint))
        times = []
        for _ in range(samples):
            start = time.perf_counter_ns()
            result = retrieve(work, 'tiếp thị SQL', limit=1)
            times.append((time.perf_counter_ns()-start)/1_000_000)
            if result.outcome != 'ok' or result.data['facts'][0]['id'] != 'B0':
                raise RuntimeError('Fictional multilingual gold query failed')
        evaluation = evaluate(work, {'schema_version': '1.0', 'limit': 1, 'cases': [
            {'id': 'vietnamese', 'query': 'tiếp thị SQL', 'expected_fact_ids': ['B0']},
            {'id': 'diacritics', 'query': 'tiep thi', 'expected_fact_ids': ['B0']},
            {'id': 'specific', 'query': 'code7', 'expected_fact_ids': ['B7']},
            {'id': 'missing', 'query': 'unconfirmedKubernetes', 'expected_fact_ids': []}]}).data
        return {'fictional_only': True, 'fact_count': fact_count, 'samples': samples,
            'python': platform.python_version(), 'os': platform.system(), 'sqlite': sqlite3.sqlite_version,
            'wall_duration_ms': {'p50': round(median(times), 3), 'max': round(max(times), 3)},
            'evaluation': evaluation, 'provider_calls': 0, 'model_tokens': None,
            'scope': 'Synthetic single-candidate corpus. Includes current source/profile validation and new in-memory index each call. '
                     'Four authored query labels, not real CV quality or production throughput. No baseline latency speedup claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=int, default=1000)
    parser.add_argument('--samples', type=int, default=10)
    args = parser.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf8')
    print(json.dumps(benchmark(args.facts, args.samples), ensure_ascii=False, indent=2))
