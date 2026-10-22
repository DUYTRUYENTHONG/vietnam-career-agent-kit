#!/usr/bin/env python3
"""Equivalent review-ready wording handoff, two CLI starts versus one. No rendering/model/network."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.ledger import canonical_hash
from scripts.demo_wording import seed


def benchmark(samples):
    results = {'separate': [], 'combined': []}
    fingerprints = {}
    for sample in range(samples):
        for mode in (['separate', 'combined'] if sample % 2 == 0 else ['combined', 'separate']):
            for candidate in ['data', 'technical', 'commercial']:
                with tempfile.TemporaryDirectory(prefix='career-wording-benchmark-') as temp:
                    work, model = seed(Path(temp)/'private', candidate)
                    path = work.atomic_text('inputs/model.json', json.dumps(model))
                    def cli(*args):
                        result = subprocess.run([sys.executable, str(ROOT/'scripts/kit.py'),
                            '--data-dir', str(work.data_dir), *args], capture_output=True,
                            text=True, encoding='utf8', timeout=30, check=True)
                        return json.loads(result.stdout)['data']
                    started = time.perf_counter_ns()
                    args = ['import-wording', '--job-id', '1', '--file', str(path)]
                    if mode == 'combined':
                        packet = cli(*args, '--include-review-packet')['review_packet']
                    else:
                        cli(*args)
                        packet = cli('wording-packet', '--job-id', '1')
                    elapsed = (time.perf_counter_ns()-started)/1_000_000
                    digest = canonical_hash(packet)
                    if candidate in fingerprints and fingerprints[candidate] != digest:
                        raise AssertionError('Equivalent packet fingerprints differ')
                    fingerprints[candidate] = digest
                    assert packet['reviewed'] is False
                    with work._db() as db:
                        assert db.execute('SELECT count(*) FROM document_sets').fetchone()[0] == 0
                    results[mode].append({'sample': sample+1, 'candidate': candidate,
                        'duration_ms': round(elapsed, 3), 'packet_digest': digest})
    report = {'schema_version': '1.0', 'fixture_version': 'wording-1', 'fictional_only': True,
        'samples_per_candidate': samples, 'candidates': 3, 'python': sys.version.split()[0],
        'scope': 'Equivalent deterministic import plus review packet. Setup, semantic review, rendering, human wait and application execution excluded.',
        'network_calls': 0, 'model_calls_in_script': 0, 'host_tokens': None, 'results': {}}
    for mode, values in results.items():
        durations = [value['duration_ms'] for value in values]
        report['results'][mode] = {'cli_starts_per_packet': 2 if mode == 'separate' else 1,
            'median_ms': round(statistics.median(durations), 3),
            'range_ms': [min(durations), max(durations)], 'samples': values}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, choices=range(1, 21), default=7)
    print(json.dumps(benchmark(parser.parse_args().samples), indent=2))
