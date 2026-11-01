"""Fictional Codex exports must not invent measurements or retain chat content."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core.codex_usage import normalize_export
from core.execution import Executor
from core.performance import record, report


class CodexUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root / 'explicit-export.jsonl'
        self.output = self.root / 'private' / 'reports' / 'performance' / 'codex-one'

    def stream(self, *extra):
        rows = [
            {'type': 'thread.started', 'thread_id': 'fictional-thread-one'},
            {'type': 'turn.started'},
            {'type': 'item.completed', 'item': {'type': 'agent_message',
                'text': 'PRIVATE CV AND SECRET SHOULD NOT BE COPIED'}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 100,
                'cached_input_tokens': 60, 'output_tokens': 20,
                'reasoning_output_tokens': 5}}, *extra]
        self.raw.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf8')
        return rows

    def normalize(self, **kwargs):
        return normalize_export(self.raw, self.output, task_id='task-one',
            workload_id='fictional-tailoring', phase='generation',
            observed_utc='2026-01-02T03:04:05+00:00', **kwargs)

    def test_cli_export_round_trips_through_existing_performance_storage(self):
        self.stream()
        result = self.normalize()
        self.assertFalse((self.root/'private'/'workflow.sqlite3').exists())
        event = json.loads(Path(result['observations'][0]).read_text(encoding='utf8'))
        self.assertEqual('agent_turn', event['measurement_scope'])
        self.assertEqual({'kind': 'per_turn', 'input_tokens': 100,
            'cached_input_tokens': 60, 'output_tokens': 20, 'reasoning_tokens': 5}, event['usage'])
        self.assertIsNone(event['model_id'])
        self.assertIsNone(event['effort'])
        self.assertIsNone(event['duration_ms'])
        self.assertIsNone(event['cost'])
        self.assertFalse(event['accepted'])
        source = Path(event['source']['path'])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), event['source']['sha256'])
        all_text = ''.join(p.read_text(encoding='utf8') for p in self.output.iterdir())
        self.assertNotIn('PRIVATE CV', all_text)
        self.assertNotIn('fictional-thread-one', all_text)
        work = Executor(self.root/'private')
        work.init()
        self.assertFalse(record(work, event).data['reused'])
        self.assertTrue(record(work, event).data['reused'])
        group = report(work).data['groups'][0]
        self.assertEqual(100, group['known_tokens']['input_tokens'])
        self.assertEqual(20, group['known_tokens']['output_tokens'])
        self.assertEqual(0, group['duration_ms']['known'])

    def test_failed_turn_missing_usage_and_caller_model_metadata_stay_distinct(self):
        self.stream({'type': 'turn.started'}, {'type': 'error', 'message': 'PRIVATE ERROR'},
            {'type': 'turn.failed', 'error': {'message': 'PRIVATE ERROR'}})
        result = self.normalize(model_id='example/model', effort='low')
        events = [json.loads(Path(p).read_text(encoding='utf8')) for p in result['observations']]
        self.assertEqual(['success', 'failed'], [e['status'] for e in events])
        self.assertTrue(all(not e['accepted'] for e in events))
        self.assertTrue(all(v is None for k,v in events[1]['usage'].items() if k != 'kind'))
        source = json.loads(Path(events[0]['source']['path']).read_text(encoding='utf8'))
        self.assertEqual('caller_supplied_not_provider_authenticated', source['model_metadata_origin'])
        self.assertNotIn('PRIVATE ERROR', ''.join(p.read_text() for p in self.output.iterdir()))

    def test_unknown_usage_is_not_zero_and_resume_identity_is_not_rekeyed(self):
        rows = self.stream()
        rows[-1].pop('usage')
        self.raw.write_text('\n'.join(map(json.dumps, rows)), encoding='utf8')
        first = json.loads(Path(self.normalize()['observations'][0]).read_text())
        self.assertIsNone(first['usage']['input_tokens'])
        # Changing the source bytes must not manufacture a fresh telemetry identity.
        self.raw.write_text('\n'.join(map(json.dumps, rows))+'\n\n', encoding='utf8')
        self.output = self.output.with_name('codex-two')
        second = json.loads(Path(self.normalize()['observations'][0]).read_text())
        self.assertEqual(first['event_id'], second['event_id'])

    def test_explicit_zero_is_preserved_without_promoting_quality_or_cost(self):
        rows=self.stream()
        rows[-1]['usage']={k:0 for k in rows[-1]['usage']}
        self.raw.write_text('\n'.join(map(json.dumps, rows)), encoding='utf8')
        event=json.loads(Path(self.normalize()['observations'][0]).read_text())
        self.assertEqual(0,event['usage']['reasoning_tokens'])
        self.assertEqual(0,event['usage']['input_tokens'])
        self.assertFalse(event['accepted'])
        self.assertIsNone(event['cost'])

    def test_unicode_separators_inside_omitted_payload_are_not_jsonl_boundaries(self):
        rows=self.stream()
        rows[2]['item']['text']='PRIVATE\u0085MESSAGE\u2028TOOL\u2029CONTENT'
        self.raw.write_bytes(('\r\n'.join(json.dumps(r,ensure_ascii=False)
            for r in rows)+'\r\n').encode('utf8'))
        result=self.normalize()
        self.assertEqual(1,len(result['observations']))
        content=''.join(p.read_text(encoding='utf8') for p in self.output.iterdir())
        self.assertNotIn('PRIVATE',content)
        self.assertNotIn('MESSAGE',content)

    def test_incomplete_ambiguous_and_invalid_streams_write_nothing(self):
        valid = self.stream()
        cases = [valid[:-1], valid[:2]+[{'type':'turn.started'}]+valid[2:],
            valid+[{'type':'thread.started','thread_id':'another'}],
            [{'type':'turn.completed','usage':{}}],
            valid+[{'type':'token_count','info':{'total_token_usage':1000}}]]
        for rows in cases:
            with self.subTest(rows=[r['type'] for r in rows]):
                self.raw.write_text('\n'.join(map(json.dumps,rows)),encoding='utf8')
                with self.assertRaises(ValueError): self.normalize()
                self.assertFalse(self.output.exists())
        for field,value in [('input_tokens',True),('input_tokens',-1),
                ('input_tokens',10**13),('cached_input_tokens',101),
                ('reasoning_output_tokens',21),('cumulative_tokens',100)]:
            with self.subTest(field=field,value=value):
                rows=self.stream();rows[-1]['usage'][field]=value
                self.raw.write_text('\n'.join(map(json.dumps,rows)),encoding='utf8')
                with self.assertRaises(ValueError): self.normalize()
                self.assertFalse(self.output.exists())

    def test_duplicate_json_keys_size_bounds_and_existing_output_fail_closed(self):
        self.raw.write_text('{"type":"thread.started","type":"turn.completed"}\n')
        with self.assertRaises(ValueError): self.normalize()
        self.assertFalse(self.output.exists())
        self.raw.write_bytes(b' '*10_000_001)
        with self.assertRaises(ValueError): self.normalize()
        self.assertFalse(self.output.exists())
        self.stream();self.output.mkdir(parents=True)
        marker=self.output/'keep.txt';marker.write_text('preserve')
        with self.assertRaises(ValueError): self.normalize()
        self.assertEqual(['keep.txt'],[p.name for p in self.output.iterdir()])
        with self.assertRaises(ValueError): self.normalize(effort='low')

    def test_script_has_a_bounded_offline_machine_readable_result(self):
        self.stream()
        command=[sys.executable,'scripts/normalize_codex_usage.py',
            '--input',str(self.raw),'--output-dir',str(self.output),
            '--task-id','task-one','--workload-id','fictional-tailoring',
            '--phase','generation','--observed-utc','2026-01-02T03:04:05Z']
        run=subprocess.run(command,capture_output=True,encoding='utf8',timeout=15)
        self.assertEqual(0,run.returncode,run.stderr)
        data=json.loads(run.stdout)
        self.assertEqual('ok',data['outcome'])
        self.assertEqual(1,len(data['data']['observations']))
        self.assertFalse((self.root/'private'/'workflow.sqlite3').exists())
        again=subprocess.run(command,capture_output=True,encoding='utf8',timeout=15)
        self.assertNotEqual(0,again.returncode)
        self.assertEqual('blocked',json.loads(again.stdout)['outcome'])


if __name__ == '__main__':
    unittest.main()
