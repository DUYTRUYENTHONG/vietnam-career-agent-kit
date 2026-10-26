"""Opt-in TinyFish Browser sessions for exact host-issued application actions.

No Agent goals, persisted logins, proxies, automatic retries or credential output.
Cloud scope approval is additional to employer/application authority.
"""
import copy
import json
import os
import re
import threading
import math
import time
from urllib.parse import urlsplit
from urllib.request import Request, ProxyHandler, build_opener

from core.contracts import ContractError, Outcome, object_fields, version
from core.ledger import canonical_hash, utc_now
from core.manifests import now_utc, timestamp
from core.workflow import WorkflowError
from .providers.firecrawl import NoRedirect
from .providers.contracts import MANUAL_HOSTS, canonical_url, public_host

ENDPOINT='https://api.browser.tinyfish.ai'
BRIDGE='tinyfish-browser'


def destination(value):
    canonical_url(value)
    p=urlsplit(value)
    if (p.scheme!='https' or not p.hostname or p.username or p.password or
            any(p.hostname==h or p.hostname.endswith('.'+h) for h in MANUAL_HOSTS)):
        raise ContractError('Use an explicitly permitted HTTPS employer destination')
    if p.hostname=='localhost' or p.hostname.endswith(('.localhost','.local','.internal')):
        raise ContractError('Private destinations are unsupported')
    import ipaddress
    try:
        address=ipaddress.ip_address(p.hostname)
    except ValueError:pass
    else:
        if not address.is_global:raise ContractError('Private destinations are unsupported')
    return value


def preview(work, run_id, forms, scope):
    object_fields(scope,{'schema_version','provider','manifest_fingerprint','expires_utc','max_sessions'},set(),'cloud scope')
    version(scope,'cloud scope')
    if scope['provider']!=BRIDGE or type(scope['max_sessions']) is not int or not 1<=scope['max_sessions']<=10:
        raise ContractError('Cloud scope requires tinyfish-browser and 1-10 sessions')
    if now_utc()>=timestamp(scope['expires_utc'],'cloud expiry'):
        raise WorkflowError('blocked','Cloud authorization scope expired')
    status=work.parallel_status(run_id).data
    with work._db() as db:
        row=db.execute('SELECT fingerprint,payload FROM execution_runs WHERE id=?',(run_id,)).fetchone()
    payload=json.loads(row['payload'])
    if payload['bridge_id']!=BRIDGE or row['fingerprint']!=scope['manifest_fingerprint']:
        raise WorkflowError('blocked','Review an exact manifest bound to tinyfish-browser')
    manifest=work._manifest_snapshot(row['fingerprint'])
    entries={str(e['job_id']):e for e in manifest['entries']}
    if not isinstance(forms,dict) or set(forms)!=set(entries):
        raise ContractError('Provide one exact form plan for every manifest job')
    from .tinyfish_forms import validate_form
    for job,plan in forms.items():
        validate_form(plan)
        from pathlib import Path
        if Path(entries[job]['document']['path']).suffix.lower()!='.pdf':
            raise ContractError('TinyFish form adapter currently supports reviewed PDFs only')
        if destination(plan['destination'])!=entries[job]['destination']:
            raise ContractError('Form plan destination differs from manifest')
    if status['workers']>scope['max_sessions'] or len(entries)>scope['max_sessions']:
        raise ContractError('Run exceeds approved cloud session allocation')
    bundle={'run_id':run_id,'forms':forms,'cloud_scope':scope}
    return Outcome('ok',{'fingerprint':canonical_hash(bundle),'provider':BRIDGE,
        'jobs':sorted(int(j) for j in entries),'max_sessions':scope['max_sessions'],
        'disclosure':'TinyFish processes remote browser content and approved candidate fields/documents. '
                     'Review provider terms, account permissions and spending before approving this exact fingerprint.',
        'network_calls':0,'live_verified':False},[])


class BrowserHTTP:
    """Official fixed-origin REST operations; secret and response errors are redacted."""
    def __init__(self, key=None):
        self.key=key if key is not None else os.environ.get('TINYFISH_API_KEY')
        if not isinstance(self.key,str) or not self.key or any(ord(c)<33 or ord(c)>126 for c in self.key):
            raise WorkflowError('needs_input','TINYFISH_API_KEY is missing or invalid')

    def __call__(self, method, session_id=None, payload=None):
        if method=='POST' and session_id is None:
            url=ENDPOINT
        elif method=='DELETE' and isinstance(session_id,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',session_id):
            url=ENDPOINT+'/'+session_id
        else:raise ContractError('Invalid TinyFish Browser operation')
        req=Request(url,method=method,data=json.dumps(payload).encode() if payload is not None else None,
            headers={'X-API-Key':self.key,'Content-Type':'application/json','Accept':'application/json'})
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(req,timeout=60) as response:
                if method=='DELETE':
                    if response.status!=204:raise ValueError()
                    return None
                if response.status!=201 or response.headers.get_content_type()!='application/json':raise ValueError()
                raw=response.read(65537)
                if len(raw)>65536:raise ValueError()
                return json.loads(raw)
        except Exception:
            raise WorkflowError('manual_required','TinyFish Browser request failed or is uncertain; do not replay session creation') from None


class TinyFishBrowserBridge:
    def __init__(self, work, run_id, forms, scope, approved_fingerprint, *, transport=None, driver=None, action_timeout_seconds=120):
        if type(action_timeout_seconds) not in {int,float} or not math.isfinite(action_timeout_seconds) or not 0<action_timeout_seconds<=3600:
            raise ContractError('Action timeout must be finite and in (0, 3600] seconds')
        plan=preview(work,run_id,forms,scope)
        if plan.data['fingerprint']!=approved_fingerprint:
            raise WorkflowError('blocked','Approve the exact cloud disclosure/form-plan fingerprint first')
        self.work=work;self.run_id=run_id;self.forms=copy.deepcopy(forms);self.scope=copy.deepcopy(scope)
        self.transport=transport if transport is not None else BrowserHTTP()
        if driver is None:
            import importlib.util
            if importlib.util.find_spec('playwright') is None:
                raise WorkflowError('needs_input','Install the optional Playwright client before creating cloud sessions')
            from .tinyfish_forms import PlaywrightForms
            driver=PlaywrightForms(work.data_dir)
        self.driver=driver;self.sessions={};self.lock=threading.Lock();self.seen=set()
        self.action_timeout_seconds=action_timeout_seconds
        self.root=work.inside('execution/tinyfish/'+run_id)
        self.root.mkdir(parents=True,exist_ok=True)
        # A restart must reconcile old sessions/intents, never allocate replacements.
        if any(self.root.glob('*.intent.json')):
            raise WorkflowError('needs_input','Existing TinyFish session intents require reconciliation; no automatic relaunch')

    def _check(self, request, deadline=float('inf')):
        if time.monotonic()>=deadline:
            raise WorkflowError('blocked','Local action deadline reached; no further mutation')
        if request.get('run_id')!=self.run_id or request.get('bridge_id')!=BRIDGE:
            raise WorkflowError('blocked','Wrong TinyFish run/bridge')
        if (now_utc()>=timestamp(self.scope['expires_utc'],'cloud expiry') or
                (request.get('action')!='verify' and now_utc()>=timestamp(request['deadline_utc'],'action deadline'))):
            raise WorkflowError('blocked','Cloud/action scope expired')
        with self.work._db() as db:
            row=db.execute('SELECT payload FROM execution_actions WHERE run_id=? AND id=? AND receipt IS NULL',
                           (self.run_id,request['request_id'])).fetchone()
        if row is None or canonical_hash(json.loads(row[0]))!=canonical_hash(request):
            raise WorkflowError('blocked','Only the exact pending canonical request may execute')
        # This guard reads current authority. Only the coordinator commits actions/receipts.
        self.work.check_parallel_action(self.run_id,request['request_id'])

    def _session(self, request):
        job=str(request['job_id'])
        with self.lock:
            if job in self.sessions:return self.sessions[job]
            if request['action']!='inspect' or request['binding_id'] is not None:
                raise WorkflowError('needs_input','No owned session; never recreate a lost application binding')
            intent=self.root/(job+'.intent.json')
            with intent.open('x',encoding='utf8') as stream:
                json.dump({'job_id':request['job_id'],'request_id':request['request_id'],'created_utc':utc_now(),
                    'provider':BRIDGE,'state':'creation_intent','destination':request['destination']},stream)
        public_host(urlsplit(request['destination']).hostname)
        # Start blank: the driver installs its request boundary before navigation.
        response=self.transport('POST',payload={'timeout_seconds':120,'proxy_config':{'enabled':False}})
        try:
            session_id=response['session_id'];cdp=response['cdp_url'];p=urlsplit(cdp)
            if (not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',session_id) or p.scheme!='wss' or
                    not p.hostname or not any(p.hostname.endswith('.'+h) for h in ['tinyfish.io','tinyfish.ai']) or
                    p.username or p.password or p.port not in {None,443}):raise ValueError()
        except Exception:
            raise WorkflowError('manual_required','Invalid TinyFish session response; reconcile the saved intent') from None
        with self.lock:
            if any(s['session_id']==session_id for s in self.sessions.values()):
                raise WorkflowError('blocked','Provider returned a session already bound to another job')
            session={'session_id':session_id,'cdp_url':cdp,'binding_id':BRIDGE+':'+session_id,'closed':False}
            self.sessions[job]=session
            # CDP URL may grant access: keep it in memory, never persist/print it.
            (self.root/(job+'.session.json')).write_text(json.dumps({'session_id':session_id,
                'job_id':request['job_id'],'created_utc':utc_now()}),encoding='utf8')
        return session

    def perform(self, request):
        deadline=time.monotonic()+self.action_timeout_seconds
        self._check(request,deadline)
        with self.lock:
            if request['request_id'] in self.seen:raise WorkflowError('blocked','Browser action already dispatched; never replay')
            self.seen.add(request['request_id'])
        session=self._session(request)
        if session['closed'] or request['binding_id'] not in {None,session['binding_id']}:
            raise WorkflowError('blocked','Application session binding changed or is closed')
        self._check(request,deadline)
        try:
            observed=self.driver.perform(session,self.forms[str(request['job_id'])],request,lambda:self._check(request,deadline))
        except Exception:
            raise WorkflowError('manual_required','Browser action failed or is uncertain; preserve intent and reconcile, never retry') from None
        if not isinstance(observed,dict) or set(observed)&{'schema_version','request_id','binding_id'}:
            raise WorkflowError('blocked','Driver must not override canonical receipt identity')
        receipt={**observed,'schema_version':'1.0','request_id':request['request_id'],'binding_id':session['binding_id']}
        if any(receipt.get(k)!=request[k] for k in ['employer','requisition']):
            raise WorkflowError('blocked','Observed page identity differs from approved application')
        return receipt

    def close_application_tab(self, request):
        job=str(request['job_id']);session=self.sessions.get(job)
        eligible=self.work.parallel_cleanup(self.run_id).data['requests']
        if (not any(canonical_hash(r)==canonical_hash(request) for r in eligible) or not session or
                request['binding_id']!=session['binding_id'] or not request['requires_agent_owned']):
            raise WorkflowError('blocked','No eligible confirmed owned TinyFish session cleanup')
        if not session['closed']:
            self.transport('DELETE',session['session_id']);session['closed']=True
        release=getattr(self.driver,'release',None)
        if callable(release):release(session)
        return {'schema_version':'1.0','request_id':request['request_id'],'bridge_id':BRIDGE,
            'binding_id':session['binding_id'],'status':'closed','agent_owned':True,'cleanup_requested':True}
