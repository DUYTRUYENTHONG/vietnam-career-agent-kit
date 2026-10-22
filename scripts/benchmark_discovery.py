"""Fictional discovery scheduling benchmark; no network, models or applications."""
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.discovery import discover


def main():
    raw=json.dumps({'jobs':[{'id':i+1,'title':'Fictional role',
        'absolute_url':f'https://employer.example.invalid/{i}',
        'location':{'name':'Fictional City'},'content':'Untrusted text'} for i in range(100)]}).encode()
    def reader(board):
        time.sleep(.05)  # Explicit simulated I/O, not observed employer latency.
        return raw
    samples={1:[],3:[]}
    for iteration in range(7):
        for workers in ([1,3] if iteration%2==0 else [3,1]):
            start=time.perf_counter()
            result=discover([f'fictional-{i}' for i in range(12)],workers=workers,reader=reader)
            assert result['leads_count']==1200 and result['failed_boards']==0
            samples[workers].append(round((time.perf_counter()-start)*1000,3))
    print(json.dumps({'fictional_only':True,'boards':12,'leads':1200,
        'simulated_read_ms':50,'samples_ms':samples,
        'median_ms':{k:statistics.median(v) for k,v in samples.items()},
        'notice':'Scheduling benchmark only. No real discovery/submission rate or model cost measured.'},indent=2))


if __name__=='__main__':main()
