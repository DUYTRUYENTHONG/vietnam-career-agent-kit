"""Preparation operations over the existing canonical SQLite ledger."""
from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .contracts import (ContractError, Outcome, choice, normalize_city, object_fields,
                        strings, text, validate_job, validate_profile, version)
from .ledger import Kit, _key, canonical_hash, utc_now


class WorkflowError(ValueError):
    def __init__(self, outcome: str, message: str):
        super().__init__(message)
        self.outcome = outcome


class Preparation(Kit):
    """Local-only, one-candidate preparation. Does not operate a browser."""

    def duplicate_candidates(self, job_id: int) -> Outcome:
        """Read same-employer identity hints without merging or validating artifacts."""
        if type(job_id) is not int or job_id <= 0:
            raise WorkflowError('needs_input', 'Use a positive local job ID')
        with self._db() as db:
            db.execute('BEGIN')
            job = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if job is None:
                raise WorkflowError('needs_input', 'Unknown local job ID')
            rows = db.execute('SELECT * FROM jobs WHERE employer_key=? AND id<>? ORDER BY id',
                              (job['employer_key'], job_id)).fetchall()
        candidates = []
        city, title = normalize_city(job['city']), _key(job['title'])
        for row in rows:
            signals = []
            if row['url'] == job['url']:
                signals.append('same_url')
            if city and city == normalize_city(row['city']) and title == _key(row['title']):
                signals.append('same_employer_title_city')
            if signals:
                candidate = {key: row[key] for key in ('id', 'platform', 'platform_job_id',
                             'req_id', 'title', 'city', 'url', 'state', 'liveness')}
                candidate['signals'] = signals
                candidate['prior_attempt_needs_reconciliation'] = row['state'] in {
                    'confirmed_submitted', 'user_reported_submitted', 'submission_uncertain'}
                candidates.append(candidate)
        return Outcome('ok', {'job_id': job_id, 'candidates': candidates,
            'requires_identity_review': bool(candidates), 'deduplication_complete': False,
            'external_history_checked': False, 'external_actions': 0,
            'scope': 'Recorded same-employer hints only; no identity proof, live checks or artifact validation.'},
            ['Verify requisitions and prior receipts before another application; distinct jobs can share a title or URL.']
            if candidates else [])

    def init(self, language: str = 'en') -> Outcome:
        choice(language, {'en', 'vi'}, 'language')
        for parent in self.data_dir.parents:
            if (parent/'workflow.sqlite3').exists():
                raise WorkflowError('blocked', 'Choose a separate workspace, not a directory inside another candidate workspace')
        if self.db_path.exists():
            with self._db() as db:
                current = db.execute('PRAGMA user_version').fetchone()[0]
                if current > 4:
                    raise WorkflowError('blocked', 'Workspace schema is newer than this toolkit; use a compatible version')
        super().init()
        statements = [
            'CREATE TABLE IF NOT EXISTS workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS evidence_sources(id TEXT PRIMARY KEY,path TEXT NOT NULL,sha256 TEXT NOT NULL,original_name TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS candidate_profile(id INTEGER PRIMARY KEY CHECK(id=1),candidate_id TEXT NOT NULL,payload TEXT NOT NULL,fingerprint TEXT NOT NULL,confirmed_fingerprint TEXT,updated_utc TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS job_documents(job_id INTEGER PRIMARY KEY REFERENCES jobs(id),payload TEXT NOT NULL,fingerprint TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS assessments(job_id INTEGER PRIMARY KEY REFERENCES jobs(id),payload TEXT NOT NULL,profile_fingerprint TEXT NOT NULL,job_fingerprint TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS drafts(id INTEGER PRIMARY KEY,job_id INTEGER NOT NULL REFERENCES jobs(id),payload TEXT NOT NULL,profile_fingerprint TEXT NOT NULL,job_fingerprint TEXT NOT NULL,created_utc TEXT NOT NULL)',
        ]
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            for statement in statements:
                db.execute(statement)
            db.execute('INSERT OR IGNORE INTO workspace_meta VALUES(?,?)', ('language', language))
            if db.execute('PRAGMA user_version').fetchone()[0]<1:
                db.execute('PRAGMA user_version=1')
            self._event(db, 'workspace_initialized', 'workspace', 'schema1 additive; no external operations')
            db.commit()
        return Outcome('ok', {'workspace':str(self.data_dir),'schema':1,'language':self.language()}, [],
                       'Đã khởi tạo không gian riêng.' if self.language()=='vi' else 'Private workspace initialized.')

    def language(self) -> str:
        with self._db() as db:
            row=db.execute("SELECT value FROM workspace_meta WHERE key='language'").fetchone()
        return row[0] if row else 'en'

    def inside(self, relative: str) -> Path:
        path=(self.data_dir/relative).resolve()
        if not path.is_relative_to(self.data_dir):
            raise WorkflowError('blocked', 'Private output/evidence path escapes its selected workspace')
        return path

    def atomic_text(self, relative: str, content: str) -> Path:
        target=self.inside(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf8',newline='',dir=target.parent,delete=False) as stream:
            stream.write(content)
            temporary=Path(stream.name)
        try:
            os.replace(temporary,target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def import_cv(self, path: str | Path, source_id: str) -> Outcome:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',source_id):
            raise ContractError('source_id: use 1-64 letters, digits, underscores or hyphens, starting with a letter')
        file=Path(path).resolve(strict=True)
        if file.suffix.lower() not in {'.txt','.md'}:
            return Outcome('manual_required', {'supported':['.txt','.md']},
                           ['PDF/DOCX extraction is not implemented in Slice 1; supply an authorized UTF-8 text copy.'])
        if file.stat().st_size>2_000_000:
            raise WorkflowError('blocked','Text evidence exceeds 2 MB; import a relevant authorized excerpt')
        content=file.read_text(encoding='utf-8-sig')
        if not content.strip() or '\x00' in content:
            raise ContractError('CV: empty or binary input; provide nonempty UTF-8 text')
        digest=hashlib.sha256(content.encode('utf8')).hexdigest()
        relative=f'evidence/{digest}.txt'
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT sha256 FROM evidence_sources WHERE id=?',(source_id,)).fetchone()
            if old and old[0]!=digest:
                raise WorkflowError('blocked','Source ID already names different bytes; import the revision with a new source ID')
            self.atomic_text(relative,content)
            db.execute('INSERT OR IGNORE INTO evidence_sources VALUES(?,?,?,?)',(source_id,relative,digest,file.name))
            self._event(db,'evidence_imported',source_id,digest)
            db.commit()
        return Outcome('ok',{'source_id':source_id,'path':relative,'sha256':digest},[])

    def _sources(self, payload: dict) -> list[dict]:
        ids=sorted({fact['source_id'] for fact in payload['facts']})
        sources=[]
        with self._db() as db:
            for source_id in ids:
                row=db.execute('SELECT * FROM evidence_sources WHERE id=?',(source_id,)).fetchone()
                if row is None:
                    raise WorkflowError('needs_input','Import the referenced CV/evidence source first: '+source_id)
                source=dict(row)
                path=self.inside(source['path'])
                if not path.is_file() or self.hash_file(path)!=source['sha256']:
                    raise WorkflowError('blocked','Imported source bytes changed or disappeared: '+source_id)
                sources.append(source)
        source_text={s['id']:self.inside(s['path']).read_text(encoding='utf8') for s in sources}
        for fact in payload['facts']:
            if fact['quote'] not in source_text[fact['source_id']]:
                raise WorkflowError('blocked','Fact quote is absent from imported source: '+fact['id'])
        return sources

    @staticmethod
    def conflicts(payload: dict) -> list[str]:
        groups:dict[str,set[str]]={}
        for fact in payload['facts']:
            if fact.get('conflict_key') and fact['status']!='rejected':
                groups.setdefault(fact['conflict_key'],set()).add(fact['value'])
        return sorted(key for key,values in groups.items() if len(values)>1)

    def import_profile(self, raw: Any) -> Outcome:
        payload=validate_profile(raw)
        sources=self._sources(payload)
        fingerprint=canonical_hash({'profile':payload,'sources':sources})
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM candidate_profile WHERE id=1').fetchone()
            if old and old['candidate_id']!=payload['candidate_id']:
                raise WorkflowError('blocked','A workspace selects one candidate; initialize a separate workspace for another person')
            confirmation=old['confirmed_fingerprint'] if old and old['fingerprint']==fingerprint else None
            db.execute('INSERT OR REPLACE INTO candidate_profile VALUES(1,?,?,?,?,?)',
                (payload['candidate_id'],json.dumps(payload,ensure_ascii=False),fingerprint,confirmation,utc_now()))
            if old and old['fingerprint']!=fingerprint:
                db.execute("UPDATE approvals SET invalidated_utc=?,reason='candidate_changed' WHERE invalidated_utc IS NULL",(utc_now(),))
            self._event(db,'profile_imported',payload['candidate_id'],fingerprint)
            db.commit()
        return self.inspect_profile()

    def inspect_profile(self) -> Outcome:
        with self._db() as db:
            row=db.execute('SELECT * FROM candidate_profile WHERE id=1').fetchone()
        if row is None:
            return Outcome('needs_input',{},['Import one profile after its CV/evidence sources.'])
        payload=validate_profile(json.loads(row['payload']))
        sources=self._sources(payload)
        fingerprint=canonical_hash({'profile':payload,'sources':sources})
        conflicts=self.conflicts(payload)
        confirmed=fingerprint==row['confirmed_fingerprint'] and not conflicts
        return Outcome('ok' if confirmed else 'needs_input',
            {'profile':payload,'sources':sources,'fingerprint':fingerprint,'confirmed':confirmed,'conflicts':conflicts},
            [] if confirmed else ['Resolve conflicting facts, then explicitly confirm this exact profile fingerprint.'])

    def confirm_profile(self, fingerprint: str, confirmation_file: str | Path) -> Outcome:
        current=self.inspect_profile()
        if not current.data or current.data['conflicts']:
            raise WorkflowError('needs_input','A complete profile without unresolved conflict groups is required')
        proof=Path(confirmation_file).resolve(strict=True)
        if not proof.is_relative_to(self.data_dir):
            raise WorkflowError('blocked','Profile confirmation file must be inside the selected private workspace')
        if fingerprint!=current.data['fingerprint'] or proof.read_text(encoding='utf8').strip()!='CONFIRM PROFILE '+fingerprint:
            raise WorkflowError('blocked','Stale/mismatched profile confirmation; review the current fingerprint')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            cursor=db.execute('UPDATE candidate_profile SET confirmed_fingerprint=? WHERE id=1 AND fingerprint=?',
                             (fingerprint,fingerprint))
            if cursor.rowcount!=1:
                raise WorkflowError('blocked','Profile changed during confirmation; re-review it')
            self._event(db,'profile_confirmed',current.data['profile']['candidate_id'],'local bookkeeping; human provenance not authenticated')
            db.commit()
        return self.inspect_profile()

    def confirmed_profile(self) -> dict:
        result=self.inspect_profile()
        if result.outcome!='ok':
            raise WorkflowError('needs_input','Confirm the exact current profile before assessment or tailoring')
        return result.data

    def import_job(self, raw: Any) -> Outcome:
        payload=validate_job(raw)
        row=self.add_job(**{key:payload[key] for key in ('platform','platform_job_id','employer',
            'req_id','title','url','city','raw_jd','readable','liveness')})
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR REPLACE INTO job_documents VALUES(?,?,?)',
                       (row['id'],json.dumps(payload,ensure_ascii=False),canonical_hash(payload)))
            self._event(db,'structured_jd_imported',row['id'],canonical_hash(payload))
            db.commit()
        return Outcome('ok',{'job':row,'normalized_city':normalize_city(payload['city']),
            'salary':payload['salary'],'source_mode':'manual structured import; no website accessed'},[])

    def job_document(self, job_id: int) -> tuple[dict, str]:
        if type(job_id) is not int or job_id<1:
            raise ContractError('job_id: expected a positive integer')
        current=self.get_job(job_id)
        with self._db() as db:
            row=db.execute('SELECT * FROM job_documents WHERE job_id=?',(job_id,)).fetchone()
        if row is None:
            raise WorkflowError('needs_input','Import a complete versioned JD for this legacy job before assessment')
        payload=validate_job(json.loads(row['payload']))
        content=self.inside(current['raw_jd_path']).read_text(encoding='utf8')
        fields=('employer','req_id','title','url','city','readable','liveness')
        if (content!=payload['raw_jd'] or canonical_hash(payload)!=row['fingerprint'] or
                any(current[key]!=payload[key] for key in fields)):
            raise WorkflowError('needs_input','JD changed outside its structured snapshot; reimport and reassess')
        return payload,row['fingerprint']

    def assess(self, job_id: int, raw: Any) -> Outcome:
        profile=self.confirmed_profile()
        job,job_hash=self.job_document(job_id)
        matrix=object_fields(raw,{'schema_version','rows'},set(),'matrix')
        version(matrix,'matrix')
        requirements={req['id']:req for req in job['requirements']}
        if not isinstance(matrix['rows'],list) or not matrix['rows']:
            raise ContractError('matrix.rows: cover every JD requirement exactly once')
        facts={fact['id']:fact for fact in profile['profile']['facts']}
        rows=[]
        seen=set()
        for entry in matrix['rows']:
            object_fields(entry,{'requirement_id','match','fact_ids','reason'},set(),'matrix row')
            text(entry['requirement_id'],'requirement_id')
            if entry['requirement_id'] not in requirements or entry['requirement_id'] in seen:
                raise ContractError('matrix: unknown or duplicate requirement ID')
            seen.add(entry['requirement_id'])
            choice(entry['match'],{'direct','partial','missing','unknown'},'match')
            text(entry['reason'],'reason')
            strings(entry['fact_ids'],'fact_ids')
            linked=[]
            for fact_id in entry['fact_ids']:
                if fact_id not in facts or facts[fact_id]['status']!='confirmed':
                    raise WorkflowError('blocked','Evidence link is missing, rejected or unconfirmed: '+fact_id)
                linked.append(facts[fact_id])
            req=requirements[entry['requirement_id']]
            if entry['match'] in {'direct','partial'} and not linked:
                raise WorkflowError('blocked','A direct/partial match needs confirmed evidence')
            if entry['match'] in {'missing','unknown'} and linked:
                raise ContractError('Missing/unknown rows do not assert evidence links; use partial with an explicit limitation')
            if entry['match']=='direct' and not any(
                    fact['field'].casefold()==req['field'].casefold() and
                    fact['value'].casefold()==req['value'].casefold() for fact in linked):
                raise WorkflowError('blocked','A direct match needs the same reviewed field/value; semantic equivalence must be reviewed explicitly')
            rows.append({**entry,'requirement':req,'evidence':linked})
        if seen!=requirements.keys():
            raise ContractError('matrix: missing requirements '+', '.join(sorted(requirements.keys()-seen)))
        prefs=profile['profile']['preferences']
        constraints=[]
        classification='Strong fit'
        if any(row['match']!='direct' for row in rows):classification='Plausible fit'
        if any(row['requirement']['mandatory'] and row['match'] in {'partial','missing'} for row in rows):classification='Stretch'
        if any(row['requirement']['mandatory'] and row['match']=='unknown' for row in rows):classification='Needs clarification'
        if any(row['requirement']['mandatory'] and row['requirement']['hard'] and row['match']=='missing' for row in rows):classification='Ineligible'
        if job['liveness']=='unverified':classification='Needs clarification'
        if job['country'].upper()!='VN' or job['liveness']=='closed':classification='Ineligible'
        if job['employer'].casefold() in [x.casefold() for x in prefs.get('excluded_employers') or []]:
            constraints.append('Explicit employer exclusion');classification='Ineligible'
        if (job.get('industry') or '').casefold() in [x.casefold() for x in prefs.get('excluded_industries') or []]:
            constraints.append('Explicit industry exclusion');classification='Ineligible'
        for pref,field in [('work_models','work_model'),('employment_types','employment_type')]:
            allowed=prefs.get(pref)
            if allowed and job[field] not in allowed:
                constraints.append('Condition not in confirmed '+pref)
        cities=prefs.get('preferred_cities')
        if cities and normalize_city(job['city']) not in {normalize_city(city) for city in cities}:
            constraints.append('Different city; relocation/remote eligibility requires explicit review')
        expected_salary=prefs.get('salary') or {}
        if expected_salary.get('amount') is not None:
            if any(expected_salary.get(key) is None or job['salary'].get(key) is None for key in ('amount','currency','period','gross_net')):
                constraints.append('Salary expectation/posting has unknown basis; do not assume a match')
            elif any(expected_salary[key]!=job['salary'][key] for key in ('currency','period','gross_net')):
                constraints.append('Salary bases differ; no automatic conversion')
            elif job['salary']['amount']<expected_salary['amount']:
                constraints.append('Advertised amount below confirmed expectation')
        if constraints and classification!='Ineligible':classification='Needs clarification'
        history=prefs.get('existing_applications') or []
        identities={f"{job['platform']}:{job['platform_job_id']}",f"{job['employer']}:{job['req_id']}"}
        if identities.intersection(history):
            raise WorkflowError('blocked','Candidate reports this application already exists; reconcile it before preparing a duplicate')
        result={'classification':classification,'rows':rows,'constraints':constraints,
            'scope':'Evidence and explicitly set preferences only; no ATS probability or live eligibility verification',
            'profile_fingerprint':profile['fingerprint'],'job_fingerprint':job_hash}
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT state FROM jobs WHERE id=?',(job_id,)).fetchone()
            if current['state'] in {'confirmed_submitted','user_reported_submitted','submission_uncertain'}:
                raise WorkflowError('blocked','Existing submitted/uncertain application requires reconciliation, not another draft')
            db.execute('INSERT OR REPLACE INTO assessments VALUES(?,?,?,?)',
                (job_id,json.dumps(result,ensure_ascii=False),profile['fingerprint'],job_hash))
            db.execute("UPDATE jobs SET state='assessed',version=version+1,updated_utc=? WHERE id=?",(utc_now(),job_id))
            self._event(db,'fit_assessed',job_id,classification)
            db.commit()
        return Outcome('ok',result,[])

    @staticmethod
    def literal(value: str) -> str:
        return re.sub(r'([\\`*_[\]{}()#!|])',r'\\\1',html.escape(value))

    def prepare(self, job_id: int, raw: Any) -> Outcome:
        profile=self.confirmed_profile()
        job,job_hash=self.job_document(job_id)
        if self.get_job(job_id)['state'] in {'confirmed_submitted','user_reported_submitted','submission_uncertain'}:
            raise WorkflowError('blocked','Existing submitted/uncertain application requires reconciliation, not another draft')
        plan=object_fields(raw,{'schema_version','language','fact_ids'},set(),'draft plan')
        version(plan,'draft plan')
        choice(plan['language'],{'en','vi'},'draft language')
        strings(plan['fact_ids'],'draft fact_ids')
        if not plan['fact_ids']:
            raise ContractError('draft fact_ids: select at least one confirmed source fact')
        if job['document_language'] and plan['language']!=job['document_language']:
            raise WorkflowError('needs_input','Draft language differs from the employer document language; create a separate approved version')
        with self._db() as db:
            assessment=db.execute('SELECT * FROM assessments WHERE job_id=?',(job_id,)).fetchone()
        if (assessment is None or assessment['profile_fingerprint']!=profile['fingerprint'] or
                assessment['job_fingerprint']!=job_hash):
            raise WorkflowError('needs_input','Assessment is missing/stale; assess the current profile and JD first')
        match=json.loads(assessment['payload'])
        if job['liveness']!='active' or match['classification']=='Ineligible':
            raise WorkflowError('blocked','Closed/unverified/ineligible vacancy: resolve the assessment before tailoring')
        facts={fact['id']:fact for fact in profile['profile']['facts']}
        selected=[]
        for fact_id in plan['fact_ids']:
            if fact_id not in facts or facts[fact_id]['status']!='confirmed':
                raise WorkflowError('blocked','Draft contains unsupported/unconfirmed fact: '+fact_id)
            selected.append(facts[fact_id])
        vi=plan['language']=='vi'
        candidate=profile['profile']
        lit=self.literal
        lines=['# '+lit(candidate['name']),'',('Vị trí ứng tuyển: ' if vi else 'Target role: ')+lit(job['title']),'']
        for key,value in candidate.get('contacts',{}).items():
            if value:lines.append(lit(value))
        lines += ['',('## Kinh nghiệm và năng lực được chọn' if vi else '## Selected experience and capabilities'),'']
        lines += ['- '+lit(fact['claim']) for fact in selected]
        lines += ['']
        fingerprint=canonical_hash({'profile':profile['fingerprint'],'job':job_hash,'plan':plan})
        base=f'drafts/{job_id}/{fingerprint[:20]}'
        cv=self.atomic_text(base+'/cv.md','\n'.join(lines))
        mapping=self.atomic_text(base+'/source-map.json',json.dumps(selected,ensure_ascii=False,indent=2))
        files={name:{'path':str(path.relative_to(self.data_dir)).replace('\\','/'),'sha256':self.hash_file(path)}
               for name,path in [('cv',cv),('source_map',mapping)]}
        result={'job_id':job_id,'language':plan['language'],'classification':match['classification'],
                'files':files,'status':'review_required','approval':False,'rendered_pdf_docx':False,
                'profile_fingerprint':profile['fingerprint'],'job_fingerprint':job_hash}
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO drafts(job_id,payload,profile_fingerprint,job_fingerprint,created_utc) VALUES(?,?,?,?,?)',
                (job_id,json.dumps(result,ensure_ascii=False),profile['fingerprint'],job_hash,utc_now()))
            db.execute("UPDATE jobs SET state='review_required',version=version+1,updated_utc=? WHERE id=?",(utc_now(),job_id))
            self._event(db,'markdown_draft_created',job_id,fingerprint)
            db.commit()
        return Outcome('ok',result,[], 'Bản nháp cần được xem xét.' if vi else 'Draft requires review; no application performed.')

    def draft_status(self, draft, profile):
        """Validate one latest draft using the same rules as a full checkpoint."""
        payload=json.loads(draft['payload']) if draft else None
        stale=False
        if draft:
            try:
                _,job_hash=self.job_document(draft['job_id'])
                stale=(not profile.data.get('confirmed') or draft['profile_fingerprint']!=profile.data.get('fingerprint') or draft['job_fingerprint']!=job_hash)
                for file in payload['files'].values():
                    file_path=self.inside(file['path'])
                    stale=stale or not file_path.is_file() or self.hash_file(file_path)!=file['sha256']
            except (WorkflowError,OSError):
                stale=True
        return payload,stale

    def job_checkpoint(self, job_id):
        profile=self.inspect_profile()
        job=self.get_job(job_id)
        with self._db() as db:
            draft=db.execute('SELECT * FROM drafts WHERE job_id=? ORDER BY id DESC LIMIT 1',(job_id,)).fetchone()
        job['draft'],job['draft_stale']=self.draft_status(draft,profile)
        return job

    def resume(self) -> Outcome:
        profile=self.inspect_profile()
        with self._db() as db:
            jobs=[dict(row) for row in db.execute('SELECT * FROM jobs ORDER BY id')]
            drafts={row['job_id']:dict(row) for row in db.execute('SELECT * FROM drafts ORDER BY id')}
        for job in jobs:
            draft=drafts.get(job['id'])
            job['draft'],job['draft_stale']=self.draft_status(draft,profile)
        return Outcome('ok' if profile.outcome=='ok' else 'needs_input',
            {'candidate':profile.data.get('profile',{}).get('name'),'profile_confirmed':profile.data.get('confirmed',False),
             'jobs':jobs,'summary':self.status(),'mode':'PREPARE','external_actions':0},profile.issues,
            'Trạng thái được khôi phục; chưa gửi hồ sơ.' if self.language()=='vi' else 'Checkpoint loaded; no application inferred.')

    def handoff(self, job_id: int) -> Outcome:
        if self.get_job(job_id)['state'] in {'confirmed_submitted','user_reported_submitted','submission_uncertain'}:
            raise WorkflowError('blocked','Existing submitted/uncertain application must not receive another application handoff')
        row=self.job_checkpoint(job_id)
        if row is None or row['draft'] is None:
            raise WorkflowError('needs_input','Prepare a reviewed draft before creating a handoff')
        if row['draft_stale']:
            raise WorkflowError('blocked','Draft/profile/JD bytes changed; review and regenerate the affected package')
        return Outcome('manual_required',{'job_id':job_id,'employer':row['employer'],'source_url':row['url'],
            'application_destination':None,'documents':{'cv':row['draft']['files']['cv']},
            'review_artifacts':{key:value for key,value in row['draft']['files'].items() if key!='cv'},
            'approved':False,'submitted':False,
            'next_steps':['Review Markdown and source matrix; render the employer-required file format.',
                'Manually verify the actual application destination, vacancy and form questions.',
                'Approve exact disclosures/consents before any upload. No live browser adapter is enabled.']},
            ['Slice 1 provides a preparation handoff, not a completed application or approved batch.'])
