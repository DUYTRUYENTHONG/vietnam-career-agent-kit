#!/usr/bin/env python3
"""Compare three CLI launch calls with one; fictional data, no browser/network."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.benchmark_execution import approved_batch
from scripts.benchmark_pipeline import seed


def sample(combined):
    with tempfile.TemporaryDirectory(prefix='career-kit-fictional-launch-') as temp:
        work=seed(Path(temp)/'private',1)
        batch=approved_batch(work,1,approve=False);entry=batch['manifest']['entries'][0]
        scope={'schema_version':'1.0','authorization_id':'fictional-launch-timing',
            'expires_utc':(datetime.now(timezone.utc)+timedelta(hours=3)).isoformat(),
            'submission_limit':1,'bridge_id':'fictional-browser','runtime_minutes':60,
            'targets':[{'employer':entry['employer'],'destination_prefix':'https://apply.example.test/form/',
                **{key:entry[key] for key in ['operations','answers','consents']}}]}
        grant=work.create_authorization(scope).data['fingerprint']
        proof=work.data_dir/'fictional-standing-proof.txt'
        proof.write_text('APPROVE AUTHORIZATION '+grant,encoding='utf8')
        work.approve_authorization(grant,proof)
        calls=0
        def invoke(*args):
            nonlocal calls
            calls+=1
            result=subprocess.run([sys.executable,str(ROOT/'scripts/kit.py'),
                '--data-dir',str(work.data_dir),*args],capture_output=True,encoding='utf8',timeout=30)
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            return json.loads(result.stdout)['data']
        started=time.perf_counter()
        if combined:
            result=invoke('launch-execution','--fingerprint',batch['fingerprint'],
                '--authorization',grant,'--bridge-id','fictional-browser','--runtime-minutes','60')
        else:
            invoke('authorize-manifest','--fingerprint',batch['fingerprint'],'--authorization',grant)
            run=invoke('start-execution','--fingerprint',batch['fingerprint'],
                '--bridge-id','fictional-browser','--runtime-minutes','60')['run_id']
            result=invoke('next-action','--run-id',run)
        elapsed=round((time.perf_counter()-started)*1000,3)
        if result['request']['action']!='inspect':raise AssertionError('Expected first read-only inspection')
        with work._db() as db:
            if db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0]:
                raise AssertionError('Benchmark must never submit')
        return elapsed,calls


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples',type=int,choices=range(1,21),default=7)
    args=parser.parse_args();results={'separate':[],'combined':[]};calls={}
    for index in range(args.samples):
        # Alternate order; each operation has a fresh, equivalent workspace.
        for label in (['separate','combined'] if index%2==0 else ['combined','separate']):
            elapsed,calls[label]=sample(label=='combined');results[label].append(elapsed)
    print(json.dumps({'fictional_only':True,'mock_renderer':True,'browser_measured':False,
        'python':sys.version.split()[0],'samples':args.samples,
        'setup_timed':False,'results':{label:{'milliseconds':values,
            'median_ms':round(statistics.median(values),3),'cli_calls':calls[label]}
            for label,values in results.items()}},indent=2))


if __name__=='__main__':main()
