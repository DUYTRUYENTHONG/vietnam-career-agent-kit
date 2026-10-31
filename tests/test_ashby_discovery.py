"""Fictional Ashby feeds only; no provider, candidate workspace or paid model."""
import json
from threading import Barrier, Lock
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from core import discovery as d
from core.contracts import ContractError
from scripts.kit import execute, parser


def posting(**changes):
    return dict(title='Fictional AI role', jobUrl='https://jobs.ashbyhq.com/fictional/post-1',
                isListed=True, location='Fictional City', workplaceType='Hybrid',
                isRemote=True, employmentType='FullTime', descriptionPlain='Untrusted full JD',
                **changes)


def feed(*jobs):
    return json.dumps({'apiVersion': '1', 'jobs': list(jobs) or [posting()]}).encode()


class AshbyDiscoveryTests(unittest.TestCase):
    def test_remote_hybrid_and_unlisted_metadata(self):
        visible=posting()
        visible['secondaryLocations']=[{'location':'Other City','address':{'addressCountry':'VN'}}]
        hidden={'isListed':False, 'title':'Do not expose unlisted role'}
        result=d.normalize_ashby('fictional', feed(visible, hidden))
        self.assertEqual(result['records_received'],2)
        self.assertEqual(len(result['leads']),1)
        lead=result['leads'][0]
        self.assertEqual(lead['key'],'ashby:fictional:post-1')
        self.assertEqual(lead['workplace_type'],'Hybrid')
        self.assertTrue(lead['is_remote'])
        self.assertEqual(lead['employment_type'],'FullTime')
        self.assertEqual(lead['secondary_locations'][0]['country'],'VN')
        self.assertNotIn('Do not expose',json.dumps(result))
        self.assertNotIn('vietnam_eligible',lead)

    def test_missing_optional_values_stay_unknown(self):
        raw=feed({'title':'Role','isListed':True,'jobUrl':'https://jobs.ashbyhq.com/fictional/id'})
        lead=d.normalize_ashby('fictional',raw)['leads'][0]
        self.assertEqual(lead['workplace_type'],'')
        self.assertIsNone(lead['is_remote'])
        self.assertEqual(lead['employment_type'],'')
        self.assertEqual(lead['location'],'')
        self.assertEqual(lead['country'],'')

    def test_duplicates_and_fingerprint_cover_content(self):
        a=posting()
        one=d.normalize_ashby('fictional',feed(a))['leads'][0]
        two=d.normalize_ashby('fictional',feed(a,a))['leads']
        self.assertEqual(two,[one])
        b=dict(a,descriptionPlain='Changed requirement')
        self.assertNotEqual(one['fingerprint'],d.normalize_ashby('fictional',feed(b))['leads'][0]['fingerprint'])
        with self.assertRaises(ValueError):d.normalize_ashby('fictional',feed(a,b))

    def test_untrusted_html_fallback_is_not_executed(self):
        a=posting();a.pop('descriptionPlain');a['descriptionHtml']='<script>untrusted()</script>'
        lead=d.normalize_ashby('fictional',feed(a))['leads'][0]
        self.assertEqual(lead['content'],'<script>untrusted()</script>')
        self.assertEqual(lead['content_format'],'html')

    def test_shape_bounds_and_unsupported_version(self):
        for raw in [b'[]',b'not json',b'x'*(d.MAX_BYTES+1),b'{"jobs":[]}',
                    b'{"apiVersion":"2","jobs":[]}',feed({'isListed':1}),
                    json.dumps({'apiVersion':'1','jobs':[posting()]*5001}).encode()]:
            with self.subTest(raw=raw[:45]):
                with self.assertRaises(ValueError):d.normalize_ashby('fictional',raw)
        for field,value in [('workplaceType','Elsewhere'),('employmentType','Maybe'),
                            ('isRemote','true'),('secondaryLocations',{}),('location',1),
                            ('descriptionPlain',[]),('isListed',None)]:
            a=posting();a[field]=value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):d.normalize_ashby('fictional',feed(a))

    def test_job_urls_cannot_change_origin_or_board(self):
        # Synthetic credentials, not a real contact or account.
        credential_url='https://'+'user:secret'+'@'+'jobs.ashbyhq.com/fictional/id'
        for url in ['http://jobs.ashbyhq.com/fictional/id',credential_url,
                    'https://other.invalid/fictional/id','https://jobs.ashbyhq.com/other/id',
                    'https://jobs.ashbyhq.com/fictional/id/extra','https://jobs.ashbyhq.com/fictional/%2e%2e']:
            a=posting();a['jobUrl']=url
            with self.subTest(url=url):
                with self.assertRaises(ValueError):d.normalize_ashby('fictional',feed(a))

    def test_compact_mode_keeps_full_identity(self):
        compact=d.discover(['fictional'],provider='ashby',reader=lambda _:feed())
        full=d.discover(['fictional'],provider='ashby',reader=lambda _:feed(),include_content=True)
        a=compact['boards'][0]['leads'][0];b=full['boards'][0]['leads'][0]
        self.assertEqual(compact['source'],'ashby-public-board')
        self.assertNotIn('content',a)
        self.assertEqual(b['content'],'Untrusted full JD')
        self.assertEqual(a['fingerprint'],b['fingerprint'])

    def test_fixed_origin_get_and_response_checks(self):
        class Headers(dict):
            content_type='application/json'
            def get_content_type(self):return self.content_type
        class Response:
            def __init__(self):self.headers=Headers()
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,n):self.bound=n;return feed()
        response=Response()
        with patch('core.discovery.build_opener') as opener:
            opener.return_value.open.return_value=response
            d.read_ashby_board('fictional')
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(),'GET')
            self.assertEqual(request.full_url,'https://api.ashbyhq.com/posting-api/job-board/fictional')
            self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'],10)
            self.assertEqual(response.bound,d.MAX_BYTES+1)
            self.assertNotIn('Authorization',dict(request.header_items()))
            self.assertEqual(opener.call_args.args[0].proxies,{})
            self.assertIsInstance(opener.call_args.args[1],d.NoRedirect)
            response.headers['Content-Encoding']='gzip'
            with self.assertRaises(ValueError):d.read_ashby_board('fictional')
            response.headers.clear();response.headers.content_type='text/html'
            with self.assertRaises(ValueError):d.read_ashby_board('fictional')

    def test_partial_failure_is_sanitized_without_retry(self):
        calls=[]
        def reader(board):
            calls.append(board)
            if board=='bad':raise HTTPError('https://api.ashbyhq.com',429,'private-detail',{},None)
            return feed()
        result=d.discover(['bad','fictional','fictional'],provider='ashby',reader=reader)
        self.assertCountEqual(calls,['bad','fictional'])
        self.assertEqual(result['failed_boards'],1)
        self.assertEqual(result['leads_count'],1)
        self.assertNotIn('private-detail',json.dumps(result))

    def test_parallel_board_reads_are_bounded_and_ordered(self):
        barrier=Barrier(2);lock=Lock();active=peak=0;calls=[]
        def reader(board):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active);calls.append(board)
            barrier.wait(timeout=2)
            with lock:active-=1
            a=posting();a['jobUrl']=f'https://jobs.ashbyhq.com/{board}/id'
            return feed(a)
        result=d.discover(['a','b','a'],workers=2,provider='ashby',reader=reader)
        self.assertEqual(peak,2)
        self.assertEqual(sorted(calls),['a','b'])
        self.assertEqual([b['board'] for b in result['boards']],['a','b'])

    def test_invalid_input_never_calls_transport(self):
        for boards in [[],['../x'],['x?candidate=private'],['a']*13]:
            with self.assertRaises(ContractError):d.discover(boards,provider='ashby',reader=lambda _:self.fail())
        with self.assertRaises(ContractError):d.read_ashby_board('../x')
        with self.assertRaises(ContractError):d.discover(['a'],provider='unknown')

    def test_cli_no_workspace_and_explicit_failure(self):
        with patch('core.discovery.read_ashby_board',return_value=feed()),patch('scripts.kit.Kit') as kit:
            outcome=execute(parser().parse_args(['discover-ashby','--board','fictional']))
        kit.assert_not_called()
        self.assertEqual(outcome.data['leads_count'],1)
        with patch('core.discovery.read_ashby_board',side_effect=TimeoutError('private-detail')):
            outcome=execute(parser().parse_args(['discover-ashby','--board','fictional']))
        self.assertEqual(outcome.json()['outcome'],'manual_required')
        self.assertNotIn('private-detail',json.dumps(outcome.json()))


if __name__=='__main__':unittest.main()
