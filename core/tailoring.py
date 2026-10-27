"""Opt-in wording v2. Linkage checks are not proof of semantic entailment.

One source fact per statement is deliberate in this first slice. Grouped history
requires source locators of the form scope#location, reviewed in the profile.
No model calls, provider access, permission cache or second state store.
"""
from copy import deepcopy
import json
import re
import unicodedata

from .contracts import ContractError, Outcome, object_fields, strings, text
from .ledger import canonical_hash, utc_now
from .metrics import Trace
from .workflow import WorkflowError

POLICY = 'wording-review-1'
LABELS = {
    'summary': ('Summary', 'Tóm tắt'), 'skills': ('Relevant skills', 'Kỹ năng phù hợp'),
    'employment': ('Experience', 'Kinh nghiệm'), 'projects': ('Selected projects', 'Dự án tiêu biểu'),
    'education': ('Education', 'Học vấn'), 'certifications': ('Certifications', 'Chứng chỉ'),
    'languages': ('Languages', 'Ngôn ngữ')}
TRANSFORMS = {'exact_selection', 'faithful_compression', 'reordering', 'translation', 'faithful_paraphrase'}
CHECKS = {'entailed', 'scope_preserved', 'qualifiers_preserved', 'language_correct', 'requirement_mapping'}
DIMENSIONS = {'relevance', 'specificity', 'coverage', 'clarity', 'concision', 'readability'}
# These are conservative alarms, not a universal entity recognizer or translator.
QUALIFIERS = [('prototype', 'nguyên mẫu'), ('classroom', 'lớp học'), ('fictional', 'giả lập'),
              ('assisted', 'hỗ trợ'), ('basic', 'cơ bản'), ('team', 'nhóm'),
              ('not', 'không'), ('no', 'không'), ('intern', 'thực tập'),
              ('supervised', 'giám sát'), ('synthetic', 'tổng hợp')]
SENSITIVE = re.compile(r'\b(?:led|owned|managed|architected|fluent|certified|expert|production|'
                       r'python|sql|salesforce|hubspot|ga4|aws|azure|bachelor|master|phd)\b', re.I)
ACTION_WORDS = set('Used Built Developed Documented Supported Assisted Queried Created Tested '
                   'Completed Translated Maintained Configured Analyzed Analysed Wrote '
                   'Đã Sử Xây Phát Ghi Hỗ Hoàn Kiểm Dùng Tham'.split())


def normalized(value):
    return ' '.join(unicodedata.normalize('NFC', value).casefold().split())


def alarms(source, target):
    findings = []
    if set(re.findall(r'\d[\w./:%+-]*', target)) - set(re.findall(r'\d[\w./:%+-]*', source)):
        findings.append('Changed number/date')
    source_words = set(re.findall(r'\w+', source))
    entities = {word for word in re.findall(r'\b\w+\b', target)
                if any(letter.isupper() for letter in word)}
    if entities - source_words - ACTION_WORDS:
        findings.append('New capitalized entity/title; use exact wording or clarify evidence')
    if {m.group().casefold() for m in SENSITIVE.finditer(target)} - {
            m.group().casefold() for m in SENSITIVE.finditer(source)}:
        findings.append('New technology, ownership or credential term')
    return findings


def validate(model, profile, job, assessment):
    model = deepcopy(object_fields(model, {'schema_version', 'candidate_id', 'job_id', 'language',
        'author', 'prompt_version', 'model_configuration', 'sections'}, set(), 'wording model'))
    if model['schema_version'] != '2.0':
        raise ContractError('wording model: only 2.0 is supported')
    for key in ('author', 'prompt_version', 'model_configuration'):
        text(model[key], key)
    if (model['candidate_id'] != profile['candidate_id'] or type(model['job_id']) is not int or
            not isinstance(model['language'], str) or model['language'] not in {'en', 'vi'} or
            job['document_language'] and model['language'] != job['document_language']):
        raise WorkflowError('blocked', 'Candidate, job or language binding mismatch')
    facts = {fact['id']: fact for fact in profile['facts'] if fact['status'] == 'confirmed'}
    rows = {row['requirement_id']: row for row in assessment['rows']}
    if not isinstance(model['sections'], list) or not 1 <= len(model['sections']) <= len(LABELS):
        raise ContractError('wording sections: select supported, nonempty sections')
    seen_sections, seen_ids, seen_text = set(), set(), set()
    for section in model['sections']:
        object_fields(section, {'kind', 'groups'}, set(), 'section')
        kind = section['kind']
        if not isinstance(kind, str) or kind not in LABELS or kind in seen_sections:
            raise ContractError('Unknown or duplicate section')
        seen_sections.add(kind)
        if not isinstance(section['groups'], list) or not 1 <= len(section['groups']) <= 30:
            raise ContractError('section.groups: provide bounded nonempty groups')
        for group in section['groups']:
            object_fields(group, {'context_fact_id', 'statements'}, set(), 'group')
            context_id = group['context_fact_id']
            if context_id is not None and (not isinstance(context_id, str) or context_id not in facts):
                raise WorkflowError('blocked', 'Group context must be a confirmed source fact')
            if kind in {'employment', 'projects'} and context_id is None:
                raise ContractError('Grouped employment/projects need an exact source-backed context')
            context = facts[context_id] if context_id else None
            if context and '#' not in context['locator']:
                raise WorkflowError('needs_input', 'Grouped history needs approved scope#locator source locators')
            if not isinstance(group['statements'], list) or not 1 <= len(group['statements']) <= 30:
                raise ContractError('group.statements: provide bounded nonempty statements')
            for statement in group['statements']:
                object_fields(statement, {'id', 'text', 'source_fact_ids', 'source_locators',
                    'requirement_ids', 'transformation', 'retained_qualifiers',
                    'unresolved_questions', 'review_status'}, set(), 'statement')
                for key in ('id', 'text'):
                    text(statement[key], 'statement.'+key)
                for key in ('source_fact_ids', 'source_locators', 'requirement_ids',
                            'retained_qualifiers', 'unresolved_questions'):
                    strings(statement[key], 'statement.'+key)
                if statement['id'] in seen_ids or normalized(statement['text']) in seen_text:
                    raise ContractError('Duplicate statement ID or bullet')
                seen_ids.add(statement['id']); seen_text.add(normalized(statement['text']))
                if len(seen_ids) > 120 or len(statement['text']) > 2000:
                    raise ContractError('Select a concise content set: at most 120 statements of 2000 characters')
                if statement['review_status'] != 'pending' or statement['unresolved_questions']:
                    raise WorkflowError('needs_input', 'Resolve questions before import; review is recorded separately')
                ids = statement['source_fact_ids']
                if len(ids) != 1 or ids[0] not in facts:
                    raise WorkflowError('blocked', 'First v2 slice requires exactly one confirmed fact per statement')
                fact = facts[ids[0]]
                if statement['source_locators'] != [fact['source_id']+'#'+fact['locator']]:
                    raise WorkflowError('blocked', 'Source locator differs from the confirmed fact')
                if context and (context['source_id'] != fact['source_id'] or
                        context['locator'].split('#')[0] != fact['locator'].split('#')[0]):
                    raise WorkflowError('blocked', 'Mixed employer/project scope in a grouped statement')
                if not isinstance(statement['transformation'], str) or statement['transformation'] not in TRANSFORMS:
                    raise ContractError('Unsupported transformation')
                if statement['transformation'] in {'exact_selection', 'reordering'}:
                    if statement['text'] != fact['claim']:
                        raise WorkflowError('blocked', 'Exact selection/reordering cannot change claim wording')
                issues = alarms(fact['claim'], statement['text'])
                for alternatives in QUALIFIERS:
                    if any(re.search(r'(?<!\w)'+re.escape(q)+r'(?!\w)', normalized(fact['claim'])) for q in alternatives):
                        retained = [q for q in alternatives if re.search(
                            r'(?<!\w)'+re.escape(q)+r'(?!\w)', normalized(statement['text']))]
                        if not retained or not any(q in [normalized(v) for v in statement['retained_qualifiers']] for q in retained):
                            issues.append('Omitted or unrecorded qualifier: '+alternatives[0])
                if any(q not in statement['text'] for q in statement['retained_qualifiers']):
                    issues.append('Retained qualifier absent from statement')
                if issues:
                    raise WorkflowError('blocked', '; '.join(issues))
                for req_id in statement['requirement_ids']:
                    row = rows.get(req_id)
                    if not row or row['match'] not in {'direct', 'partial'} or ids[0] not in row['fact_ids']:
                        raise WorkflowError('blocked', 'Requirement link must use the current assessed evidence')
    if sum(len(s['text']) for s in statements(model)) > 50_000:
        raise ContractError('Content exceeds 50,000 characters')
    return model


def statements(model):
    return [s for section in model['sections'] for group in section['groups'] for s in group['statements']]


def content(model, profile, job):
    """The same ordered lines feed Markdown, DOCX and PDF text integrity checks."""
    vi = model['language'] == 'vi'
    facts = {fact['id']: fact for fact in profile['facts']}
    sections = []
    for section in model['sections']:
        groups = []
        for group in section['groups']:
            groups.append({'context': facts[group['context_fact_id']]['claim'] if group['context_fact_id'] else None,
                           'statements': deepcopy(group['statements'])})
        sections.append({'kind': section['kind'], 'heading': LABELS[section['kind']][vi], 'groups': groups})
    return {'schema_version': '2.0', 'candidate_id': profile['candidate_id'], 'name': profile['name'],
        'contacts': [v for v in profile.get('contacts', {}).values() if v], 'language': model['language'],
        'headline': ('Vị trí ứng tuyển: ' if vi else 'Target role: ')+job['title'], 'sections': sections}


class Wording:
    """Mixin used only by Documents; existing SQLite drafts remain canonical."""

    def wording_context(self, job_id):
        profile = self.confirmed_profile()
        job, job_hash = self.job_document(job_id)
        if self.get_job(job_id)['state'] in {'confirmed_submitted', 'user_reported_submitted', 'submission_uncertain'}:
            raise WorkflowError('blocked', 'Submitted/uncertain job requires reconciliation')
        with self._db() as db:
            row = db.execute('SELECT * FROM assessments WHERE job_id=?', (job_id,)).fetchone()
        if not row or row['profile_fingerprint'] != profile['fingerprint'] or row['job_fingerprint'] != job_hash:
            raise WorkflowError('needs_input', 'Assess current confirmed evidence and JD before wording')
        assessment = json.loads(row['payload'])
        if job['liveness'] != 'active' or assessment['classification'] == 'Ineligible':
            raise WorkflowError('blocked', 'Closed, unverified or ineligible job cannot receive wording')
        return profile, job, job_hash, assessment

    def import_wording(self, job_id, raw):
        trace = Trace()
        with trace.stage('current_evidence_and_assessment'):
            profile, job, job_hash, assessment = self.wording_context(job_id)
        with trace.stage('deterministic_wording_checks'):
            model = validate(raw, profile['profile'], job, assessment)
        if model['job_id'] != job_id:
            raise WorkflowError('blocked', 'Model job ID differs from the requested job')
        binding = {'model': model, 'profile_fingerprint': profile['fingerprint'],
                   'job_fingerprint': job_hash, 'assessment_hash': canonical_hash(assessment), 'policy': POLICY}
        fingerprint = canonical_hash(binding)
        base = f'drafts/{job_id}/wording-{fingerprint}'
        from .rendering import content_lines
        rendered = content(model, profile['profile'], job)
        if sum(len(value) for value, _ in content_lines(rendered)) > 50_000:
            raise WorkflowError('needs_input', 'Complete content including context and identity exceeds 50,000 characters')
        md = '\n\n'.join(prefix+self.literal(value) for value, prefix in content_lines(rendered, markdown=True))+'\n'
        selected_ids = {s['source_fact_ids'][0] for s in statements(model)}
        selected_ids.update(g['context_fact_id'] for section in model['sections'] for g in section['groups'] if g['context_fact_id'])
        source_map = [fact for fact in profile['profile']['facts'] if fact['id'] in selected_ids]
        files = {}
        for key, name, value in [('cv', 'cv.md', md), ('source_map', 'source-map.json', json.dumps(source_map, ensure_ascii=False)),
                                 ('wording', 'wording.json', json.dumps(binding, ensure_ascii=False))]:
            files[key] = self.file_record(self.atomic_text(base+'/'+name, value))
        result = {'job_id': job_id, 'language': model['language'], 'classification': assessment['classification'],
            'content_version': '2.0', 'wording_fingerprint': fingerprint, 'files': files,
            'status': 'wording_review_required', 'approval': False, 'rendered_pdf_docx': False,
            'profile_fingerprint': profile['fingerprint'], 'job_fingerprint': job_hash}
        with trace.stage('draft_commit'):
            self._save_wording_draft(job_id, result, binding)
        return Outcome('ok', {**result, 'metrics': trace.report(statements=len(statements(model)),
            input_utf8_bytes=len(json.dumps(raw, ensure_ascii=False).encode('utf8')),
            render_count=0, external_calls=0)}, [], 'Independent statement review is required before rendering or handoff.')

    def _save_wording_draft(self, job_id, result, binding, expected_draft=None):
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if expected_draft is not None:
                latest = db.execute('SELECT payload FROM drafts WHERE job_id=? ORDER BY id DESC LIMIT 1', (job_id,)).fetchone()
                if not latest or canonical_hash(json.loads(latest['payload'])) != expected_draft:
                    raise WorkflowError('blocked', 'Draft changed before review commit; inspect the current packet')
            profile, _, job_hash, assessment = self.wording_context(job_id)
            if (profile['fingerprint'] != binding['profile_fingerprint'] or job_hash != binding['job_fingerprint'] or
                    canonical_hash(assessment) != binding['assessment_hash']):
                raise WorkflowError('blocked', 'Evidence changed before wording commit')
            db.execute('INSERT INTO drafts(job_id,payload,profile_fingerprint,job_fingerprint,created_utc) VALUES(?,?,?,?,?)',
                (job_id, json.dumps(result, ensure_ascii=False), profile['fingerprint'], job_hash, utc_now()))
            db.execute("UPDATE jobs SET state='review_required',version=version+1,updated_utc=? WHERE id=?", (utc_now(), job_id))
            self._event(db, 'wording_'+result['status'], job_id, result['wording_fingerprint'])
            db.commit()

    def wording_packet(self, job_id):
        draft = self.current_draft(job_id)
        if draft.get('content_version') != '2.0':
            raise WorkflowError('needs_input', 'Import an explicit v2 wording model first')
        binding = self.private_json(self.inside(draft['files']['wording']['path']))
        profile, job, job_hash, assessment = self.wording_context(job_id)
        if (canonical_hash(binding) != draft['wording_fingerprint'] or binding['policy'] != POLICY or
                binding['profile_fingerprint'] != profile['fingerprint'] or binding['job_fingerprint'] != job_hash or
                binding['assessment_hash'] != canonical_hash(assessment)):
            raise WorkflowError('blocked', 'Wording binding is stale')
        model = validate(binding['model'], profile['profile'], job, assessment)
        selected_ids = {s['source_fact_ids'][0] for s in statements(model)}
        selected_ids.update(g['context_fact_id'] for section in model['sections'] for g in section['groups'] if g['context_fact_id'])
        facts = [fact for fact in profile['profile']['facts'] if fact['id'] in selected_ids]
        represented = sorted({req for s in statements(model) for req in s['requirement_ids']})
        compact_assessment = {key: assessment[key] for key in ('classification', 'constraints')}
        compact_assessment['rows'] = [{key: row[key] for key in ('requirement_id', 'match', 'fact_ids', 'reason')}
                                     for row in assessment['rows']]
        return Outcome('ok', {'fingerprint': draft['wording_fingerprint'], 'policy': POLICY, 'model': model,
            'candidate': {key: profile['profile'].get(key) for key in ('candidate_id', 'name', 'contacts')},
            'job': {key: job[key] for key in ('employer', 'req_id', 'title', 'url', 'raw_jd', 'city',
                                             'country', 'liveness', 'document_language', 'salary')},
            'bindings': {key: binding[key] for key in ('profile_fingerprint', 'job_fingerprint', 'assessment_hash')},
            'source_records': [source for source in profile['sources'] if source['id'] in {fact['source_id'] for fact in facts}],
            'facts': facts, 'requirements': job['requirements'], 'assessment': compact_assessment,
            'coverage': {'represented_requirement_ids': represented, 'represented': len(represented),
                'denominator': len(job['requirements']), 'meaning': 'Evidence-mapped requirements represented, not qualifications satisfied'},
            'reviewed': 'wording_review' in draft['files']}, [])

    def review_wording(self, job_id, raw):
        packet = self.wording_packet(job_id).data
        validate_review(raw, packet)
        draft = deepcopy(self.current_draft(job_id))
        if draft['wording_fingerprint'] != packet['fingerprint']:
            raise WorkflowError('blocked', 'Draft changed during review; inspect the current packet')
        expected = canonical_hash(draft)
        binding = self.private_json(self.inside(draft['files']['wording']['path']))
        path = self.atomic_text(f"drafts/{job_id}/reviews/{canonical_hash(raw)}.json", json.dumps(raw, ensure_ascii=False))
        draft['files']['wording_review'] = self.file_record(path)
        draft['status'] = 'review_required'
        self._save_wording_draft(job_id, draft, binding, expected_draft=expected)
        return Outcome('ok', draft, [], 'Factual review recorded; rendered page review and disclosure approval remain separate.')

    def reject_wording(self, job_id, reason):
        text(reason, 'reason')
        self.wording_packet(job_id)
        draft = deepcopy(self.current_draft(job_id))
        expected = canonical_hash(draft)
        binding = self.private_json(self.inside(draft['files']['wording']['path']))
        draft['files'].pop('wording_review', None)
        draft['status'] = 'wording_review_required'
        draft['review_rejection'] = reason
        self._save_wording_draft(job_id, draft, binding, expected_draft=expected)
        return Outcome('ok', draft, [], 'Factual review rejected; dependent current renders and approvals are invalid.')

    def reviewed_wording_content(self, job_id, draft):
        packet = self.wording_packet(job_id).data
        if 'wording_review' not in draft['files']:
            raise WorkflowError('needs_input', 'Independent v2 factual review is required before rendering/handoff')
        review = self.private_json(self.inside(draft['files']['wording_review']['path']))
        validate_review(review, packet)
        profile, job, _, _ = self.wording_context(job_id)
        result = content(packet['model'], profile['profile'], job)
        for section in result['sections']:
            for group in section['groups']:
                for statement in group['statements']:
                    statement['review_status'] = 'approved'
        return {**result, 'wording_fingerprint': packet['fingerprint'], 'review_hash': canonical_hash(review),
            'draft_fingerprint': canonical_hash(draft), 'profile_fingerprint': draft['profile_fingerprint'],
            'job_fingerprint': draft['job_fingerprint']}


def validate_review(raw, packet):
    object_fields(raw, {'schema_version', 'fingerprint', 'policy', 'reviewer', 'independent_pass',
        'statements', 'editorial'}, set(), 'wording review')
    if (raw['schema_version'] != '2.0' or raw['fingerprint'] != packet['fingerprint'] or
            raw['policy'] != POLICY or raw['independent_pass'] is not True or
            not isinstance(raw['reviewer'], str) or not raw['reviewer'].strip() or
            raw['reviewer'] == packet['model']['author']):
        raise WorkflowError('needs_input', 'Exact fingerprint and a separately identified independent review pass are required')
    ids = {s['id'] for s in statements(packet['model'])}
    if not isinstance(raw['statements'], dict) or raw['statements'].keys() != ids:
        raise WorkflowError('needs_input', 'Review every statement exactly once')
    for value in raw['statements'].values():
        object_fields(value, CHECKS | {'rationale'}, set(), 'statement review')
        text(value['rationale'], 'review rationale')
        if any(value[key] is not True for key in CHECKS):
            raise WorkflowError('blocked', 'Remaining factual review finding; repair or use reviewed exact claims')
    object_fields(raw['editorial'], DIMENSIONS, set(), 'editorial rubric')
    for value in raw['editorial'].values():
        object_fields(value, {'score', 'statement_ids', 'rationale'}, set(), 'editorial dimension')
        text(value['rationale'], 'editorial rationale')
        strings(value['statement_ids'], 'editorial statement IDs')
        if type(value['score']) is not int or not 0 <= value['score'] <= 3 or not value['statement_ids'] or not set(value['statement_ids']) <= ids:
            raise ContractError('Editorial dimensions need score 0–3 and exact statement evidence; no ATS probability')
