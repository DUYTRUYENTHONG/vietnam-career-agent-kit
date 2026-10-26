"""Owned local Chromium sessions using existing canonical form and lane checks."""
import asyncio
import copy
import json
import threading
import time
import uuid
from urllib.parse import urlsplit

from core.contracts import Outcome
from core.ledger import canonical_hash, utc_now
from core.manifests import now_utc, timestamp
from core.workflow import WorkflowError
from .tinyfish_browser import destination
from .providers.contracts import public_host
from .tinyfish_forms import PlaywrightForms, ResponseBoundary, validate_form

BRIDGE = 'local-playwright'


def validate_plans(work, fingerprint, forms):
    work.check_manifest(fingerprint)
    manifest = work.current_manifest(fingerprint)
    if manifest.get('execution', {}).get('bridge_id') != BRIDGE:
        raise WorkflowError('blocked', 'Review an execution manifest for the local browser bridge')
    entries = {str(e['job_id']): e for e in manifest['entries']}
    if not isinstance(forms, dict) or set(forms) != set(entries):
        raise WorkflowError('blocked', 'Map exactly every approved application')
    for job, plan in forms.items():
        validate_form(plan)
        entry = entries[job]
        destination(plan['destination'])
        if (plan['destination'] != entry['destination'] or
                {k: v['text'] for k, v in plan['identity'].items()} !=
                {k: entry[k] for k in ('employer', 'requisition')}):
            raise WorkflowError('blocked', 'Form destination or identity differs from the approved job')
    return manifest


class LocalForms(PlaywrightForms):
    """In-memory contexts only; no imported/exported login state or personal profiles."""
    async def _create(self, session, plan):
        from playwright.async_api import async_playwright
        client = await async_playwright().start()
        connection = {'client': client, 'ready': False}
        self.connections[session['session_id']] = connection
        try:
            browser = await client.chromium.launch(headless=False)
            connection['browser'] = browser
            context = await browser.new_context(service_workers='block')
            # HTTP routes do not intercept WebSockets. Unsupported transports are
            # disabled before any page is created; this is not an OS firewall.
            await context.route_web_socket('**/*', self.block_socket)
            await context.add_init_script('''for (const name of ['RTCPeerConnection',
                'webkitRTCPeerConnection', 'WebTransport']) {
                if (name in globalThis) Object.defineProperty(globalThis, name, {
                    value: class { constructor() { throw new Error('Unsupported application transport'); } },
                    writable: false, configurable: false }); }''')
            page = await context.new_page()
            expected = urlsplit(plan['destination'])
            async def boundary(route):
                actual = urlsplit(route.request.url)
                if (route.request.frame.page != page or
                        (actual.scheme, actual.netloc) != (expected.scheme, expected.netloc)):
                    await route.abort()
                else:
                    await route.continue_()
            await context.route('**/*', boundary)
            context.on('page', lambda popup: asyncio.create_task(popup.close()) if popup != page else None)
            cdp = await context.new_cdp_session(page)
            guard = ResponseBoundary(cdp)
            await guard.install()
            page.set_default_timeout(10000)
            connection.update(page=page, boundary=guard, ready=True)
            await page.goto(plan['destination'], wait_until='domcontentloaded', timeout=30000)
            return {'session_id': session['session_id'], 'url': page.url,
                    'instruction': 'If login is needed, sign in yourself in this owned window; then execute. No password is read.'}
        except BaseException:
            connection['ready'] = False
            await self._dispose(connection)
            self.connections.pop(session['session_id'], None)
            raise

    @staticmethod
    async def block_socket(socket):
        await socket.close(code=1008, reason='Unsupported application transport')

    @staticmethod
    async def _dispose(connection):
        try:
            if 'browser' in connection: await connection['browser'].close()
        finally:
            await connection['client'].stop()

    def open(self, session, plan):
        future = asyncio.run_coroutine_threadsafe(self._create(session, plan), self._loop())
        try:
            return future.result(timeout=45)
        except TimeoutError:
            session['setup_uncertain'] = True
            future.cancel()
            raise WorkflowError('manual_required', 'Browser setup timed out; confirm cleanup before reopening') from None

    async def _connect(self, session, plan, request, authorize):
        connection = self.connections.get(session['session_id'])
        if not connection or not connection['ready'] or connection['boundary'].blocked:
            raise WorkflowError('manual_required', 'Owned session unavailable or redirect blocked; no recreation')
        result = await self.on_page(connection['page'], plan, request, authorize)
        if connection['boundary'].blocked:
            raise WorkflowError('manual_required', 'Redirect blocked; reconcile any possible submission')
        return result

    def release(self, session):
        async def close():
            connection = self.connections.get(session['session_id'])
            if connection:
                await self._dispose(connection)
                self.connections.pop(session['session_id'], None)
        asyncio.run_coroutine_threadsafe(close(), self._loop()).result(timeout=30)


class LocalBrowserBridge:
    def __init__(self, work, run_id, forms, *, driver=None):
        with work._db() as db:
            row = db.execute('SELECT fingerprint FROM execution_runs WHERE id=?', (run_id,)).fetchone()
        if not row: raise WorkflowError('blocked', 'Unknown browser run')
        validate_plans(work, row['fingerprint'], forms)
        self.work, self.run_id, self.forms = work, run_id, copy.deepcopy(forms)
        self.driver = driver if driver is not None else LocalForms(work.data_dir)
        self.sessions, self.seen, self.lock = {}, set(), threading.Lock()
        self.root = work.inside('execution/local-browser/' + run_id)
        self.root.mkdir(parents=True, exist_ok=True)
        if any(self.root.glob('*.intent.json')):
            raise WorkflowError('needs_input', 'Existing sessions require reconciliation; never recreate on restart')

    def open(self, job_id):
        job = str(job_id)
        if job not in self.forms: raise WorkflowError('blocked', 'Unknown approved job')
        public_host(urlsplit(self.forms[job]['destination']).hostname)
        with self.lock:
            if job in self.sessions: raise WorkflowError('blocked', 'Session already opened; use the existing window')
            with self.work._db() as db:
                run = db.execute('SELECT * FROM execution_runs WHERE id=?', (self.run_id,)).fetchone()
            if run['owner'] != self.work.actor:
                raise WorkflowError('blocked', 'A different coordinator owns this run')
            self.work.check_manifest(run['fingerprint'])
            if run['state'] != 'active' or now_utc() >= timestamp(run['deadline_utc'], 'deadline'):
                raise WorkflowError('blocked', 'Browser run is no longer active')
            session = {'session_id': uuid.uuid4().hex, 'closed': False}
            session['binding_id'] = BRIDGE + ':' + session['session_id']
            (self.root / (job + '.intent.json')).write_text(json.dumps(
                {'job_id': job_id, 'session_id': session['session_id'], 'created_utc': utc_now()}), encoding='utf8')
            self.sessions[job] = session
        try:
            return self.driver.open(session, self.forms[job])
        except Exception:
            if session.get('setup_uncertain'):
                raise
            # Only an unstarted window is eligible here. Release must complete
            # before removing the intent; otherwise preserve it for recovery.
            self.driver.release(session)
            with self.lock:
                self.sessions.pop(job, None)
                (self.root / (job + '.intent.json')).unlink()
            raise

    def _check(self, request, deadline):
        if time.monotonic() >= deadline:
            raise WorkflowError('blocked', 'Local browser action deadline reached')
        if request['run_id'] != self.run_id or request['bridge_id'] != BRIDGE:
            raise WorkflowError('blocked', 'Wrong local browser run')
        with self.work._db() as db:
            row = db.execute('SELECT payload FROM execution_actions WHERE id=? AND run_id=? AND receipt IS NULL',
                             (request['request_id'], self.run_id)).fetchone()
        if not row or canonical_hash(json.loads(row[0])) != canonical_hash(request):
            raise WorkflowError('blocked', 'Only the exact pending canonical action may execute')
        self.work.check_parallel_action(self.run_id, request['request_id'])

    def perform(self, request):
        deadline = time.monotonic() + 120
        self._check(request, deadline)
        with self.lock:
            if request['request_id'] in self.seen: raise WorkflowError('blocked', 'Never replay a browser action')
            self.seen.add(request['request_id'])
            session = self.sessions.get(str(request['job_id']))
        if not session or session['closed'] or request['binding_id'] not in {None, session['binding_id']}:
            raise WorkflowError('manual_required', 'Open/login the owned session before executing; no replacement')
        observed = self.driver.perform(session, self.forms[str(request['job_id'])], request,
                                       lambda: self._check(request, deadline))
        if not isinstance(observed, dict) or set(observed) & {'schema_version', 'request_id', 'binding_id'}:
            raise WorkflowError('blocked', 'Driver cannot override canonical receipt identity')
        if any(observed.get(key) != request[key] for key in ('employer', 'requisition')):
            raise WorkflowError('blocked', 'Observed page identity changed')
        return {**observed, 'schema_version': '1.0', 'request_id': request['request_id'],
                'binding_id': session['binding_id']}

    def close_application_tab(self, request):
        eligible = self.work.parallel_cleanup(self.run_id).data['requests']
        session = self.sessions.get(str(request['job_id']))
        if not session or not any(canonical_hash(r) == canonical_hash(request) for r in eligible) or request['binding_id'] != session['binding_id']:
            raise WorkflowError('blocked', 'No confirmed owned session is eligible for cleanup')
        self.driver.release(session); session['closed'] = True
        return {'schema_version': '1.0', 'request_id': request['request_id'], 'bridge_id': BRIDGE,
                'binding_id': session['binding_id'], 'status': 'closed', 'agent_owned': True, 'cleanup_requested': True}
