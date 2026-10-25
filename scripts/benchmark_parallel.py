#!/usr/bin/env python3
"""Measure the real application engine with fictional browser latency only."""
import argparse
import base64
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.benchmark_pipeline import seed
from scripts.benchmark_execution import approved_batch
from core.parallel_execution import ParallelExecutor, run_parallel_with_bridge


def measure(jobs,workers,latency_ms):
    with tempfile.TemporaryDirectory(prefix='career-fictional-parallel-') as temporary:
        seeded=seed(Path(temporary)/'private',jobs)
        work=ParallelExecutor(seeded.data_dir)
        batch=approved_batch(work,jobs)
        entries={entry['job_id']:entry for entry in batch['manifest']['entries']}
        (work.data_dir/'confirmation.png').write_bytes(base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
        run=work.start_parallel_execution(batch['fingerprint'],'fictional-browser',60,workers).data['run_id']
        lock=threading.Lock();active=0;peak=0;calls=0
        class Bridge:
            def perform(self,request):
                nonlocal active,peak,calls
                with lock:active+=1;peak=max(active,peak);calls+=1
                try:
                    time.sleep(latency_ms/1000)
                    entry=entries[request['job_id']]
                    receipt={'schema_version':'1.0','request_id':request['request_id'],
                        'binding_id':f"fictional-{request['job_id']}",'url':entry['destination'],
                        'employer':entry['employer'],'requisition':entry['requisition'],'status':'ok'}
                    if request['action'] in {'inspect','fill','upload','review'}:
                        receipt['form']={'fields':['salary'],'required_fields':['salary'],'consents':[],
                            'upload_extensions':['.pdf'],'blockers':[]}
                    if request['action']=='upload':receipt['document_sha256']=entry['document_sha256']
                    if request['action']=='review':receipt.update(values={'salary':'Negotiable'},consents=[],
                        document_sha256=entry['document_sha256'])
                    if request['action']=='verify':receipt.update(confirmed=True,
                        confirmation_text='Fictional benchmark confirmation',screenshot='confirmation.png')
                    return receipt
                finally:
                    with lock:active-=1
        started=time.perf_counter()
        result=run_parallel_with_bridge(work,run,Bridge())
        elapsed=time.perf_counter()-started
        with work._db() as db:
            attempts=db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0]
            confirmations=db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0]
        if result.data['state']!='completed' or confirmations!=jobs or result.data['worker_errors']:
            raise RuntimeError('Fictional benchmark failed; no successful throughput result')
        return {'workers':workers,'jobs':jobs,'seconds':round(elapsed,3),'peak_browser_calls':peak,
                'browser_calls':calls,'durable_attempts':attempts,'confirmed_receipts':confirmations}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=int,choices=range(1,11),default=10)
    parser.add_argument('--latency-ms',type=int,choices=range(0,5001),default=250)
    args=parser.parse_args()
    results=[measure(args.jobs,workers,args.latency_ms) for workers in [1,10]]
    print(json.dumps({'schema_version':'1.0','fictional_only':True,'real_engine':True,
        'live_browser_measured':False,'provider_calls':0,'mock_action_latency_ms':args.latency_ms,
        'preparation_included':False,'results':results,
        'observed_fixture_ratio':round(results[0]['seconds']/results[1]['seconds'],3),
        'notice':'Fixture timing only; no live employer throughput, model usage or monetary savings measured.'},indent=2))


if __name__=='__main__':main()
