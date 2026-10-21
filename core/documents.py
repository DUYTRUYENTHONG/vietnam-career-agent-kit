"""Source-bound rendered documents and explicit local review records."""
import json
import os
from pathlib import Path
import tempfile
import uuid

from .contracts import Outcome, object_fields, text, version
from .ledger import canonical_hash, utc_now
from .rendering import render_files
from .workflow import Preparation, WorkflowError

TERMINAL={'confirmed_submitted','user_reported_submitted','submission_uncertain'}


class Documents(Preparation):
    def init(self, language='en'):
        super().init(language)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS document_sets(id TEXT PRIMARY KEY,job_id INTEGER NOT NULL REFERENCES jobs(id),payload TEXT NOT NULL,fingerprint TEXT NOT NULL,created_utc TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS document_reviews(render_id TEXT PRIMARY KEY REFERENCES document_sets(id),fingerprint TEXT NOT NULL,payload TEXT NOT NULL,recorded_utc TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS campaign_manifests(fingerprint TEXT PRIMARY KEY,payload TEXT NOT NULL,created_utc TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS campaign_approvals(fingerprint TEXT PRIMARY KEY REFERENCES campaign_manifests(fingerprint),approved_utc TEXT NOT NULL,revoked_utc TEXT,reason TEXT)')
            db.execute('PRAGMA user_version=2')
            db.commit()
        return Outcome('ok',{'workspace':str(self.data_dir),'schema':2,'language':self.language()},[])

    def current_draft(self, job_id):
        state=Preparation.resume(self)
        row=next((r for r in state.data['jobs'] if r['id']==job_id),None)
        if not row or not row['draft'] or row['draft_stale']:
            raise WorkflowError('needs_input','A current source-bound Markdown draft is required; prepare/review current evidence first')
        if row['state'] in TERMINAL or row['liveness']!='active':
            raise WorkflowError('blocked','Closed, submitted or uncertain job cannot receive a new render/approval')
        return row['draft']

    def content_model(self, job_id):
        draft=self.current_draft(job_id)
        profile=self.confirmed_profile()['profile']
        job,_=self.job_document(job_id)
        selected=json.loads(self.inside(draft['files']['source_map']['path']).read_text(encoding='utf8'))
        facts={f['id']:f for f in profile['facts'] if f['status']=='confirmed'}
        if not isinstance(selected,list) or not selected or any(facts.get(f.get('id'))!=f for f in selected):
            raise WorkflowError('blocked','Draft source map does not match current confirmed facts')
        vi=draft['language']=='vi'
        model={'schema_version':'1.0','candidate_id':profile['candidate_id'],'name':profile['name'],
            'language':draft['language'],'contacts':[v for v in profile.get('contacts',{}).values() if v],
            'headline':('Vị trí ứng tuyển: ' if vi else 'Target role: ')+job['title'],
            'section':'Kinh nghiệm và năng lực được chọn' if vi else 'Selected experience and capabilities',
            'fact_ids':[f['id'] for f in selected],'claims':[f['claim'] for f in selected],
            'draft_fingerprint':canonical_hash(draft),'profile_fingerprint':draft['profile_fingerprint'],
            'job_fingerprint':draft['job_fingerprint']}
        if sum(len(value) for value in [model['name'],model['headline'],*model['contacts'],*model['claims']])>50_000:
            raise WorkflowError('needs_input','Select a concise CV content set below 50,000 characters')
        return model

    def file_record(self,path):
        return {'path':path.relative_to(self.data_dir).as_posix(),'sha256':self.hash_file(path)}

    def render(self, job_id, soffice=None):
        content=self.content_model(job_id)
        render_id=uuid.uuid4().hex
        parent=self.inside('documents');parent.mkdir(exist_ok=True)
        target=parent/render_id
        with tempfile.TemporaryDirectory(prefix='building-',dir=parent) as temp:
            staging=Path(temp)
            (staging/'content.json').write_text(json.dumps(content,ensure_ascii=False,indent=2),encoding='utf8')
            try:result=render_files(content,staging,soffice)
            except WorkflowError:raise
            except Exception as error:
                raise WorkflowError('failed','Optional renderer/parser failed; no artifacts or approval were registered. Check the local tools and document content') from error
            if self.content_model(job_id)!=content:
                raise WorkflowError('blocked','Candidate/draft/JD changed while rendering; regenerate after review')
            os.replace(staging,target)
        payload={'render_id':render_id,'job_id':job_id,'content_hash':canonical_hash(content),
            'draft_fingerprint':content['draft_fingerprint'],'page_count':result['page_count'],
            'renderer':result['renderer'],
            'files':{key:self.file_record(target/name) for key,name in
                [('docx','cv.docx'),('pdf','cv.pdf'),('content','content.json')]},
            'pages':[self.file_record(target/f'page-{n:03}.png') for n in range(1,result['page_count']+1)]}
        fingerprint=canonical_hash(payload)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if self.content_model(job_id)!=content:
                raise WorkflowError('blocked','Source changed before the render commit; artifacts remain unapproved')
            db.execute('INSERT INTO document_sets VALUES(?,?,?,?,?)',
                (render_id,job_id,json.dumps(payload,ensure_ascii=False),fingerprint,utc_now()))
            self._event(db,'documents_rendered',render_id,fingerprint)
            db.commit()
        return Outcome('ok',{**payload,'fingerprint':fingerprint,'reviewed':False,'approved':False},[],
            'Inspect every page image and confirm content, language, glyphs and layout before approval.')

    def current_render(self, render_id):
        with self._db() as db:
            row=db.execute('SELECT * FROM document_sets WHERE id=?',(render_id,)).fetchone()
            review=db.execute('SELECT * FROM document_reviews WHERE render_id=?',(render_id,)).fetchone()
        if not row:raise WorkflowError('needs_input','Unknown render_id; render the selected current job first')
        payload=json.loads(row['payload'])
        if canonical_hash(payload)!=row['fingerprint']:
            raise WorkflowError('blocked','Render snapshot integrity check failed')
        if canonical_hash(self.content_model(row['job_id']))!=payload['content_hash']:
            raise WorkflowError('blocked','Rendered content is stale against the current profile, job or draft')
        for file in [*payload['files'].values(),*payload['pages']]:
            path=self.inside(file['path'])
            if not path.is_file() or self.hash_file(path)!=file['sha256']:
                raise WorkflowError('blocked','Rendered file/page bytes changed or disappeared; render and review again')
        return {**payload,'fingerprint':row['fingerprint'],
            'reviewed':bool(review and review['fingerprint']==row['fingerprint'])}

    def private_json(self, path):
        path=Path(path).resolve(strict=True)
        if not path.is_relative_to(self.data_dir) or path.stat().st_size>2_000_000:
            raise WorkflowError('blocked','Review/approval inputs must be small files inside the selected private workspace')
        return json.loads(path.read_text(encoding='utf-8-sig'))

    def review_documents(self, render_id, path):
        current=self.current_render(render_id)
        review=self.private_json(path)
        object_fields(review,{'schema_version','render_fingerprint','reviewed_pages','checks'},set(),'document review')
        version(review,'document review')
        checks=object_fields(review['checks'],{'content','layout','glyphs','language'},set(),'review checks')
        if (review['render_fingerprint']!=current['fingerprint'] or
                review['reviewed_pages']!=list(range(1,current['page_count']+1)) or
                any(type(v) is not int for v in review['reviewed_pages']) or
                any(v is not True for v in checks.values())):
            raise WorkflowError('needs_input','Review every current page exactly once in order and affirm every check for this exact fingerprint')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.current_render(render_id)
            db.execute('INSERT OR REPLACE INTO document_reviews VALUES(?,?,?,?)',
                (render_id,current['fingerprint'],json.dumps(review),utc_now()))
            self._event(db,'documents_reviewed',render_id,current['fingerprint'])
            db.commit()
        return Outcome('ok',self.current_render(render_id),[],
            'Local review recorded; this does not authenticate a human or approve external disclosure.')

    def handoff(self,job_id):
        base=super().handoff(job_id)
        with self._db() as db:
            row=db.execute('SELECT id FROM document_sets WHERE job_id=? ORDER BY created_utc DESC LIMIT 1',(job_id,)).fetchone()
        if row:
            rendered=self.current_render(row['id'])
            base.data['documents']={key:rendered['files'][key] for key in ('docx','pdf')}
            base.data['review_artifacts'].update({'content':rendered['files']['content'],'pages':rendered['pages']})
            base.data['documents_reviewed']=rendered['reviewed']
            base.issues[:]=['Rendered documents are local; verify destination/answers/consents and approval before disclosure.']
        return base

    def reject_documents(self,render_id,reason):
        text(reason,'reason')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT id FROM document_sets WHERE id=?',(render_id,)).fetchone():
                raise WorkflowError('needs_input','Unknown render_id')
            db.execute('DELETE FROM document_reviews WHERE render_id=?',(render_id,))
            self._event(db,'documents_rejected',render_id,reason);db.commit()
        return Outcome('ok',{'render_id':render_id,'reviewed':False,'reason':reason},[])
