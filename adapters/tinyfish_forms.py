"""Explicit, single-page employer forms over an optional Playwright CDP client.

No page instructions become authority. Unsupported controls stop the lane.
"""
import asyncio
import hashlib
import threading
from pathlib import Path
from urllib.parse import urlsplit

from core.contracts import ContractError, object_fields, text, version
from core.workflow import WorkflowError


def validate_form(plan):
    object_fields(plan, {'schema_version','destination','identity','fields','consents',
        'upload_selector','submit_selector','confirmation_selector','confirmation_text',
        'blocker_selectors'}, set(), 'form plan')
    version(plan,'form plan')
    for key in ['destination','upload_selector','submit_selector','confirmation_selector','confirmation_text']:
        text(plan[key],key)
    object_fields(plan['identity'],{'employer','requisition'},set(),'identity')
    for item in plan['identity'].values():
        object_fields(item,{'selector','text'},set(),'identity item')
        text(item['selector'],'identity selector');text(item['text'],'identity text')
    if not isinstance(plan['fields'],dict):raise ContractError('fields must be an object')
    selectors=[]
    for name,item in plan['fields'].items():
        text(name,'field name')
        object_fields(item,{'selector','kind'},set(),'field')
        text(item['selector'],'selector')
        if item['kind'] not in {'text','select'}:raise ContractError('Only text/select fields supported')
        selectors.append(item['selector'])
    if not isinstance(plan['consents'],list):raise ContractError('consents must be a list')
    ids=[]
    for item in plan['consents']:
        object_fields(item,{'id','selector','text_selector','text','required'},set(),'consent')
        for key in ['id','selector','text_selector','text']:text(item[key],key)
        if type(item['required']) is not bool:raise ContractError('required must be boolean')
        ids.append(item['id']);selectors.append(item['selector'])
    selectors += [plan['upload_selector'],plan['submit_selector']]
    if len(set(ids))!=len(ids) or len(set(selectors))!=len(selectors):raise ContractError('Duplicate form mapping')
    if not isinstance(plan['blocker_selectors'],list):raise ContractError('blocker_selectors must be a list')
    for selector in plan['blocker_selectors']:text(selector,'blocker selector')


class ResponseBoundary:
    """Reject redirects at response stage, before Chromium can forward a POST."""
    def __init__(self,cdp):self.cdp=cdp;self.blocked=False

    async def paused(self,event):
        if 300<=event.get('responseStatusCode',0)<400 and event['responseStatusCode']!=304:
            self.blocked=True
            await self.cdp.send('Fetch.failRequest',{'requestId':event['requestId'],'errorReason':'BlockedByClient'})
        else:
            await self.cdp.send('Fetch.continueResponse',{'requestId':event['requestId']})

    async def install(self):
        self.cdp.on('Fetch.requestPaused',self.paused)
        await self.cdp.send('Fetch.enable',{'patterns':[{'urlPattern':'*','requestStage':'Response'}]})


class PlaywrightForms:
    def __init__(self, root):
        self.root=Path(root).resolve()
        self.reviewed={}
        self.inspected={}
        self.connections={};self.loop=None;self.loop_lock=threading.Lock()

    def _loop(self):
        with self.loop_lock:
            if self.loop is None:
                self.loop=asyncio.new_event_loop()
                threading.Thread(target=self.loop.run_forever,daemon=True).start()
        return self.loop

    def perform(self, session, plan, request, authorize):
        validate_form(plan)
        # One persistent CDP connection per job: no sixfold reconnect overhead,
        # and response guards remain installed between protocol actions.
        return asyncio.run_coroutine_threadsafe(self._connect(session,plan,request,authorize),self._loop()).result(timeout=120)

    def release(self,session):
        async def disconnect():
            connection=self.connections.pop(session['session_id'],None)
            if connection:await connection['client'].stop()
        if self.loop:asyncio.run_coroutine_threadsafe(disconnect(),self.loop).result(timeout=30)

    async def _connect(self,session,plan,request,authorize):
        try:from playwright.async_api import async_playwright
        except ImportError:raise WorkflowError('needs_input','Install the optional Playwright client in your host environment') from None
        connection=self.connections.get(session['session_id'])
        if connection is None:
            client=await async_playwright().start()
            # Retain the client even on partial setup failure: never reconnect
            # an uncertain session automatically, and keep network guards alive.
            connection={'client':client,'ready':False}
            self.connections[session['session_id']]=connection
            browser=await client.chromium.connect_over_cdp(session['cdp_url'],timeout=30000)
            if len(browser.contexts)!=1 or len(browser.contexts[0].pages)!=1:
                raise WorkflowError('manual_required','Expected one isolated browser page')
            page=browser.contexts[0].pages[0]
            if browser.contexts[0].service_workers:
                raise WorkflowError('manual_required','Service-worker forms require a separate supported adapter')
            # This adapter does not support service-worker-backed forms. Block
            # ordinary registration before the first document loads, and bypass
            # worker interception for this page's network requests.
            await browser.contexts[0].add_init_script('''
                if (navigator.serviceWorker) {
                    Object.defineProperty(navigator.serviceWorker, 'register', {
                        value: () => Promise.reject(new Error('Unsupported form service worker')),
                        writable: false, configurable: false
                    });
                }
            ''')
            cdp=await browser.contexts[0].new_cdp_session(page)
            await cdp.send('Network.enable')
            await cdp.send('Network.setBypassServiceWorker',{'bypass':True})
            response_boundary=ResponseBoundary(cdp)
            await response_boundary.install()
            page.set_default_timeout(10000)
            origin=urlsplit(plan['destination'])
            async def boundary(route):
                target=urlsplit(route.request.url)
                if route.request.frame.page!=page or (target.scheme,target.netloc)!=(origin.scheme,origin.netloc):await route.abort()
                else:await route.continue_()
            await browser.contexts[0].route('**/*',boundary)
            if page.url=='about:blank':
                await asyncio.to_thread(authorize)
                await page.goto(plan['destination'],wait_until='domcontentloaded',timeout=30000)
            await page.wait_for_load_state('domcontentloaded',timeout=30000)
            connection.update(page=page,boundary=response_boundary,ready=True)
        if not connection['ready'] or connection['boundary'].blocked:
            raise WorkflowError('manual_required','Session setup incomplete or redirect blocked; no replay')
        result=await self.on_page(connection['page'],plan,request,authorize)
        if connection['boundary'].blocked:
            raise WorkflowError('manual_required','Redirect blocked before forwarding; reconcile possible submission')
        return result

    async def one(self,page,selector):
        node=page.locator(selector)
        if await node.count()!=1 or not await node.is_visible():
            raise WorkflowError('manual_required','Mapped control missing, hidden or ambiguous')
        return node

    async def identity(self,page,plan,request):
        actual=urlsplit(page.url);expected=urlsplit(request['destination'])
        if (actual.scheme,actual.netloc)!=(expected.scheme,expected.netloc):
            raise WorkflowError('manual_required','Application left its approved origin')
        if request['action']!='verify' and page.url!=request['destination']:
            raise WorkflowError('manual_required','Application destination changed')
        observed={}
        for name,item in plan['identity'].items():
            observed[name]=(await (await self.one(page,item['selector'])).inner_text()).strip()
            if observed[name]!=item['text'] or observed[name]!=request[name]:
                raise WorkflowError('blocked','Observed employer/requisition changed')
        return {'url':page.url,**observed,'status':'ok'}

    async def observe(self,page,plan):
        for selector in ['input[type=password]','iframe[src*="recaptcha"]','iframe[src*="challenges.cloudflare"]',
                         '[class*="captcha"]',*plan['blocker_selectors']]:
            for node in await page.locator(selector).all():
                if await node.is_visible():raise WorkflowError('manual_required','Login, challenge or reviewed blocker is visible')
        # Stop before disclosing anything to frames or new required/consent controls.
        if len(page.frames)!=1:raise WorkflowError('manual_required','Embedded forms require a dedicated reviewed adapter')
        mapped=[v['selector'] for v in plan['fields'].values()]+[v['selector'] for v in plan['consents']]+[plan['upload_selector']]
        for node in await page.locator('input,select,textarea,[contenteditable=true]').all():
            if not await node.is_visible():continue
            kind=await node.get_attribute('type')
            required=await node.get_attribute('required') is not None or await node.get_attribute('aria-required')=='true'
            if required or kind in {'checkbox','radio','file'}:
                if not any([await node.evaluate('(el,selector)=>el.matches(selector)',s) for s in mapped]):
                    raise WorkflowError('needs_input','Unknown required control or consent')
        required=[]
        for name,item in plan['fields'].items():
            node=await self.one(page,item['selector'])
            tag=await node.evaluate('el=>el.tagName.toLowerCase()')
            kind=await node.get_attribute('type') or 'text'
            if (item['kind']=='select' and tag!='select') or (item['kind']=='text' and
                    (tag not in {'input','textarea'} or kind in {'checkbox','radio','file','password','hidden','submit'})):
                raise WorkflowError('manual_required','Field control type changed')
            if await node.get_attribute('required') is not None or await node.get_attribute('aria-required')=='true':required.append(name)
        consents=[]
        for item in plan['consents']:
            node=await self.one(page,item['selector'])
            label=(await (await self.one(page,item['text_selector'])).inner_text()).strip()
            required_flag=await node.get_attribute('required') is not None or await node.get_attribute('aria-required')=='true'
            if await node.get_attribute('type')!='checkbox' or label!=item['text'] or required_flag!=item['required']:
                raise WorkflowError('needs_input','Consent control/text/requirement changed')
            consents.append({'id':item['id'],'text':label,'required':required_flag})
        upload=await self.one(page,plan['upload_selector'])
        if await upload.get_attribute('type')!='file':raise WorkflowError('manual_required','Upload control changed')
        extensions=[s.strip().lower() for s in (await upload.get_attribute('accept') or '').split(',') if s.strip()]
        await self.one(page,plan['submit_selector'])
        return {'fields':list(plan['fields']),'required_fields':required,'consents':consents,
                'upload_extensions':extensions,'blockers':[]}

    async def document_hash(self,page,plan):
        return await (await self.one(page,plan['upload_selector'])).evaluate('''async el => {
            if(el.files.length!==1) return null;
            const bytes=await el.files[0].arrayBuffer();
            return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)))
                .map(x=>x.toString(16).padStart(2,'0')).join(''); }''')

    async def values(self,page,plan,names):
        return {'values':{name:await (await self.one(page,plan['fields'][name]['selector'])).input_value() for name in names},
                'consents':[{'id':c['id'],'text':c['text'],'choice':await (await self.one(page,c['selector'])).is_checked()} for c in plan['consents']],
                'document_sha256':await self.document_hash(page,plan)}

    async def on_page(self,page,plan,request,authorize):
        result=await self.identity(page,plan,request)
        action=request['action']
        if action=='verify':
            node=await self.one(page,plan['confirmation_selector'])
            message=(await node.inner_text()).strip()
            if message!=plan['confirmation_text']:raise WorkflowError('manual_required','Explicit confirmation did not match')
            target=self.root/'execution'/'tinyfish'/request['run_id']/(request['request_id']+'.png')
            target.parent.mkdir(parents=True,exist_ok=True)
            await page.screenshot(path=str(target),full_page=True)
            return {**result,'confirmed':True,'confirmation_text':message,'screenshot':target.relative_to(self.root).as_posix()}
        form=await self.observe(page,plan)
        if action=='inspect':self.inspected[request['job_id']]=form
        elif self.inspected.get(request['job_id'])!=form:
            raise WorkflowError('needs_input','Form changed since canonical inspection; no further writes')
        async def before_write():
            await self.identity(page,plan,request)
            if await self.observe(page,plan)!=self.inspected.get(request['job_id']):
                raise WorkflowError('needs_input','Form changed immediately before mutation')
            await asyncio.to_thread(authorize)
        if action=='fill':
            if not set(request['values'])<=set(plan['fields']):raise WorkflowError('blocked','Unmapped approved answer')
            consent_map={c['id']:c for c in plan['consents']}
            for item in request['consents']:
                if item['id'] not in consent_map or item['text']!=consent_map[item['id']]['text']:
                    raise WorkflowError('blocked','Unmapped consent')
            for name,value in request['values'].items():
                node=await self.one(page,plan['fields'][name]['selector']);await before_write()
                if plan['fields'][name]['kind']=='select':await node.select_option(value=str(value))
                else:await node.fill(str(value))
            for item in request['consents']:
                node=await self.one(page,consent_map[item['id']]['selector']);await before_write()
                await node.set_checked(item['choice'])
        elif action=='upload':
            path=(self.root/request['document']['path']).resolve()
            if not path.is_relative_to(self.root):raise WorkflowError('blocked','Document left workspace')
            content=path.read_bytes();digest=hashlib.sha256(content).hexdigest()
            if digest!=request['document']['sha256']:raise WorkflowError('blocked','Frozen document changed')
            if path.suffix.lower()!='.pdf':raise WorkflowError('blocked','Only reviewed PDFs supported')
            node=await self.one(page,plan['upload_selector']);await before_write()
            await node.set_input_files({'name':path.name,'mimeType':'application/pdf','buffer':content})
            observed=await self.document_hash(page,plan)
            if observed!=digest:raise WorkflowError('blocked','Browser upload bytes differ')
            result['document_sha256']=observed
        elif action=='review':
            observed=await self.values(page,plan,request['values'])
            expected={key:request[key] for key in ['values','consents','document_sha256']}
            if observed!=expected:raise WorkflowError('blocked','Visible review differs from approved answers/document')
            self.reviewed[request['job_id']]=observed
            result.update(observed)
        elif action=='submit':
            reviewed=self.reviewed.get(request['job_id'])
            if reviewed is None or await self.values(page,plan,reviewed['values'])!=reviewed:
                raise WorkflowError('blocked','Visible answers/document changed after review')
            node=await self.one(page,plan['submit_selector']);await before_write()
            await node.click(no_wait_after=True)
            return result
        elif action!='inspect':raise WorkflowError('blocked','Unsupported action')
        result['form']=await self.observe(page,plan)
        return result
