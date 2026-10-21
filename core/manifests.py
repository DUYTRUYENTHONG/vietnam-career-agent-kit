"""Finite, expiring local approval records. No browser or submit executor."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from .contracts import ContractError, Outcome, choice, object_fields, strings, text, version
from .documents import Documents
from .ledger import _https, canonical_hash, utc_now
from .workflow import WorkflowError

OPERATIONS={'fill','upload','submit'}


def now_utc():return datetime.now(timezone.utc)


def timestamp(value,label):
    text(value,label)
    try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as error:raise ContractError(label+': expected an ISO timestamp') from error
    if parsed.tzinfo is None or parsed.utcoffset()!=timedelta(0):
        raise ContractError(label+': supply an explicit UTC timestamp')
    return parsed


def operations(value,label):
    strings(value,label)
    if not value or not set(value)<=OPERATIONS:raise ContractError(label+': choose fill/upload/submit')


class Campaign(Documents):
    def validate_answers(self,entry,profile):
        answers=entry['answers']
        if not isinstance(answers,dict):raise ContractError('answers: expected an object')
        strings(entry['required_answers'],'required_answers')
        if not set(entry['required_answers'])<=answers.keys():
            raise WorkflowError('needs_input','Required screening answers are missing; do not guess')
        facts={f['id']:f for f in profile['facts'] if f['status']=='confirmed'}
        for question,answer in answers.items():
            text(question,'answer question')
            object_fields(answer,{'value','source','fact_ids','kind'},set(),'answer')
            if answer['kind']!='ordinary':
                raise WorkflowError('manual_required','Legal/sensitive declarations require direct user action and are outside this manifest')
            choice(answer['source'],{'profile_fact','candidate_confirmed'},'answer.source')
            strings(answer['fact_ids'],'answer.fact_ids')
            if type(answer['value']) is not bool:text(answer['value'],'answer.value')
            if answer['source']=='profile_fact':
                if (not answer['fact_ids'] or any(i not in facts for i in answer['fact_ids']) or
                        not any(answer['value']==facts[i]['value'] for i in answer['fact_ids'])):
                    raise WorkflowError('blocked','Profile-derived answer needs exact current confirmed evidence')
            elif answer['fact_ids']:
                raise ContractError('Candidate-confirmed answers do not fabricate profile evidence IDs')
        if not isinstance(entry['consents'],list):raise ContractError('consents: expected a list')
        seen=set()
        for consent in entry['consents']:
            object_fields(consent,{'id','text','choice'},set(),'consent')
            text(consent['id'],'consent.id');text(consent['text'],'consent.text')
            if type(consent['choice']) is not bool or consent['id'] in seen:
                raise ContractError('consent: unique IDs and explicit boolean choices required')
            seen.add(consent['id'])

    def validate_policy(self,entry,now):
        destination=_https(entry['destination'],'destination')
        policy=object_fields(entry['policy'],{'permission','source','checked_utc','allowed_operations'},set(),'policy')
        if policy['permission']!='permitted':
            raise WorkflowError('manual_required','Unknown/manual write permission cannot become approved automation; provide a manual handoff')
        source=_https(policy['source'],'policy.source')
        if (source.hostname,source.port)!=(destination.hostname,destination.port):
            raise WorkflowError('blocked','Permission evidence must identify this exact destination host and port')
        checked=timestamp(policy['checked_utc'],'policy.checked_utc')
        if not now-timedelta(days=7)<=checked<=now:
            raise WorkflowError('needs_input','Permission evidence is future-dated or older than seven days; review it again')
        operations(entry['operations'],'operations');operations(policy['allowed_operations'],'policy.allowed_operations')
        if not set(entry['operations'])<=set(policy['allowed_operations']):
            raise WorkflowError('blocked','Requested operations exceed the recorded source permission')

    def create_manifest(self,raw):
        plan=object_fields(raw,{'schema_version','campaign_id','mode','expires_utc','submission_limit','entries'},set(),'campaign plan')
        version(plan,'campaign plan');text(plan['campaign_id'],'campaign_id')
        choice(plan['mode'],{'ASSIST','APPROVED_BATCH'},'mode')
        now=now_utc();expiry=timestamp(plan['expires_utc'],'expires_utc')
        if not now<expiry<=now+timedelta(days=30):
            raise WorkflowError('needs_input','Expiry must be in the future and no more than 30 days away')
        entries=plan['entries'];limit=plan['submission_limit']
        if not isinstance(entries,list) or not 1<=len(entries)<=100:
            raise ContractError('entries: select a finite batch of 1-100 jobs')
        if (type(limit) is not int or (plan['mode']=='ASSIST' and limit!=0) or
                (plan['mode']=='APPROVED_BATCH' and not 1<=limit<=len(entries))):
            raise ContractError('submission_limit: ASSIST requires 0; APPROVED_BATCH requires 1..entry count')
        profile=self.confirmed_profile()
        rows=[];seen=set()
        for entry in entries:
            object_fields(entry,{'job_id','render_id','format','destination','operations','answers',
                'required_answers','consents','policy'},set(),'campaign entry')
            if type(entry['job_id']) is not int or entry['job_id']<1 or entry['job_id'] in seen:
                raise ContractError('entries: unique positive integer job IDs required')
            seen.add(entry['job_id']);text(entry['render_id'],'render_id')
            choice(entry['format'],{'docx','pdf'},'format')
            self.validate_policy(entry,now)
            if plan['mode']=='ASSIST' and 'submit' in entry['operations']:
                raise WorkflowError('blocked','ASSIST cannot authorize submit')
            if plan['mode']=='APPROVED_BATCH' and 'submit' not in entry['operations']:
                raise ContractError('APPROVED_BATCH entries must explicitly select submit')
            self.validate_answers(entry,profile['profile'])
            rendered=self.current_render(entry['render_id'])
            if rendered['job_id']!=entry['job_id'] or not rendered['reviewed']:
                raise WorkflowError('blocked','Select the same job and an exact fully reviewed document set')
            job=self.get_job(entry['job_id'])
            _,job_hash=self.job_document(entry['job_id'])
            document=rendered['files'][entry['format']]
            rows.append({**entry,'employer':job['employer'],'requisition':job['req_id'],
                'platform':job['platform'],'platform_job_id':job['platform_job_id'],
                'job_fingerprint':job_hash,'render_fingerprint':rendered['fingerprint'],
                'document':document,'document_sha256':document['sha256'],
                'answers_sha256':canonical_hash(entry['answers']),'consents_sha256':canonical_hash(entry['consents'])})
        manifest={**plan,'entries':rows,'candidate_id':profile['profile']['candidate_id'],
            'profile_fingerprint':profile['fingerprint'],'execution_enabled':False}
        fingerprint=canonical_hash(manifest)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if self.confirmed_profile()['fingerprint']!=profile['fingerprint']:
                raise WorkflowError('blocked','Candidate profile changed while preparing the manifest')
            for row in rows:self.current_render(row['render_id'])
            previous=db.execute('SELECT a.fingerprint,m.payload FROM campaign_approvals a JOIN campaign_manifests m USING(fingerprint) WHERE a.revoked_utc IS NULL AND a.fingerprint<>?',(fingerprint,)).fetchall()
            for old in previous:
                old_jobs={entry['job_id'] for entry in json.loads(old['payload'])['entries']}
                if seen.intersection(old_jobs):
                    db.execute('UPDATE campaign_approvals SET revoked_utc=?,reason=? WHERE fingerprint=?',
                        (utc_now(),'Superseded by a new overlapping manifest scope',old['fingerprint']))
                    self._event(db,'manifest_superseded',old['fingerprint'],fingerprint)
            db.execute('INSERT OR IGNORE INTO campaign_manifests VALUES(?,?,?)',
                (fingerprint,json.dumps(manifest,ensure_ascii=False),utc_now()))
            self._event(db,'manifest_prepared',fingerprint,'local finite scope; no external action')
            db.commit()
        path=self.atomic_text('manifests/'+fingerprint+'.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        with self._db() as db:
            existing=db.execute('SELECT revoked_utc FROM campaign_approvals WHERE fingerprint=?',(fingerprint,)).fetchone()
        return Outcome('ok',{'fingerprint':fingerprint,'manifest':manifest,'file':self.file_record(path),
            'approved':bool(existing and existing['revoked_utc'] is None),'execution_enabled':False},[])

    def current_manifest(self,fingerprint):
        text(fingerprint,'fingerprint')
        with self._db() as db:
            row=db.execute('SELECT * FROM campaign_manifests WHERE fingerprint=?',(fingerprint,)).fetchone()
        if not row:raise WorkflowError('needs_input','Unknown manifest fingerprint; create and review an exact finite manifest')
        manifest=json.loads(row['payload'])
        if canonical_hash(manifest)!=fingerprint:raise WorkflowError('blocked','Manifest integrity check failed')
        exported=self.inside('manifests/'+fingerprint+'.json')
        if not exported.is_file() or canonical_hash(self.private_json(exported))!=fingerprint:
            raise WorkflowError('blocked','Manifest review file changed or disappeared; create/review the exact scope again')
        now=now_utc()
        if now>=timestamp(manifest['expires_utc'],'expires_utc'):
            raise WorkflowError('blocked','Manifest expired; review a new finite scope')
        profile=self.confirmed_profile()
        if profile['fingerprint']!=manifest['profile_fingerprint'] or profile['profile']['candidate_id']!=manifest['candidate_id']:
            raise WorkflowError('blocked','Manifest candidate/profile changed')
        for entry in manifest['entries']:
            rendered=self.current_render(entry['render_id'])
            self.validate_policy(entry,now)
            if not rendered['reviewed'] or rendered['fingerprint']!=entry['render_fingerprint']:
                raise WorkflowError('blocked','Manifest document review is absent/stale')
        return manifest

    def approve_manifest(self,fingerprint,confirmation):
        self.current_manifest(fingerprint)
        file=Path(confirmation).resolve(strict=True)
        if (not file.is_relative_to(self.data_dir) or file.stat().st_size>1024 or
                file.read_text(encoding='utf-8-sig').strip()!='APPROVE MANIFEST '+fingerprint):
            raise WorkflowError('blocked','Exact approval proof must be inside this private workspace and match the reviewed manifest fingerprint')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE');self.current_manifest(fingerprint)
            previous=db.execute('SELECT revoked_utc FROM campaign_approvals WHERE fingerprint=?',(fingerprint,)).fetchone()
            if previous and previous['revoked_utc'] is not None:
                raise WorkflowError('blocked','Revoked/superseded scope cannot reuse an old confirmation; create and review a new manifest with a fresh expiry')
            db.execute('INSERT OR REPLACE INTO campaign_approvals VALUES(?,?,NULL,NULL)',(fingerprint,utc_now()))
            self._event(db,'manifest_approved',fingerprint,'local bookkeeping; human provenance not authenticated; execution unavailable')
            db.commit()
        return self.check_manifest(fingerprint)

    def check_manifest(self,fingerprint,intent=None):
        manifest=self.current_manifest(fingerprint)
        with self._db() as db:
            approval=db.execute('SELECT * FROM campaign_approvals WHERE fingerprint=?',(fingerprint,)).fetchone()
        if not approval or approval['revoked_utc']:
            raise WorkflowError('blocked','No current explicit approval for this exact manifest')
        if intent is not None:
            keys={'job_id','destination','action','document_sha256','answers_sha256','consents_sha256'}
            object_fields(intent,keys,set(),'disclosure intent')
            choice(intent['action'],OPERATIONS,'intent.action')
            entry=next((r for r in manifest['entries'] if type(intent['job_id']) is int and r['job_id']==intent['job_id']),None)
            if (not entry or intent['action'] not in entry['operations'] or
                    any(intent[key]!=entry[key] for key in keys-{'action'})):
                raise WorkflowError('blocked','Intent differs from the approved job, destination, CV, answers, consents or operation')
        return Outcome('ok',{'fingerprint':fingerprint,'approved':True,'execution_enabled':False,
            'mode':manifest['mode'],'submission_limit':manifest['submission_limit'],'expires_utc':manifest['expires_utc']},
            ['Local approval validation only. Browser/attempt execution and submission-limit consumption are not implemented.'])

    def revoke_manifest(self,fingerprint,reason):
        text(reason,'reason')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('UPDATE campaign_approvals SET revoked_utc=?,reason=? WHERE fingerprint=? AND revoked_utc IS NULL',
                (utc_now(),reason,fingerprint)).rowcount
            if not changed:raise WorkflowError('needs_input','No unrevoked approval for this fingerprint')
            self._event(db,'manifest_revoked',fingerprint,reason);db.commit()
        return Outcome('ok',{'fingerprint':fingerprint,'revoked':True,'execution_enabled':False},[])

    def resume(self):
        result=super().resume()
        with self._db() as db:
            if db.execute('PRAGMA user_version').fetchone()[0]<2:return result
            renders=db.execute('SELECT id FROM document_sets ORDER BY created_utc').fetchall()
            manifests=db.execute('SELECT fingerprint FROM campaign_manifests ORDER BY created_utc').fetchall()
        document_status=[]
        for row in renders:
            try:
                item=self.current_render(row['id'])
                document_status.append({'render_id':row['id'],'job_id':item['job_id'],'reviewed':item['reviewed'],'stale':False})
            except (WorkflowError,OSError,ValueError) as error:
                document_status.append({'render_id':row['id'],'stale':True,'issues':[str(error)]})
        approvals=[]
        for row in manifests:
            try:
                self.check_manifest(row['fingerprint'])
                approvals.append({'fingerprint':row['fingerprint'],'approved':True,'execution_enabled':False})
            except (WorkflowError,OSError,ValueError) as error:
                approvals.append({'fingerprint':row['fingerprint'],'approved':False,'issues':[str(error)]})
        result.data.update({'document_sets':document_status,'manifests':approvals})
        return result
