#!/usr/bin/env python3
"""Fictional validation benchmark; no model, browser, converter or applications."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_pipeline import seed


def fake_render(content, directory, soffice=None):
    for name in ['cv.docx', 'cv.pdf', 'page-001.png']:
        (directory / name).write_bytes(('FICTIONAL BENCHMARK ' + name).encode())
    return {'page_count': 1, 'renderer': {'test_double': True}}


def approved_batch(work, jobs, approve=True):
    now = datetime.now(timezone.utc)
    entries = []
    with patch('core.documents.render_files', side_effect=fake_render):
        for job_id in range(1, jobs + 1):
            render = work.render(job_id).data
            review = {'schema_version': '1.0', 'render_fingerprint': render['fingerprint'],
                      'reviewed_pages': [1],
                      'checks': dict.fromkeys(['content', 'layout', 'glyphs', 'language'], True)}
            proof = work.data_dir / 'fictional-review.json'
            proof.write_text(json.dumps(review), encoding='utf8')
            work.review_documents(render['render_id'], proof)
            entries.append({'job_id': job_id, 'render_id': render['render_id'], 'format': 'pdf',
                'destination': f'https://apply.example.test/form/FICT-{job_id}',
                'operations': ['fill', 'upload', 'submit'],
                'answers': {'salary': {'value': 'Negotiable', 'source': 'candidate_confirmed',
                                      'fact_ids': [], 'kind': 'ordinary'}},
                'required_answers': ['salary'], 'consents': [],
                'policy': {'permission': 'permitted', 'source': 'https://apply.example.test/policy',
                           'checked_utc': now.isoformat(),
                           'allowed_operations': ['fill', 'upload', 'submit']}})
    plan = {'schema_version': '1.0', 'campaign_id': 'fictional-benchmark',
            'mode': 'APPROVED_BATCH', 'expires_utc': (now + timedelta(hours=2)).isoformat(),
            'submission_limit': jobs, 'entries': entries,
            'execution': {'bridge_id': 'fictional-browser', 'runtime_minutes': 60}}
    result = work.create_manifest(copy.deepcopy(plan)).data
    if approve:
        proof = work.data_dir / 'fictional-approval.txt'
        proof.write_text('APPROVE MANIFEST ' + result['fingerprint'], encoding='utf8')
        work.approve_manifest(result['fingerprint'], proof)
    return result


def measure(work, operation, samples):
    times, profiles, jobs = [], [], []
    for _ in range(samples):
        with patch.object(work, 'inspect_profile', wraps=work.inspect_profile) as profile_reads, \
                patch.object(work, 'job_document', wraps=work.job_document) as job_reads:
            started = time.perf_counter()
            operation()
            times.append(round((time.perf_counter() - started) * 1000, 3))
            profiles.append(profile_reads.call_count)
            jobs.append(job_reads.call_count)
    return {'milliseconds': times, 'median_ms': round(statistics.median(times), 3),
            'profile_validations': profiles, 'job_document_reads': jobs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, choices=range(1, 101), default=100)
    parser.add_argument('--samples', type=int, choices=range(1, 21), default=5)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='career-kit-execution-benchmark-') as temp:
        work = seed(Path(temp) / 'private', args.jobs)
        batch = approved_batch(work, args.jobs)
        results = {'fictional_only': True, 'mock_renderer': True, 'browser_measured': False,
                   'jobs': args.jobs, 'samples': args.samples, 'python': sys.version.split()[0]}
        results['check_manifest'] = measure(work, lambda: work.check_manifest(batch['fingerprint']), args.samples)
        run = work.start_execution(batch['fingerprint'], 'fictional-browser', 60).data['run_id']
        request = work.next_action(run).data['request']
        results['check_action'] = measure(work, lambda: work.check_action(run, request['request_id']), args.samples)
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
