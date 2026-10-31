#!/usr/bin/env python3
"""Fictional v2 wording demonstration. Generated reviews are TEST INPUTS ONLY."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.documents import Documents
from core.tailoring import CHECKS, DIMENSIONS, POLICY, statements


def seed(directory, candidate='data', language='en'):
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('Use a new empty fictional workspace')
    roles = {'data': ('Junior Data Analyst', 'SQL', 'Queried a fictional sales dataset using SQL.'),
             'technical': ('Junior Automation Developer', 'Python', 'Tested a fictional classroom prototype using Python.'),
             'commercial': ('Customer Solutions Associate', 'onboarding', 'Documented fictional customer onboarding steps.')}
    title, skill, claim = roles[candidate]
    work = Documents(directory); work.init(language)
    facts = []
    source = [f'Fictional {candidate} candidate.']
    for fact_id, field, value, quote, locator in [
        ('E0', 'employment', 'context', 'Example Cooperative — Support Assistant | 2024–2025.', 'employment/cooperative#header'),
        ('E1', 'capability', 'support', 'Documented fictional customer support cases.', 'employment/cooperative#bullet'),
        ('P0', 'project', 'context', 'Fictional classroom project.', 'project/classroom#header'),
        ('F1', 'skill', skill, claim, 'project/classroom#bullet'),
        ('ED', 'education', 'Bachelor', 'Completed a fictional Bachelor of Information Systems.', 'education#degree'),
        ('L1', 'language', 'English', 'English: basic reading.', 'language#english'),
        ('X1', 'capability', 'support', 'Assisted a fictional team with support cases.', 'employment/other#bullet')]:
        source.append(quote)
        facts.append({'id': fact_id, 'field': field, 'value': value, 'claim': quote, 'source_id': 'CV1',
                      'quote': quote, 'locator': locator, 'status': 'confirmed'})
    path = work.atomic_text('inputs/fictional-cv.md', '\n'.join(source))
    work.import_cv(path, 'CV1')
    profile = {'schema_version': '1.0', 'candidate_id': 'fictional-'+candidate,
        'name': 'Example '+candidate, 'language': language, 'preferences': {},
        'contacts': {'email': candidate+'@example.invalid'}, 'facts': facts}
    fingerprint = work.import_profile(profile).data['fingerprint']
    work.confirm_profile(fingerprint, work.atomic_text('inputs/confirmation.txt', 'CONFIRM PROFILE '+fingerprint))
    job = json.loads((ROOT/'examples/fictional/job.json').read_text(encoding='utf8'))
    job.update(title=title, document_language=language,
        raw_jd=('FICTIONAL LOCAL DEMONSTRATION ONLY. '
                f'{skill} project experience required; relevant certification preferred. '
                'No real application destination exists.'),
        requirements=[{'id': 'R1', 'text': skill+' project experience', 'field': 'skill', 'value': skill,
                       'mandatory': True, 'hard': False},
                      {'id': 'R2', 'text': 'Relevant certification preferred', 'field': 'certification',
                       'value': 'certificate', 'mandatory': False, 'hard': False}])
    work.import_job(job)
    work.assess(1, {'schema_version': '1.0', 'rows': [
        {'requirement_id': 'R1', 'match': 'direct', 'fact_ids': ['F1'], 'reason': 'Exact confirmed skill; project scope retained.'},
        {'requirement_id': 'R2', 'match': 'missing', 'fact_ids': [], 'reason': 'No certification evidence.'}]})
    def statement(fact, reqs=()):
        qualifiers = [q for q in ['fictional', 'classroom', 'prototype', 'basic'] if q in fact['claim']]
        return {'id': 'S-'+fact['id'], 'text': fact['claim'], 'source_fact_ids': [fact['id']],
            'source_locators': ['CV1#'+fact['locator']], 'requirement_ids': list(reqs),
            'transformation': 'exact_selection', 'retained_qualifiers': qualifiers,
            'unresolved_questions': [], 'review_status': 'pending'}
    by_id = {fact['id']: fact for fact in facts}
    model = {'schema_version': '2.0', 'candidate_id': profile['candidate_id'], 'job_id': 1,
        'language': language, 'author': 'fictional-draft-pass', 'prompt_version': 'fixture-1',
        'model_configuration': 'no model: authored fixture', 'sections': [
            {'kind': kind, 'groups': [{'context_fact_id': context,
                'statements': [statement(by_id[fact_id], ['R1'] if fact_id == 'F1' else [])]}]}
            for kind, context, fact_id in [('employment', 'E0', 'E1'), ('projects', 'P0', 'F1'),
                                          ('education', None, 'ED'), ('languages', None, 'L1')]]}
    return work, model


def fictional_review(packet):
    """Never use this helper to fabricate a review of a real candidate document."""
    ids = [s['id'] for s in statements(packet['model'])]
    return {'schema_version': '2.0', 'fingerprint': packet['fingerprint'], 'policy': POLICY,
        'reviewer': 'fictional-test-review-pass', 'independent_pass': True,
        'statements': {sid: {**dict.fromkeys(CHECKS, True), 'rationale': 'Fictional test assertion; no real reviewer claim.'} for sid in ids},
        'editorial': {key: {'score': 2, 'statement_ids': ids, 'rationale': 'Fictional rubric fixture, not an editorial evaluation.'}
                      for key in DIMENSIONS}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--candidate', choices=['data', 'technical', 'commercial'], default='data')
    args = parser.parse_args()
    def run(directory):
        work, model = seed(directory, args.candidate)
        imported = work.import_wording(1, model).data
        packet = work.wording_packet(1).data
        review = fictional_review(packet)
        work.review_wording(1, review)
        # No automatic rendered-layout review and no approval or external actions.
        work.atomic_text('reports/packet.json', json.dumps(packet, ensure_ascii=False, indent=2))
        work.atomic_text('reports/content-v2.json', json.dumps(work.content_model(1), ensure_ascii=False, indent=2))
        return {'fictional_only': True, 'synthetic_review_only': True, 'draft': imported,
                'reviewed_content_available': True, 'rendered': False, 'external_actions': 0}
    if args.data_dir:
        result = run(args.data_dir)
    else:
        with tempfile.TemporaryDirectory(prefix='career-kit-wording-') as temp:
            result = run(Path(temp)/'private')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf8')
    main()
