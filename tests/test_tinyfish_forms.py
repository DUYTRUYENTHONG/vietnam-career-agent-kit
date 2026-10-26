"""Exercise browser action logic with a controlled, fictional page double."""
import asyncio
import hashlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from adapters.tinyfish_forms import PlaywrightForms, ResponseBoundary
from core.workflow import WorkflowError
from test_tinyfish_browser import form


class Node:
    def __init__(self,page,selector):self.page=page;self.selector=selector
    async def count(self):return int(self.selector in self.page.nodes)
    async def is_visible(self):return True
    async def all(self):return [self] if await self.count() else []
    async def inner_text(self):return self.page.nodes[self.selector].get('text','')
    async def get_attribute(self,name):return self.page.nodes[self.selector].get(name)
    async def input_value(self):return self.page.nodes[self.selector].get('value','')
    async def is_checked(self):return self.page.nodes[self.selector].get('checked',False)
    async def fill(self,value):self.page.nodes[self.selector]['value']=value
    async def select_option(self,value):await self.fill(value)
    async def set_checked(self,value):self.page.nodes[self.selector]['checked']=value
    async def set_input_files(self,file):self.page.file=file['buffer']
    async def click(self,**kwargs):self.page.clicks+=1
    async def evaluate(self,code,arg=None):
        if 'el.matches' in code:return self.selector==arg
        if 'tagName' in code:return 'input'
        if 'crypto.subtle' in code:return hashlib.sha256(self.page.file).hexdigest() if self.page.file else None
        raise AssertionError('Unexpected evaluation')


class Many:
    def __init__(self,page):self.page=page
    async def all(self):return [Node(self.page,key) for key,value in self.page.nodes.items() if 'type' in value]


class Page:
    def __init__(self):
        self.url='https://apply.example.test/form/FICT-1';self.frames=[object()];self.file=b'';self.clicks=0
        self.nodes={'#employer':{'text':'Fictional Example'},'#requisition':{'text':'FICT-1'},
            '#salary':{'type':'text','required':''},'#privacy':{'type':'checkbox','required':''},
            '#privacy-label':{'text':'Fictional retention policy'},'#cv':{'type':'file','accept':'.pdf'},
            '#submit':{},'#confirmation':{'text':'Fictional application submitted'}}
    def locator(self,selector):return Many(self) if selector.startswith('input,select,textarea,') else Node(self,selector)
    async def screenshot(self,path,**kwargs):Path(path).write_bytes(b'fictional screenshot bytes')
    def set_default_timeout(self,value):pass
    async def wait_for_load_state(self,*args,**kwargs):pass


class FormsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.driver=PlaywrightForms(self.root);self.page=Page();self.calls=[]
        self.plan=form({'destination':self.page.url,'employer':'Fictional Example','requisition':'FICT-1'})
        self.request={'run_id':'fictional-run','request_id':'fictional-request','job_id':1,
            'destination':self.page.url,'employer':'Fictional Example','requisition':'FICT-1'}
    def tearDown(self):self.temp.cleanup()
    def act(self,action,**data):
        return asyncio.run(self.driver.on_page(self.page,self.plan,{**self.request,'action':action,**data},lambda:self.calls.append(action)))

    def test_full_action_flow_observes_bytes_and_values_before_one_submit(self):
        self.assertEqual(self.act('inspect')['form']['required_fields'],['salary'])
        consents=[{'id':'privacy-v1','text':'Fictional retention policy','choice':True}]
        self.act('fill',values={'salary':'Negotiable'},consents=consents)
        path=self.root/'cv.pdf';path.write_bytes(b'fictional reviewed document')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(self.act('upload',document={'path':'cv.pdf','sha256':digest})['document_sha256'],digest)
        self.act('review',values={'salary':'Negotiable'},consents=consents,document_sha256=digest)
        self.act('submit');self.assertEqual(self.page.clicks,1)
        receipt=self.act('verify');self.assertTrue(receipt['confirmed'])
        self.assertTrue((self.root/receipt['screenshot']).is_file())
        self.assertEqual(self.calls,['fill','fill','upload','submit'])

    def test_new_required_control_changed_consent_or_challenge_stops_before_disclosure(self):
        for change in [lambda p:p.nodes.update({'#unknown':{'type':'text','required':''}}),
                       lambda p:p.nodes['#privacy-label'].update(text='new terms'),
                       lambda p:p.nodes.update({'iframe[src*="recaptcha"]':{}})]:
            self.page=Page();change(self.page)
            with self.assertRaises(WorkflowError):self.act('fill',values={'salary':'Negotiable'},consents=[])
            self.assertEqual(self.calls,[])

    def test_changed_upload_or_values_prevents_final_click(self):
        self.act('inspect')
        self.driver.reviewed[1]={'values':{'salary':'Negotiable'},'consents':[],'document_sha256':'expected'}
        with self.assertRaises(WorkflowError):self.act('submit')
        self.assertEqual(self.page.clicks,0)
        path=self.root/'cv.pdf';path.write_bytes(b'changed')
        with self.assertRaises(WorkflowError):self.act('upload',document={'path':'cv.pdf','sha256':'wrong'})
        self.assertEqual(self.page.file,b'')

    def test_mapped_required_flag_change_stops_before_first_write(self):
        self.act('inspect');self.page.nodes['#salary'].pop('required')
        with self.assertRaises(WorkflowError):self.act('fill',values={'salary':'Negotiable'},consents=[])
        self.assertEqual(self.calls,[])

    def test_redirect_identity_and_confirmation_are_not_inferred(self):
        self.page.url='https://other.example.test/'
        with self.assertRaises(WorkflowError):self.act('inspect')
        self.page=Page();self.page.nodes['#employer']['text']='Other employer'
        with self.assertRaises(WorkflowError):self.act('verify')

    def test_response_stage_rejects_307_before_post_bytes_can_be_forwarded(self):
        calls=[]
        class CDP:
            async def send(self,method,args):calls.append((method,args))
            def on(self,event,handler):calls.append((event,handler))
        guard=ResponseBoundary(CDP())
        asyncio.run(guard.install())
        asyncio.run(guard.paused({'requestId':'post-with-cv','responseStatusCode':307,
            'request':{'method':'POST','url':self.page.url},
            'responseHeaders':[{'name':'Location','value':'https://other.example.test/collect'}]}))
        self.assertTrue(guard.blocked)
        self.assertEqual(calls[-1],('Fetch.failRequest',{'requestId':'post-with-cv','errorReason':'BlockedByClient'}))
        self.assertFalse(any(method=='Fetch.continueResponse' for method,args in calls))

    def test_reuses_one_cdp_connection_and_keeps_response_guard_between_actions(self):
        calls=[];page=self.page
        class CDP:
            async def send(self,*args):calls.append(args)
            def on(self,*args):calls.append(args)
        class Context:
            pages=[page];service_workers=[]
            async def add_init_script(self,script):calls.append(('init',))
            async def new_cdp_session(self,page):return CDP()
            async def route(self,*args):calls.append(('context-route',))
        class Client:
            async def connect_over_cdp(self,*args,**kwargs):
                calls.append(('connect',));return SimpleNamespace(contexts=[Context()])
            async def start(self):return SimpleNamespace(chromium=self)
        module=SimpleNamespace(async_playwright=lambda:Client())
        async def actions():
            for action in ['inspect','fill']:
                request={**self.request,'action':action,'values':{'salary':'Negotiable'},'consents':[]}
                await self.driver._connect({'session_id':'fixture','cdp_url':'wss://fixture.tinyfish.io/cdp'},self.plan,request,lambda:None)
        with patch.dict('sys.modules',{'playwright':SimpleNamespace(),'playwright.async_api':module}):asyncio.run(actions())
        self.assertEqual(calls.count(('connect',)),1)
        self.assertEqual(calls.count(('context-route',)),1)
        self.assertTrue(any(item[0]=='Fetch.enable' for item in calls))
        self.page=Page();self.page.nodes['#confirmation']['text']='Thank you for visiting'
        with self.assertRaises(WorkflowError):self.act('verify')
