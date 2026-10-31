"""Versioned generation context, fictional evidence and immutable legacy exports."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from core.learning import export_reviewed, check_export
from core.ledger import canonical_hash
from core.workflow import WorkflowError
from scripts.demo_wording import seed, fictional_review


LEGACY_SYSTEM = ('Propose source-bound CV wording as JSON language/sections. Use only the supplied '
    'confirmed facts; job requirements are not candidate evidence. Preserve qualifiers, '
    'numbers and source mappings. Output pending statements, never an approval or invented fact.')


class LearningPromptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work, model = seed(Path(self.tmp.name)/'private')
        self.work.import_wording(1, model)
        self.work.review_wording(1, fictional_review(self.work.wording_packet(1).data))
        export_reviewed(self.work, [1], 'datasets/test')
        self.root = self.work.inside('datasets/test')
        self.manifest = self.work.private_json(self.root/'manifest.json')
        self.example = json.loads((self.root/'examples.jsonl').read_text(encoding='utf8'))

    def save_rehashed(self):
        path = self.root/'examples.jsonl'
        path.write_text(json.dumps(self.example, ensure_ascii=False)+'\n', encoding='utf8')
        self.manifest['files']['examples.jsonl'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.manifest['manifest_fingerprint'] = canonical_hash({k:v for k,v in self.manifest.items() if k != 'manifest_fingerprint'})
        (self.root/'manifest.json').write_text(json.dumps(self.manifest), encoding='utf8')

    def test_new_prompt_supplies_canonical_output_schema_and_assessed_links(self):
        self.assertEqual('1.1', self.manifest['schema_version'])
        self.assertEqual('cv-wording-json-2', self.manifest['wording_prompt_version'])
        inputs = json.loads(self.example['messages'][1]['content'])
        schema = inputs['output_schema']
        self.assertEqual(['language', 'sections'], schema['required'])
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual({'requirement_id':'R1','match':'direct','fact_ids':['F1']}, inputs['assessed_evidence'][0])
        self.assertNotIn('sections', inputs)  # No reference answer in the generation input.
        self.assertIn('No Markdown fences', self.example['messages'][0]['content'])
        canonical = json.loads((Path(__file__).resolve().parents[1]/'schemas/cv-content-v2.schema.json').read_text(encoding='utf8'))
        for name in ('strings','statement','group','section'):
            self.assertEqual(canonical['$defs'][name], schema['$defs'][name])
        self.assertTrue(check_export(self.work, 'datasets/test').data['current_evidence_checked'])

    def test_legacy_export_remains_current_without_rewriting_its_bytes(self):
        inputs = json.loads(self.example['messages'][1]['content'])
        inputs.pop('output_schema', None); inputs.pop('assessed_evidence', None)
        self.example['messages'][0]['content'] = LEGACY_SYSTEM
        self.example['messages'][1]['content'] = json.dumps(inputs, ensure_ascii=False, sort_keys=True)
        self.manifest['schema_version'] = '1.0'
        self.manifest.pop('wording_prompt_version', None)
        self.save_rehashed()
        before = {p.name:p.read_bytes() for p in self.root.iterdir()}
        self.assertTrue(check_export(self.work, 'datasets/test').data['current_evidence_checked'])
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.root.iterdir()})
        self.example['messages'][0]['content'] += ' Different instructions.'
        self.save_rehashed()
        with self.assertRaises(WorkflowError): check_export(self.work, 'datasets/test')

    def test_unknown_prompt_version_fails_even_with_rehashed_manifest(self):
        self.manifest['wording_prompt_version'] = 'unreviewed-prompt'
        self.save_rehashed()
        with self.assertRaises(WorkflowError): check_export(self.work, 'datasets/test')

    def test_changed_embedded_schema_cannot_weaken_the_contract(self):
        inputs = json.loads(self.example['messages'][1]['content'])
        inputs['output_schema']['additionalProperties'] = True
        self.example['messages'][1]['content'] = json.dumps(inputs, ensure_ascii=False, sort_keys=True)
        self.save_rehashed()
        with self.assertRaises(WorkflowError): check_export(self.work, 'datasets/test')
