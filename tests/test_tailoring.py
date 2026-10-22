from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.contracts import ContractError
from core.ledger import canonical_hash
from core.manifests import Campaign
from core.rendering import paragraphs
from core.workflow import WorkflowError
from scripts.demo_wording import fictional_review, seed
from test_documents import fake_render


class WordingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.work, self.model = seed(Path(self.tmp.name)/'private')

    def imported(self):
        return self.work.import_wording(1, self.model).data

    def reviewed(self):
        self.imported()
        return self.work.review_wording(1, fictional_review(self.work.wording_packet(1).data))

    def test_review_required_and_shared_wording_reaches_render_not_legacy_quotes(self):
        statement = self.model['sections'][1]['groups'][0]['statements'][0]
        statement.update(text='Used SQL to query a fictional sales dataset.', transformation='faithful_paraphrase')
        result = self.imported()
        for action in [lambda: self.work.content_model(1), lambda: self.work.render(1), lambda: self.work.handoff(1)]:
            with self.assertRaises(WorkflowError): action()
        packet = self.work.wording_packet(1).data
        self.assertEqual(1, packet['coverage']['represented'])
        self.assertEqual(2, packet['coverage']['denominator'])
        self.work.review_wording(1, fictional_review(packet))
        content = self.work.content_model(1)
        self.assertIn(statement['text'], ' '.join(paragraphs(content)))
        self.assertNotIn('Queried a fictional sales dataset using SQL.', ' '.join(paragraphs(content)))
        self.assertIn(statement['text'], self.work.inside(result['files']['cv']['path']).read_text(encoding='utf8'))
        with patch('core.documents.render_files', side_effect=fake_render) as renderer:
            render = self.work.render(1).data
        self.assertEqual(content, renderer.call_args.args[0])
        self.assertFalse(render['reviewed'])
        self.assertEqual('approved', content['sections'][1]['groups'][0]['statements'][0]['review_status'])

    def test_adversarial_numbers_ownership_tools_qualifiers_and_scope(self):
        original = deepcopy(self.model)
        bad = ['Led SQL analysis of a fictional sales dataset.',
               'Queried 100 fictional sales datasets using SQL.',
               'Queried a fictional sales dataset using SQL and Python.',
               'Queried a sales dataset using SQL.',
               'Queried a fictional Salesforce dataset using SQL.']
        for wording in bad:
            with self.subTest(wording=wording):
                self.model = deepcopy(original)
                statement = self.model['sections'][1]['groups'][0]['statements'][0]
                statement.update(text=wording, transformation='faithful_paraphrase')
                with self.assertRaises((WorkflowError, ContractError)): self.imported()
        self.model = deepcopy(original)
        self.model['sections'][0]['groups'][0]['statements'][0].update(
            source_fact_ids=['X1'], source_locators=['CV1#employment/other#bullet'],
            text='Assisted a fictional team with support cases.', retained_qualifiers=['Assisted', 'fictional', 'team'])
        with self.assertRaisesRegex(WorkflowError, 'Mixed'): self.imported()

    def test_pending_claims_credentials_and_language_inflation_fail(self):
        for section_index, text in [(2, 'Completed a fictional Master of Information Systems.'),
                                    (3, 'English: fluent reading.')]:
            model = deepcopy(self.model)
            model['sections'][section_index]['groups'][0]['statements'][0].update(text=text, transformation='faithful_paraphrase')
            with self.assertRaises(WorkflowError): self.work.import_wording(1, model)

    def test_review_is_exact_independent_complete_and_can_fail(self):
        self.imported(); packet = self.work.wording_packet(1).data
        for change in [{'fingerprint': '0'*64}, {'reviewer': self.model['author']}, {'independent_pass': False},
                       {'statements': {}}]:
            with self.subTest(change=change):
                with self.assertRaises(WorkflowError): self.work.review_wording(1, {**fictional_review(packet), **change})
        review = fictional_review(packet)
        review['statements']['S-F1']['entailed'] = False
        with self.assertRaises(WorkflowError): self.work.review_wording(1, review)
        with self.assertRaises(WorkflowError): self.work.content_model(1)

    def test_files_profile_jd_assessment_and_review_drift_invalidate(self):
        self.reviewed()
        with patch('core.documents.render_files', side_effect=fake_render): rendered = self.work.render(1).data
        draft = self.work.current_draft(1)
        review_path = self.work.inside(draft['files']['wording_review']['path'])
        review_path.write_text('{}', encoding='utf8')
        with self.assertRaises(WorkflowError): self.work.current_render(rendered['render_id'])

    def test_candidate_and_job_binding_no_leakage_and_duplicate_bullets(self):
        other, _ = seed(Path(self.tmp.name)/'other', 'commercial')
        with self.assertRaises(WorkflowError): other.import_wording(1, self.model)
        wrong = {**self.model, 'job_id': 2}
        with self.assertRaises(WorkflowError): self.work.import_wording(1, wrong)
        duplicate = deepcopy(self.model)
        duplicate['sections'][1]['groups'][0]['statements'].append(deepcopy(duplicate['sections'][1]['groups'][0]['statements'][0]))
        with self.assertRaises(ContractError): self.work.import_wording(1, duplicate)

    def test_ineligible_missing_mapping_and_unresolved_input_are_not_papered_over(self):
        model = deepcopy(self.model)
        model['sections'][1]['groups'][0]['statements'][0]['requirement_ids'] = ['R2']
        with self.assertRaises(WorkflowError): self.work.import_wording(1, model)
        model = deepcopy(self.model)
        model['sections'][0]['groups'][0]['statements'][0]['unresolved_questions'] = ['Ownership unknown']
        with self.assertRaises(WorkflowError): self.work.import_wording(1, model)

    def test_three_distinct_candidate_families_are_not_maintainer_specific(self):
        for candidate in ['technical', 'commercial']:
            work, model = seed(Path(self.tmp.name)/candidate, candidate)
            work.import_wording(1, model)
            work.review_wording(1, fictional_review(work.wording_packet(1).data))
            self.assertEqual('fictional-'+candidate, work.content_model(1)['candidate_id'])

    def test_changed_source_jd_and_assessment_stale_the_content(self):
        self.reviewed()
        original_profile = self.work.inspect_profile().data['profile']
        changed = deepcopy(original_profile)
        changed['contacts']['phone'] = '000 fictional'
        self.work.import_profile(changed)
        with self.assertRaises(WorkflowError): self.work.content_model(1)
        # Reconfirmation alone does not update a prior wording/review fingerprint.
        fp = self.work.inspect_profile().data['fingerprint']
        self.work.confirm_profile(fp, self.work.atomic_text('confirmation-new.txt', 'CONFIRM PROFILE '+fp))
        with self.assertRaises(WorkflowError): self.work.content_model(1)
        self.work.assess(1, {'schema_version':'1.0','rows':[
            {'requirement_id':'R1','match':'direct','fact_ids':['F1'],'reason':'Current project evidence.'},
            {'requirement_id':'R2','match':'missing','fact_ids':[],'reason':'No certification.'}]})
        self.reviewed()
        job, _ = self.work.job_document(1)
        job['raw_jd'] += ' Changed requirement text.'
        self.work.import_job(job)
        with self.assertRaises(WorkflowError): self.work.content_model(1)

    def test_provenance_alone_does_not_pass_semantics_or_a_failed_repair(self):
        s = self.model['sections'][1]['groups'][0]['statements'][0]
        # No number/entity alarm, but the claimed business result is unsupported.
        s.update(text='Queried a fictional sales dataset using SQL, improving customer retention.',
                 transformation='faithful_paraphrase')
        self.imported()
        review = fictional_review(self.work.wording_packet(1).data)
        review['statements']['S-F1'].update(entailed=False, rationale='Retention outcome absent from source.')
        with self.assertRaises(WorkflowError): self.work.review_wording(1, review)
        with self.assertRaises(WorkflowError): self.work.content_model(1)
        self.assertEqual('wording_review_required', self.work.current_draft(1)['status'])

    def test_prototype_qualifier_cannot_be_dropped(self):
        work, model = seed(Path(self.tmp.name)/'technical', 'technical')
        s = model['sections'][1]['groups'][0]['statements'][0]
        s.update(text='Tested a fictional classroom application using Python.', transformation='faithful_paraphrase')
        with self.assertRaisesRegex(WorkflowError, 'qualifier'): work.import_wording(1, model)

    def test_real_cli_and_private_input_boundary(self):
        root = Path(__file__).resolve().parents[1]
        path = self.work.atomic_text('inputs/model.json', json.dumps(self.model))
        def cli(*args):
            return subprocess.run([sys.executable, str(root/'scripts/kit.py'), '--data-dir',
                str(self.work.data_dir), *args], cwd=self.tmp.name, capture_output=True, text=True,
                encoding='utf8', timeout=20)
        imported = cli('import-wording', '--job-id', '1', '--file', str(path))
        self.assertEqual(0, imported.returncode, imported.stdout+imported.stderr)
        packet = json.loads(cli('wording-packet', '--job-id', '1').stdout)['data']
        review = self.work.atomic_text('inputs/review.json', json.dumps(fictional_review(packet)))
        reviewed = cli('review-wording', '--job-id', '1', '--file', str(review))
        self.assertEqual(0, reviewed.returncode, reviewed.stdout+reviewed.stderr)
        outside = Path(self.tmp.name)/'outside.json'; outside.write_text(json.dumps(self.model))
        blocked = cli('import-wording', '--job-id', '1', '--file', str(outside))
        self.assertEqual(2, blocked.returncode)
        self.assertEqual('blocked', json.loads(blocked.stdout)['outcome'])

    def test_vietnamese_translation_preserves_supported_qualifier_and_entities(self):
        work, model = seed(Path(self.tmp.name)/'vi', 'data', 'vi')
        model['sections'] = [model['sections'][1]]
        model['sections'][0]['kind'] = 'skills'
        model['sections'][0]['groups'][0]['context_fact_id'] = None
        s = model['sections'][0]['groups'][0]['statements'][0]
        s.update(text='Đã dùng SQL để truy vấn tập dữ liệu bán hàng giả lập.', transformation='translation',
                 retained_qualifiers=['giả lập'])
        work.import_wording(1, model)
        work.review_wording(1, fictional_review(work.wording_packet(1).data))
        self.assertIn('giả lập', ' '.join(paragraphs(work.content_model(1))))
        s['text'] = 'Đã dùng SQL để truy vấn tập dữ liệu bán hàng.'
        with self.assertRaises(WorkflowError): work.import_wording(1, model)

    def test_rejection_new_wording_and_source_bytes_invalidate_current_render(self):
        self.reviewed()
        with patch('core.documents.render_files', side_effect=fake_render): rendered = self.work.render(1).data
        self.work.reject_wording(1, 'Factual issue discovered during review.')
        with self.assertRaises(WorkflowError): self.work.current_render(rendered['render_id'])
        self.reviewed()
        with patch('core.documents.render_files', side_effect=fake_render): rendered = self.work.render(1).data
        self.work.import_wording(1, self.model)
        with self.assertRaises(WorkflowError): self.work.current_render(rendered['render_id'])
        self.reviewed()
        source = self.work.inspect_profile().data['sources'][0]
        self.work.inside(source['path']).write_text('Changed imported source', encoding='utf8')
        with self.assertRaises(WorkflowError): self.work.content_model(1)

    def test_superseded_draft_cannot_be_approved_by_a_racing_old_review(self):
        self.imported()
        old = self.work.current_draft(1)
        binding = self.work.private_json(self.work.inside(old['files']['wording']['path']))
        updated = deepcopy(self.model)
        updated['prompt_version'] = 'new-version'
        self.work.import_wording(1, updated)
        with self.assertRaisesRegex(WorkflowError, 'Draft changed'):
            self.work._save_wording_draft(1, old, binding, expected_draft=canonical_hash(old))

    def test_v2_factual_rejection_invalidates_an_exact_approved_manifest(self):
        self.reviewed()
        work = Campaign(self.work.data_dir); work.init()
        with patch('core.documents.render_files', side_effect=fake_render): rendered = work.render(1).data
        review = {'schema_version':'1.0','render_fingerprint':rendered['fingerprint'],
            'reviewed_pages':[1],'checks':dict.fromkeys(['content','layout','glyphs','language'],True)}
        work.review_documents(rendered['render_id'], work.atomic_text('page-review.json',json.dumps(review)))
        now = datetime.now(timezone.utc)
        plan = {'schema_version':'1.0','campaign_id':'fictional-v2','mode':'ASSIST',
            'expires_utc':(now+timedelta(hours=1)).isoformat(),'submission_limit':0,
            'entries':[{'job_id':1,'render_id':rendered['render_id'],'format':'pdf',
                'destination':'https://apply.example.test/v2','operations':['fill','upload'],
                'answers':{},'required_answers':[],'consents':[],
                'policy':{'permission':'permitted','source':'https://apply.example.test/policy',
                    'checked_utc':now.isoformat(),'allowed_operations':['fill','upload']}}]}
        manifest = work.create_manifest(plan).data
        work.approve_manifest(manifest['fingerprint'], work.atomic_text('approval.txt','APPROVE MANIFEST '+manifest['fingerprint']))
        self.assertTrue(work.check_manifest(manifest['fingerprint']).data['approved'])
        work.reject_wording(1, 'Factual review withdrawn')
        with self.assertRaises(WorkflowError): work.check_manifest(manifest['fingerprint'])


if __name__ == '__main__': unittest.main()
