import json
from threading import Lock
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from core.contracts import ContractError
from core.discovery import MAX_BYTES, NoRedirect, discover, normalize, read_board
from scripts.kit import execute, parser


def board_bytes(count=100):
    return json.dumps({'jobs': [{'id': i+1, 'title': 'Fictional automation role',
        'absolute_url': f'https://employer.example.invalid/jobs/{i+1}',
        'location': {'name': 'Fictional City'}, 'content': '<p>Untrusted JD</p>'}
        for i in range(count)]}).encode()


class DiscoveryTests(unittest.TestCase):
    def test_dedup_and_stable_fingerprint(self):
        raw=board_bytes(1)
        payload=json.loads(raw);payload['jobs']*=2
        result=normalize('fictional',json.dumps(payload).encode())
        self.assertEqual(len(result['leads']),1)
        self.assertEqual(result['leads'],normalize('fictional',raw)['leads'])
        payload['jobs'][1]=dict(payload['jobs'][1],title='Changed')
        with self.assertRaises(ValueError):normalize('fictional',json.dumps(payload).encode())

    def test_bounds_and_bad_records(self):
        for boards in [[],['../bad'],['x?token=secret'],['x']*13]:
            with self.assertRaises(ContractError):discover(boards)
        with self.assertRaises(ContractError):discover(['x'],workers=4)
        with self.assertRaises(ContractError):read_board('../invalid')
        for raw in [b'[]',b'no json',b'x'*(MAX_BYTES+1),b'{"jobs":[{}]}',board_bytes(5001)]:
            with self.assertRaises(ValueError):normalize('fictional',raw)
        payload=json.loads(board_bytes(1))
        for url in ['http://example.invalid','https://user:pass@example.invalid']:
            payload['jobs'][0]['absolute_url']=url
            with self.assertRaises(ValueError):normalize('fictional',json.dumps(payload).encode())

    def test_parallel_bounded_and_deterministic(self):
        active=peak=0;lock=Lock();calls=[]
        def reader(board):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active);calls.append(board)
            time.sleep(.02)
            with lock:active-=1
            return board_bytes()
        result=discover(['fictional-a','fictional-b','fictional-a','fictional-c'],reader=reader,workers=2)
        self.assertEqual(result['leads_count'],300)
        self.assertEqual(len(calls),3)
        self.assertEqual(peak,2)
        self.assertEqual([r['board'] for r in result['boards']],['fictional-a','fictional-b','fictional-c'])

    def test_partial_failure_no_retry(self):
        calls=[]
        def reader(board):
            calls.append(board)
            if board=='bad':raise HTTPError('https://example.invalid',429,'secret',{},None)
            return board_bytes(1)
        result=discover(['bad','good'],reader=reader)
        self.assertEqual(result['failed_boards'],1)
        self.assertEqual(result['boards'][0]['http_status'],429)
        self.assertNotIn('secret',json.dumps(result))
        self.assertEqual(len(calls),2)

    def test_fixed_origin_get_and_no_redirect(self):
        class Headers(dict):
            def get_content_type(self):return 'application/json'
        class Response:
            headers=Headers()
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):
                self.bound=n
                return board_bytes(1)
        response=Response()
        with patch('core.discovery.build_opener') as opener:
            opener.return_value.open.return_value=response
            read_board('fictional')
            args,kwargs=opener.return_value.open.call_args
            self.assertEqual(args[0].get_method(),'GET')
            self.assertEqual(args[0].full_url,'https://boards-api.greenhouse.io/v1/boards/fictional/jobs?content=true')
            self.assertEqual(kwargs['timeout'],10)
            self.assertEqual(response.bound,MAX_BYTES+1)
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://other.invalid'))

    def test_cli_no_workspace(self):
        with patch('core.discovery.read_board',return_value=board_bytes(1)):
            outcome=execute(parser().parse_args(['discover-greenhouse','--board','fictional']))
        self.assertEqual(outcome.data['leads_count'],1)
        self.assertNotIn('content',outcome.data['boards'][0]['leads'][0])

    def test_full_content_opt_in_does_not_change_identity(self):
        compact=discover(['fictional'],reader=lambda _:board_bytes(1))
        full=discover(['fictional'],reader=lambda _:board_bytes(1),include_content=True)
        a=compact['boards'][0]['leads'][0];b=full['boards'][0]['leads'][0]
        self.assertNotIn('content',a)
        self.assertIn('content',b)
        self.assertEqual(a['fingerprint'],b['fingerprint'])

    def test_cli_failed_board_is_not_ok(self):
        with patch('core.discovery.read_board',side_effect=TimeoutError('private detail')):
            outcome=execute(parser().parse_args(['discover-greenhouse','--board','fictional']))
        self.assertEqual(outcome.json()['outcome'],'manual_required')
        self.assertEqual(outcome.data['failed_boards'],1)
        self.assertNotIn('private detail',json.dumps(outcome.json()))


if __name__=='__main__':unittest.main()
