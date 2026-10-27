"""Optional SDK/Chromium QA. No credential vault, Google account or employer access."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.demo_slice1 import demo
from scripts.plugin_config import generate
from core.execution import Executor
from adapters.gmail_client import GmailClient
from adapters.local_browser import LocalForms


class PluginIntegrationTests(unittest.TestCase):
    def test_sdk_stdio_discovery_tracker_validation_and_configured_paths(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def check(workspace, kind):
            server = StdioServerParameters(command=sys.executable,
                args=[str(ROOT/'scripts/serve_plugin.py'), kind, '--data-dir', str(workspace)])
            async with asyncio.timeout(60):
                async with stdio_client(server) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = {t.name:t for t in (await session.list_tools()).tools}
                        self.assertIn('campaign_tracker', tools)
                        self.assertNotIn('approve_manifest', tools)
                        tool = tools['email_send_next' if kind=='email' else 'browser_execute']
                        self.assertTrue(tool.annotations.destructiveHint)
                        result = await session.call_tool('campaign_tracker', {})
                        self.assertFalse(result.isError)
                        self.assertEqual(json.loads(result.content[0].text)['data']['observed_submissions'], 0)
                        # A malformed consequential call must fail before entering its handler.
                        invalid = await session.call_tool('email_start' if kind=='email' else 'browser_start', {})
                        self.assertTrue(invalid.isError)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)/'private';demo(workspace)
            work=Executor(workspace);work.init()
            result=generate(work, sys.executable)
            self.assertFalse(result['host_settings_changed'])
            for path in result['packages']:
                config=json.loads((Path(path)/'mcp.json').read_text())
                target=next(iter(config['mcpServers'].values()))
                self.assertEqual(Path(target['command']),Path(sys.executable).resolve())
                self.assertIn(str(workspace.resolve()),target['args'])
            asyncio.run(check(workspace,'email'));asyncio.run(check(workspace,'browser'))

    def test_gmail_rejects_plaintext_vault_and_never_follows_send_redirects(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Executor(Path(tmp)/'private')
            client=GmailClient(work,'credentials/client.json')
            backend=type('Plaintext',(),{'__module__':'untrusted_plaintext','priority':10})()
            with patch('keyring.get_keyring',return_value=backend):
                with self.assertRaisesRegex(ValueError,'credential vault'):client._vault()
            response=SimpleNamespace(status_code=302)
            class Session:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def post(self,url,**kwargs):
                    self.kwargs=kwargs;return response
            session=Session()
            account={'id':'fictional-id','email':'candidate@example.com'}
            with patch.object(client,'_session',return_value=session), patch.object(client,'_identity',return_value=account):
                with client.prepare(account) as send:
                    with self.assertRaises(ValueError):send('fictional MIME')
            self.assertFalse(session.kwargs['allow_redirects'])
            self.assertEqual(session.kwargs['timeout'],30)
            session.kwargs=None
            with patch.object(client,'_session',return_value=session), patch.object(client,'_identity',return_value=account):
                with self.assertRaisesRegex(ValueError,'account changed'):
                    with client.prepare({'id':'different-account','email':'candidate@example.com'}):pass
            self.assertIsNone(session.kwargs)

    def test_real_chromium_form_bytes_review_challenge_and_receipt(self):
        from playwright.async_api import async_playwright
        async def check(root):
            html='''<h1 id="employer">Fictional Employer</h1><div id="requisition">FICT-1</div>
            <input id="salary" required><input id="cv" type="file" accept=".pdf">
            <input id="privacy" type="checkbox" required><label id="privacy-label">Fictional policy</label>
            <button id="submit" onclick="document.getElementById('confirmation').hidden=false">Apply</button>
            <p id="confirmation" hidden>Fictional application submitted</p>'''
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True)
                context=await browser.new_context(service_workers='block')
                await context.route_web_socket('**/*',LocalForms.block_socket)
                page=await context.new_page()
                await page.route('**/*',lambda route:route.fulfill(status=200,content_type='text/html',body=html))
                await page.goto('https://apply.example.test/FICT-1')
                socket_close=await page.evaluate('''() => new Promise(resolve => {
                    const ws=new WebSocket('wss://unapproved.example.test/fictional');
                    ws.onclose=e=>resolve(e.code); })''')
                self.assertEqual(socket_close,1008)
                plan={'schema_version':'1.0','destination':page.url,
                    'identity':{'employer':{'selector':'#employer','text':'Fictional Employer'},
                                'requisition':{'selector':'#requisition','text':'FICT-1'}},
                    'fields':{'salary':{'selector':'#salary','kind':'text'}},
                    'consents':[{'id':'p','selector':'#privacy','text_selector':'#privacy-label','text':'Fictional policy','required':True}],
                    'upload_selector':'#cv','submit_selector':'#submit','confirmation_selector':'#confirmation',
                    'confirmation_text':'Fictional application submitted','blocker_selectors':['#new-terms']}
                driver=LocalForms(root)
                driver.connections['fictional-session']={'page':page,'ready':True,'boundary':SimpleNamespace(blocked=False)}
                content=b'%PDF-1.4\nFICTIONAL TEST ONLY';(root/'cv.pdf').write_bytes(content)
                digest=hashlib.sha256(content).hexdigest()
                base={'run_id':'fictional-run','destination':page.url,'employer':'Fictional Employer','requisition':'FICT-1','job_id':1}
                choices=[{'id':'p','text':'Fictional policy','choice':True}]
                mutations=0
                def guard():
                    nonlocal mutations
                    mutations+=1
                for action in ('inspect','fill','upload','review','submit','verify'):
                    request={**base,'request_id':'fictional-'+action,'action':action}
                    if action in ('fill','review'):request.update(values={'salary':'Negotiable'},consents=choices)
                    if action=='upload':request['document']={'path':'cv.pdf','sha256':digest}
                    if action=='review':request['document_sha256']=digest
                    result=await driver._connect({'session_id':'fictional-session'},plan,request,guard)
                self.assertTrue(result['confirmed']);self.assertTrue((root/result['screenshot']).is_file())
                self.assertEqual(mutations,4)  # text, consent, file, submit
                await page.locator('body').evaluate("el=>el.insertAdjacentHTML('beforeend','<input id=secret type=password>')")
                with self.assertRaisesRegex(ValueError,'Login, challenge'):
                    await driver.observe(page,plan)
                await browser.close()
        with tempfile.TemporaryDirectory() as tmp:asyncio.run(check(Path(tmp)))
