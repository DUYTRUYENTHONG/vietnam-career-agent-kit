"""Opt-in standing delegation, bounded by recipient, facts, budget and expiry.

Local records do not authenticate a human or replace host action-time consent.
Exact manifests, document reviews and browser receipts remain mandatory.
"""
import json
from datetime import timedelta
from pathlib import Path
import re

from .contracts import ContractError, Outcome, object_fields, text, version
from .ledger import _https, canonical_hash, utc_now
from .manifests import now_utc, timestamp, operations
from .workflow import WorkflowError


def require_schema(work):
    with work._db() as db:
        schema=db.execute('PRAGMA user_version').fetchone()[0]
        if schema>5:
            raise WorkflowError('blocked','Standing workspace schema is newer than this toolkit')
        if schema<4:
            raise WorkflowError('needs_input','Run compatible init for standing authorization schema 4')


def safe_url(value, label, prefix=False):
    url=_https(value,label)
    if ('*' in url.netloc or '\\' in url.path or '//' in url.path or
            any(part in {'.','..'} for part in url.path.split('/')) or
            re.search(r'%(?:2f|5c|2e|25)',url.path,re.I) or
            (prefix and not url.path.endswith('/'))):
        raise ContractError(label+': use an unambiguous HTTPS directory prefix without wildcards or traversal')
    return url


def create(work, raw):
    require_schema(work)
    plan=object_fields(raw,{'schema_version','authorization_id','expires_utc',
        'submission_limit','bridge_id','runtime_minutes','targets'},set(),'standing authorization')
    version(plan,'standing authorization');text(plan['authorization_id'],'authorization_id')
    text(plan['bridge_id'],'bridge_id')
    now=now_utc();expiry=timestamp(plan['expires_utc'],'expires_utc')
    if not now<expiry<=now+timedelta(days=30):
        raise WorkflowError('needs_input','Standing expiry must be in the next 30 days; no automatic renewal')
    if (type(plan['submission_limit']) is not int or not 1<=plan['submission_limit']<=100 or
            type(plan['runtime_minutes']) is not int or not 1<=plan['runtime_minutes']<=60 or
            len(plan['bridge_id'])>128):
        raise ContractError('Standing scope requires 1..100 submissions and 1..60 runtime minutes')
    if not isinstance(plan['targets'],list) or not 1<=len(plan['targets'])<=50:
        raise ContractError('targets: name 1..50 explicit employers and destination prefixes')
    profile=work.confirmed_profile();seen=set()
    for target in plan['targets']:
        object_fields(target,{'employer','destination_prefix','operations','answers','consents'},set(),'standing target')
        text(target['employer'],'employer');safe_url(target['destination_prefix'],'destination_prefix',True)
        identity=(target['employer'].casefold(),target['destination_prefix'])
        if identity in seen:raise ContractError('Duplicate standing recipient scope')
        seen.add(identity);operations(target['operations'],'operations')
        if 'submit' not in target['operations']:
            raise ContractError('Standing auto-apply targets must explicitly include submit')
        work.validate_answers({**target,'required_answers':[]},profile['profile'])
    grant={**plan,'candidate_id':profile['profile']['candidate_id'],
           'profile_fingerprint':profile['fingerprint'],'actor':work.actor}
    fingerprint=canonical_hash(grant)
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE')
        if work.confirmed_profile()['fingerprint']!=profile['fingerprint'] or now_utc()>=expiry:
            raise WorkflowError('blocked','Profile or expiry changed during authorization preparation')
        db.execute('INSERT OR IGNORE INTO campaign_authorizations VALUES(?,?,NULL,NULL,NULL,?)',
                   (fingerprint,json.dumps(grant,ensure_ascii=False),utc_now()))
        work._event(db,'standing_authorization_prepared',fingerprint,'requires actual user approval');db.commit()
        existing=db.execute('SELECT approved_utc,revoked_utc FROM campaign_authorizations WHERE fingerprint=?',(fingerprint,)).fetchone()
    path=work.atomic_text('authorizations/'+fingerprint+'.json',json.dumps(grant,ensure_ascii=False,indent=2))
    return Outcome('ok',{'fingerprint':fingerprint,'authorization':grant,'file':work.file_record(path),
                        'approved':bool(existing['approved_utc'] and not existing['revoked_utc'])},
                   ['Creation alone grants no authority; record actual scoped user approval.'])


def current(work, fingerprint, approved=True):
    require_schema(work);text(fingerprint,'authorization fingerprint')
    with work._db() as db:
        row=db.execute('SELECT * FROM campaign_authorizations WHERE fingerprint=?',(fingerprint,)).fetchone()
    if not row:raise WorkflowError('needs_input','Unknown standing authorization')
    grant=json.loads(row['payload'])
    exported=work.inside('authorizations/'+fingerprint+'.json')
    if (canonical_hash(grant)!=fingerprint or not exported.is_file() or
            canonical_hash(work.private_json(exported))!=fingerprint):
        raise WorkflowError('blocked','Standing authorization or its review copy changed')
    if row['revoked_utc'] or (approved and not row['approved_utc']):
        raise WorkflowError('blocked','Standing authorization is unapproved or revoked')
    if now_utc()>=timestamp(grant['expires_utc'],'standing expiry'):
        raise WorkflowError('blocked','Standing authorization expired; obtain a fresh scoped decision')
    profile=work.confirmed_profile()
    if (grant['actor']!=work.actor or grant['candidate_id']!=profile['profile']['candidate_id'] or
            grant['profile_fingerprint']!=profile['fingerprint']):
        raise WorkflowError('blocked','Standing candidate, profile or coordinator changed')
    if now_utc()>=timestamp(grant['expires_utc'],'standing expiry'):
        raise WorkflowError('blocked','Standing authorization expired during profile validation')
    return grant


def approve(work, fingerprint, confirmation):
    current(work,fingerprint,False)
    proof=Path(confirmation).resolve(strict=True)
    if (not proof.is_relative_to(work.data_dir) or proof.stat().st_size>1024 or
            proof.read_text(encoding='utf-8-sig').strip()!='APPROVE AUTHORIZATION '+fingerprint):
        raise WorkflowError('blocked','Exact standing approval proof must match the reviewed scope inside this workspace')
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE');current(work,fingerprint,False)
        db.execute('UPDATE campaign_authorizations SET approved_utc=? WHERE fingerprint=?',(utc_now(),fingerprint))
        work._event(db,'standing_authorization_approved',fingerprint,'actual approval required; human provenance not authenticated');db.commit()
    return Outcome('ok',{'fingerprint':fingerprint,'approved':True},[])


def link(work, fingerprint):
    with work._db() as db:
        if db.execute('PRAGMA user_version').fetchone()[0]<4:return None
        row=db.execute('SELECT * FROM manifest_authorizations WHERE fingerprint=?',(fingerprint,)).fetchone()
    return dict(row) if row else None


def qualified_assessments(work, manifest):
    with work._db() as db:
        for entry in manifest['entries']:
            assessment=db.execute('SELECT * FROM assessments WHERE job_id=?',(entry['job_id'],)).fetchone()
            if (not assessment or assessment['profile_fingerprint']!=manifest['profile_fingerprint'] or
                    assessment['job_fingerprint']!=entry['job_fingerprint'] or
                    json.loads(assessment['payload'])['classification'] not in {'Strong fit','Plausible fit'}):
                raise WorkflowError('manual_required','Standing automation requires a current Strong/Plausible assessment')


def check_link(work, fingerprint, manifest):
    linked=link(work,fingerprint)
    if not linked:return None
    current(work,linked['authorization_fingerprint'])
    qualified_assessments(work,manifest)
    return {'approval_basis':'standing_authorization',
            'authorization_fingerprint':linked['authorization_fingerprint']}


def matches(entry, target):
    actual=safe_url(entry['destination'],'destination')
    allowed=safe_url(target['destination_prefix'],'destination_prefix',True)
    return (entry['employer'].casefold()==target['employer'].casefold() and
            (actual.scheme,actual.hostname,actual.port,actual.query)==
            (allowed.scheme,allowed.hostname,allowed.port,allowed.query) and
            actual.path.startswith(allowed.path) and
            set(entry['operations'])<=set(target['operations']) and
            all(target['answers'].get(key)==answer for key,answer in entry['answers'].items()) and
            all(consent in target['consents'] for consent in entry['consents']))


def derive(work, fingerprint, authorization_fingerprint):
    require_schema(work)
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE')
        grant=current(work,authorization_fingerprint)
        manifest=work.current_manifest(fingerprint)
        linked=link(work,fingerprint)
        if linked:
            if linked['authorization_fingerprint']!=authorization_fingerprint:
                raise WorkflowError('blocked','This manifest is already bound to another standing scope')
            db.commit();return work.check_manifest(fingerprint)
        if db.execute('SELECT 1 FROM campaign_approvals WHERE fingerprint=?',(fingerprint,)).fetchone():
            raise WorkflowError('blocked','Existing exact/revoked approval cannot be rewritten as standing authority')
        if (manifest['mode']!='APPROVED_BATCH' or not manifest.get('execution_enabled') or manifest['execution']['bridge_id']!=grant['bridge_id'] or
                manifest['execution']['runtime_minutes']>grant['runtime_minutes'] or
                timestamp(manifest['expires_utc'],'manifest expiry')>timestamp(grant['expires_utc'],'standing expiry')):
            raise WorkflowError('blocked','Manifest exceeds standing bridge, runtime or expiry')
        qualified_assessments(work,manifest)
        for entry in manifest['entries']:
            if work.current_draft(entry['job_id'])['classification'] not in {'Strong fit','Plausible fit'}:
                raise WorkflowError('manual_required','Standing automation requires current Strong/Plausible fit')
            if not any(matches(entry,target) for target in grant['targets']):
                raise WorkflowError('needs_input','New recipient, destination, answer, consent or operation needs a scoped user decision')
        allocated=db.execute('SELECT COALESCE(sum(allocated_submissions),0) FROM manifest_authorizations WHERE authorization_fingerprint=?',
                             (authorization_fingerprint,)).fetchone()[0]
        if allocated+manifest['submission_limit']>grant['submission_limit']:
            raise WorkflowError('blocked','Standing application budget is fully allocated; cancelled/expired batches do not refund it')
        # Recheck after potentially long all-entry document/fit validation.
        current(work,authorization_fingerprint)
        if now_utc()>=timestamp(manifest['expires_utc'],'manifest expiry'):
            raise WorkflowError('blocked','Manifest expired during authorization')
        db.execute('INSERT INTO manifest_authorizations VALUES(?,?,?)',
                   (fingerprint,authorization_fingerprint,manifest['submission_limit']))
        db.execute('INSERT INTO campaign_approvals VALUES(?,?,NULL,NULL)',(fingerprint,utc_now()))
        work._event(db,'manifest_authorized_by_standing_scope',fingerprint,authorization_fingerprint);db.commit()
    return work.check_manifest(fingerprint)


def revoke(work, fingerprint, reason):
    require_schema(work);text(reason,'reason')
    with work._db() as db:
        db.execute('BEGIN IMMEDIATE')
        changed=db.execute('UPDATE campaign_authorizations SET revoked_utc=?,reason=? WHERE fingerprint=? AND revoked_utc IS NULL',
                           (utc_now(),reason,fingerprint)).rowcount
        if not changed:raise WorkflowError('needs_input','No unrevoked standing scope with this fingerprint')
        work._event(db,'standing_authorization_revoked',fingerprint,reason);db.commit()
    return Outcome('ok',{'fingerprint':fingerprint,'revoked':True},[])


def check(work, fingerprint):
    grant=current(work,fingerprint)
    with work._db() as db:
        allocated=db.execute('SELECT COALESCE(sum(allocated_submissions),0) FROM manifest_authorizations WHERE authorization_fingerprint=?',
                             (fingerprint,)).fetchone()[0]
    return Outcome('ok',{'fingerprint':fingerprint,'approved':True,
        'expires_utc':grant['expires_utc'],'submission_limit':grant['submission_limit'],
        'allocated_submissions':allocated,'remaining_unallocated':grant['submission_limit']-allocated},
        ['Allocated limits are not confirmed application counts. Host/tool confirmations remain separate.'])
