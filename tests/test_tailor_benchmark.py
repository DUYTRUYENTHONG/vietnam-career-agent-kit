"""Fictional behavioral regressions; no models, real CVs or network calls."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from core import tailor_benchmark as b


class TailorBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        raw = 'Built Python API tests with AI assistance.\nExperience testing APIs.'
        (self.root/'source.txt').write_bytes(raw.encode('utf8'))
        source = {'path': 'source.txt', 'sha256': b.digest(raw.encode()), 'locator': 'lines1-2'}
        self.case = {'case_id': 'fictional1', 'profile_group': 'fictional-person',
            'source_group': 'employer-a', 'language': 'en',
            'requirement': {'id': 'R1', 'text': 'Experience testing APIs.', 'source': source},
            'facts': [{'id': 'F1', 'text': 'Built Python API tests with AI assistance.',
                'scope': 'AI-assisted personal prototype', 'qualifiers': ['AI assistance'], 'source': source}],
            'exposure': 'Fictional previously exposed regression fixture; not an unseen-profile test'}

    def annotation(self, reviewer):
        return {'case_id': 'fictional1', 'case_sha256': b.binding(self.case),
            'reviewer_id': reviewer, 'reviewer_type': 'human', 'source_checked': True,
            'expected_decision': 'tailored', 'acceptable_fact_ids': ['F1'],
            'rationale': 'Fictional human attestation fixture, not an actual review.'}

    def frozen(self):
        b.prepare(self.root, [self.case], 'prepared')
        return b.freeze(self.root, 'prepared', [self.annotation('A')],
                        [self.annotation('B')], 'frozen')

    def records(self):
        rt = dict(b.RUNTIME_PROTOCOL, tokenizer_sha256='a'*64, adapter_sha256=None)
        return [{'case_id': self.case['case_id'], 'condition': arm,
            'case_sha256': b.binding(self.case), 'messages_sha256': b.binding(b.messages(self.case, arm)),
            'raw_output': '{"decision":"tailored","statement":{"text":"Built Python API tests with AI assistance.","fact_id":"F1","requirement_id":"R1"}}',
            'metrics': {'input_tokens': 50, 'output_tokens': 20, 'generation_ms': 12.0},
            'runtime': dict(rt, adapter_sha256='b'*64 if arm == 'adapter_evidence' else None)} for arm in b.ARMS]

    def reviews(self):
        rows = b.read_rows(self.root/'blinded/review_packet.jsonl')
        return [{'review_id': row['review_id'], 'case_sha256': row['case_sha256'],
            'output_sha256': row['output_sha256'], 'reviewer_id': who, 'reviewer_type': 'human',
            'checks': {k: True for k in b.CHECKS},
            'editorial': {d: {'score': 3, 'rationale': 'Fictional test review.'} for d in b.DIMENSIONS}}
            for row in rows for who in ('C', 'D')]

    def test_pending_templates_cannot_freeze(self):
        b.prepare(self.root, [self.case], 'prepared')
        with self.assertRaisesRegex(ValueError, 'human'):
            b.freeze(self.root, 'prepared', b.read_rows(self.root/'prepared/review_A.jsonl'),
                     b.read_rows(self.root/'prepared/review_B.jsonl'), 'frozen')

    def test_same_reviewer_cannot_supply_both_packets(self):
        b.prepare(self.root, [self.case], 'prepared')
        with self.assertRaisesRegex(ValueError, 'distinct'):
            b.freeze(self.root, 'prepared', [self.annotation('A')], [self.annotation('A')], 'frozen')

    def test_disagreement_is_not_automatic_gold(self):
        b.prepare(self.root, [self.case], 'prepared')
        other = self.annotation('B'); other.update(expected_decision='not_demonstrated', acceptable_fact_ids=[])
        with self.assertRaisesRegex(ValueError, 'adjudicate'):
            b.freeze(self.root, 'prepared', [self.annotation('A')], [other], 'frozen')

    def test_bad_source_hash_and_out_of_root_fail(self):
        for path in ('../escape', '/absolute'):
            with self.assertRaises(ValueError):
                b.inside(self.root, path)
        self.case['facts'][0]['source']['sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            b.prepare(self.root, [self.case], 'prepared')

    def test_absent_claim_in_valid_source_fails(self):
        self.case['facts'][0]['text'] = 'Deployed Kubernetes in production.'
        with self.assertRaisesRegex(ValueError, 'not found'):
            b.prepare(self.root, [self.case], 'prepared')

    def test_no_overwrite_and_no_duplicate_case(self):
        b.prepare(self.root, [self.case], 'prepared')
        with self.assertRaisesRegex(ValueError, 'new output'):
            b.prepare(self.root, [self.case], 'prepared')
        with self.assertRaisesRegex(ValueError, 'Duplicate case'):
            b.prepare(self.root, [self.case, self.case], 'new')

    def test_frozen_input_has_no_gold_and_shared_evidence_prompt(self):
        self.frozen()
        rows = b.read_rows(self.root/'frozen/generation_inputs.jsonl')
        self.assertNotIn('acceptable_fact_ids', str(rows))
        self.assertNotIn('rationale', str(rows))
        self.assertEqual(rows[0]['conditions']['base_evidence'], rows[0]['conditions']['adapter_evidence'])
        self.assertEqual([m['role'] for m in rows[0]['conditions']['base_evidence']], ['system', 'user'])

    def test_changed_source_after_freeze_blocks_run(self):
        self.frozen(); (self.root/'source.txt').write_text('changed', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            b.runs(self.root, 'frozen', self.records())

    def test_unknown_fact_and_duplicate_json_keys_fail(self):
        for raw in ('{"decision":"tailored","decision":"not_demonstrated","statement":null}',
                    '{"decision":"tailored","statement":{"text":"Work","fact_id":"F9","requirement_id":"R1"}}'):
            with self.assertRaises(ValueError):
                b.validate_output(raw, self.case)

    def test_missing_records_remain_in_full_cohort(self):
        self.frozen(); b.blind(self.root, 'frozen', self.records()[:1], 'blinded')
        report = b.compare(self.root, 'frozen', 'blinded', [])
        self.assertEqual(report['arms']['adapter_evidence']['invalid_or_missing'], 1)
        self.assertEqual(report['arms']['adapter_evidence']['full_cohort_quality_mean'], 0)
        self.assertFalse(report['candidate_experiment_gate_met'])

    def test_blind_packet_hides_arm_and_output_change_fails_review(self):
        self.frozen(); b.blind(self.root, 'frozen', self.records(), 'blinded')
        rows = b.read_rows(self.root/'blinded/review_packet.jsonl')
        self.assertNotIn('condition', rows[0])
        reviews = self.reviews(); reviews[0]['output_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'output changed'):
            b.compare(self.root, 'frozen', 'blinded', reviews)

    def test_favorable_self_or_single_review_does_not_accept(self):
        self.frozen(); b.blind(self.root, 'frozen', self.records(), 'blinded')
        reviews = self.reviews()[::2]
        report = b.compare(self.root, 'frozen', 'blinded', reviews)
        self.assertFalse(report['all_outputs_human_reviewed'])
        reviews[0]['reviewer_type'] = 'model'
        with self.assertRaisesRegex(ValueError, 'Human'):
            b.compare(self.root, 'frozen', 'blinded', reviews)

    def test_tied_scores_cannot_outperform_or_promote(self):
        self.frozen(); b.blind(self.root, 'frozen', self.records(), 'blinded')
        report = b.compare(self.root, 'frozen', 'blinded', self.reviews())
        self.assertEqual(report['primary_quality_delta'], 0)
        self.assertIsNone(report['paired_cluster_bootstrap_95_interval'])
        self.assertFalse(report['candidate_experiment_gate_met'])
        self.assertFalse(report['model_promoted'])
        self.assertEqual(report['arms']['base_evidence']['passed'], 1)

    def test_unfavorable_reviewer_is_not_dropped(self):
        self.frozen(); b.blind(self.root, 'frozen', self.records(), 'blinded')
        reviews = self.reviews(); reviews[0]['checks']['entailed'] = False
        report = b.compare(self.root, 'frozen', 'blinded', reviews)
        self.assertEqual(sum(x['factuality_failures'] for x in report['arms'].values()), 1)

    def test_invalid_telemetry_and_runtime_mismatch_fail(self):
        self.frozen()
        records = self.records(); records[0]['metrics']['generation_ms'] = float('nan')
        with self.assertRaises(ValueError):
            b.runs(self.root, 'frozen', records)
        records = self.records(); records[0]['runtime']['revision'] = 'unreviewed'
        with self.assertRaisesRegex(ValueError, 'protocol'):
            b.runs(self.root, 'frozen', records)
        records = self.records(); records[1]['runtime']['tokenizer_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'tokenizer'):
            b.runs(self.root, 'frozen', records)

    def test_prompt_variant_preserves_gold_and_uses_frozen_messages(self):
        fm = self.frozen()
        vm = b.prompt_variant(self.root, 'frozen', 'Preserve exact evidence and scope.', 'variant')
        self.assertEqual(fm['cohort_sha256'], vm['cohort_sha256'])
        self.assertEqual(fm['files']['gold.jsonl'], vm['files']['gold.jsonl'])
        rows = self.records()[:2]
        inputs = b.read_rows(self.root/'variant/generation_inputs.jsonl')[0]
        for row in rows:
            row['messages_sha256'] = b.binding(inputs['conditions'][row['condition']])
        b.blind(self.root, 'variant', rows, 'blinded', comparison='prompt')
        report = b.compare(self.root, 'variant', 'blinded', [])
        self.assertEqual(set(report['arms']), {'base_original', 'base_evidence'})
        self.assertNotEqual(report['baseline_system_sha256'], report['candidate_system_sha256'])

    def test_training_targets_require_review_and_disjoint_employers(self):
        from adapters.tailor_study import training_rows
        target = b.validate_output(self.records()[0]['raw_output'], self.case)
        reviews = [{'reviewer_id': n, 'reviewer_type': 'human', 'source_checked': True,
            'entailed': True, 'qualifiers_preserved': True, 'target_sha256': b.binding(target)} for n in ('A','B')]
        case = deepcopy(self.case); case['source_group'] = 'training-employer'
        rows = [{'case': case, 'target': target, 'reviews': reviews}]
        self.assertEqual(len(training_rows(self.root, rows, [self.case])), 1)
        rows[0]['reviews'][0]['reviewer_type'] = None
        with self.assertRaisesRegex(ValueError, 'reviewed'):
            training_rows(self.root, rows, [self.case])
        rows[0]['case']['source_group'] = self.case['source_group']
        with self.assertRaisesRegex(ValueError, 'overlap'):
            training_rows(self.root, rows, [self.case])

    def test_html_annotation_does_not_execute_untrusted_text(self):
        from scripts.render_benchmark_review import render
        self.case['facts'][0]['scope'] = '</script><script>alert(1)</script> __ROWS__ __SLOT__'
        b.prepare(self.root, [self.case], 'prepared')
        with self.assertRaisesRegex(ValueError, 'reviewer slot'):
            render(self.root, 'prepared', 'invalid.html', '</script>')
        path = render(self.root, 'prepared', 'review.html', 'A')
        html = path.read_text(encoding='utf8')
        self.assertIn("connect-src 'none'", html)
        self.assertNotIn('https://', html)
        self.assertIn('review_A_completed.jsonl', html)
        self.assertIn('textContent', html)
        self.assertIn('Requirement source:', html)
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertIn('\\u003c/script\\u003e', html)
        self.assertIn('__ROWS__ __SLOT__', html)


if __name__ == '__main__':
    unittest.main()
