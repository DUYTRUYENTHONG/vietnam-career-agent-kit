"""Fictional corpus behavior; no network, candidate files or models."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from core.requirement_corpus import apply_extractions, build_corpus, collect_legacy, write_corpus


def snapshot(key='A', text='Requirements:\nNo Docker required.\n2–4 years; USD 1000/month.'):
    return {'id': key, 'employer': 'Fictional Example', 'job_key': key,
            'source_url': 'https://example.test/jobs/'+key, 'raw_text': text,
            'source_kind': 'full_jd', 'requirements': [
                {'id': 'R1', 'quote': 'No Docker required.', 'kind': 'required'}]}


class RequirementCorpusTests(unittest.TestCase):
    def test_extraction_sidecar_binds_exact_current_raw_capture_without_upgrading_source(self):
        import hashlib
        a = snapshot(); a['requirements'] = []; a['source_kind'] = 'unknown'
        packet = {'schema_version': 'requirements-extractions-v1', 'records': [
            {'id': 'A', 'raw_text_sha256': hashlib.sha256(a['raw_text'].encode()).hexdigest(),
             'requirements': [{'id': 'R1', 'quote': 'No Docker required.', 'kind': 'unknown'}]}]}
        result = build_corpus(apply_extractions([a], packet))
        self.assertEqual(1, len(result['requirements']))
        self.assertEqual('unknown', result['requirements'][0]['sources'][0]['source_kind'])
        self.assertEqual([], a['requirements'])
        packet['records'][0]['raw_text_sha256'] = '0'*64
        with self.assertRaises(ValueError): apply_extractions([a], packet)

    def test_cleaning_preserves_negation_units_and_every_duplicate_source(self):
        a = snapshot(); b = snapshot('B', a['raw_text'].replace('\n', '\r\n'))
        result = build_corpus([a, b])
        self.assertEqual(1, len(result['documents']))
        self.assertEqual(2, len(result['documents'][0]['sources']))
        self.assertIn('No Docker required.', result['documents'][0]['text'])
        self.assertIn('2–4 years; USD 1000/month.', result['documents'][0]['text'])
        self.assertEqual(1, len(result['requirements']))
        self.assertEqual(2, len(result['requirements'][0]['sources']))
        self.assertFalse(result['summary']['training_ready'])

    def test_repeated_quotes_cannot_amplify_large_source_metadata_without_a_bound(self):
        rows = []
        for i in range(4):
            rows.append({'id': 'I'*3000+str(i), 'employer': 'E'*3000,
                         'job_key': 'J'*3000, 'source_url': 'https://example.test/'+'x'*3000,
                         'raw_text': 'Python', 'source_kind': 'excerpt',
                         'requirements': [{'id': str(j), 'quote': 'Python', 'kind': 'unknown'}
                                          for j in range(500)]})
        with self.assertRaisesRegex(ValueError, 'provenance'):
            build_corpus(rows)

    def test_conflicting_kinds_remain_pending_and_unknown_capture_stays_unknown(self):
        a = snapshot(); b = snapshot('B')
        b['source_kind'] = 'assessment_summary'
        b['requirements'][0]['kind'] = 'preferred'
        result = build_corpus([a, b])
        r = result['requirements'][0]
        self.assertTrue(r['classification_conflict'])
        self.assertEqual('pending_extraction_review', r['review_status'])
        self.assertIsNone(result['documents'][0]['sources'][0]['captured_utc'])
        self.assertIn('assessment_summary', {s['source_kind'] for s in r['sources']})

    def test_whole_packet_is_validated_before_any_export(self):
        for change in ({'requirements': [{'id': 'R1', 'quote': 'Expert CUDA', 'kind': 'required'}]},
                       {'source_url': 'https://user:secret@example.invalid/job'},
                       {'source_kind': 'automatically_verified'}, {'source_kind': []},
                       {'requirements': [{'id': 'R1', 'quote': 'No Docker required.', 'kind': []}]}):
            row = snapshot(); row.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_corpus([snapshot('first'), row])
        with self.assertRaises(ValueError): build_corpus([snapshot(), snapshot()])
        with self.assertRaises(ValueError): build_corpus([])

    def test_export_is_complete_private_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as t:
            target = Path(t)/'run'
            result = write_corpus(build_corpus([snapshot()]), target)
            manifest = json.loads((target/'manifest.json').read_text())
            self.assertFalse(manifest['training_ready'])
            self.assertEqual(0, manifest['model_calls'])
            self.assertEqual(result['files'], manifest['files'])
            with self.assertRaises(FileExistsError):
                write_corpus(build_corpus([snapshot()]), target)
            repo = Path(__file__).resolve().parents[1]
            with self.assertRaises(ValueError):
                write_corpus(build_corpus([snapshot()]), repo/'forbidden-corpus')

    def test_legacy_collection_is_read_only_bounded_and_does_not_claim_extraction(self):
        with tempfile.TemporaryDirectory() as t:
            dbpath = Path(t)/'old.sqlite3'
            with closing(sqlite3.connect(dbpath)) as db:
                db.execute('CREATE TABLE jobs(id INTEGER,employer TEXT,platform TEXT,platform_job_id TEXT,req_id TEXT,title TEXT,url TEXT,raw_jd TEXT,updated_utc TEXT)')
                db.executemany('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)', [
                    (i, 'Fictional', 'manual', str(i), '', 'AI Engineer',
                     'https://example.test/'+str(i), 'Python knowledge.', '2026-01-01T00:00:00Z') for i in (1, 2)])
                db.commit()
            before = dbpath.read_bytes()
            result = build_corpus(collect_legacy(dbpath, limit=2))
            self.assertEqual(2, result['summary']['input_records'])
            self.assertEqual([], result['requirements'])
            self.assertEqual(before, dbpath.read_bytes())
            with self.assertRaises(ValueError): collect_legacy(dbpath, limit=1)
            with self.assertRaises(ValueError): collect_legacy(Path(t)/'missing.sqlite3')
            self.assertFalse((Path(t)/'missing.sqlite3').exists())

    def test_unicode_normalization_keeps_original_raw_bytes_and_validates_exact_quote(self):
        a = snapshot(text='Yêu cầu:\nPython không bắt buộc.'); a['requirements'] = []
        b = snapshot('B', 'Ye\u0302u ca\u0302\u0300u:\nPython không bắt buộc.'); b['requirements'] = []
        result = build_corpus([a, b])
        self.assertEqual(1, len(result['documents']))
        refs = result['documents'][0]['sources']
        self.assertNotEqual(refs[0]['raw_text_sha256'], refs[1]['raw_text_sha256'])
        self.assertNotEqual(result['raw_records'][0]['raw_text'], result['raw_records'][1]['raw_text'])

    def test_cli_creates_review_queue_and_invalid_input_creates_no_output(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); source = root/'source.jsonl'; target = root/'run'
            source.write_text(json.dumps(snapshot()), encoding='utf8')
            args = [sys.executable, str(repo/'scripts/requirements_corpus.py'),
                    '--snapshots', str(source), '--output', str(target)]
            run = subprocess.run(args, cwd=repo, capture_output=True, text=True)
            self.assertEqual(0, run.returncode, run.stdout+run.stderr)
            self.assertFalse(json.loads(run.stdout)['training_ready'])
            self.assertTrue((target/'manifest.json').is_file())
            source.write_text('{invalid', encoding='utf8')
            args[-1] = str(root/'invalid-run')
            run = subprocess.run(args, cwd=repo, capture_output=True, text=True)
            self.assertEqual(1, run.returncode)
            self.assertFalse((root/'invalid-run').exists())


if __name__ == '__main__':
    unittest.main()
