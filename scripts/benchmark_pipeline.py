#!/usr/bin/env python3
"""Disposable fictional pipeline benchmark. No browser, models or real converter."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.execution import Executor
from scripts.demo_slice1 import demo


def seed(directory, jobs):
    demo(directory)
    work = Executor(directory)
    work.init()
    load = lambda name: json.loads((ROOT / 'examples/fictional' / name).read_text(encoding='utf8'))
    for number in range(2, jobs + 1):
        job = load('job.json')
        job.update(platform_job_id=f'fictional-{number}', req_id=f'FICT-{number}',
                   url=f'https://jobs.example.test/FICT-{number}')
        job_id = work.import_job(job).data['job']['id']
        work.assess(job_id, load('matrix.json'))
        work.prepare(job_id, load('plan.json'))
    return work


def measure(work, operation, samples):
    times, reads = [], []
    for _ in range(samples):
        with patch.object(work, 'job_document', wraps=work.job_document) as count:
            started = time.perf_counter()
            operation()
            times.append(round((time.perf_counter() - started) * 1000, 3))
            reads.append(count.call_count)
    return {'milliseconds': times, 'median_ms': round(statistics.median(times), 3),
            'job_document_reads': reads}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, choices=range(1, 101), default=100)
    parser.add_argument('--samples', type=int, choices=range(1, 21), default=5)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='career-kit-benchmark-') as temp:
        work = seed(Path(temp) / 'private', args.jobs)
        results = {'fictional_only': True, 'jobs': args.jobs, 'samples': args.samples,
                   'python': sys.version.split()[0],
                   'content_model': measure(work, lambda: work.content_model(1), args.samples),
                   'resume': measure(work, work.resume, args.samples)}
        if hasattr(work, 'tracker'):
            results['tracker'] = measure(work, work.tracker, args.samples)
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
