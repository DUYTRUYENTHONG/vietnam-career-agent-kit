"""Durable host handoffs tested with fictional callbacks, not model API calls."""
import unittest
import io
from contextlib import redirect_stdout
from core import reviewer_automation as h, cv_review_agents as a, tailor_benchmark as b
from tests import test_cv_review_agents as fixture


class AutomationTests(unittest.TestCase):
    setUp = fixture.ReviewerTests.setUp
    requests = fixture.ReviewerTests.requests
    response = fixture.ReviewerTests.response

    def cycle(self):
        self.requests(); h.start(self.root, 'requests', 'cycle')

    def test_automatic_callback_runs_three_roles_then_needs_human_resolution(self):
        self.cycle(); calls = []
        def respond(request):
            calls.append(request['role']); return self.response(request['role'])
        result = h.run_with_host(self.root, 'cycle', respond)
        self.assertEqual(calls, list(a.ROLES))
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(result['human_resolution_required'])
        self.assertFalse(result['human_gold_created'])
        self.assertEqual(h.run_with_host(self.root, 'cycle', respond), result)
        self.assertEqual(len(calls), 3)

    def test_pending_handoff_is_durable_and_never_reissued_after_restart(self):
        self.cycle(); first = h.advance(self.root, 'cycle')
        self.assertEqual(first['request']['role'], 'evidence')
        second = h.advance(self.root, 'cycle')
        self.assertEqual(second['status'], 'waiting_for_original_reply')
        self.assertNotIn('request', second)
        self.assertFalse(second['reissue_permitted'])
        next_role = h.advance(self.root, 'cycle', self.response())
        self.assertEqual(next_role['request']['role'], 'requirements')

    def test_callback_failure_leaves_pending_not_automatic_retry(self):
        self.cycle()
        def fail(request):
            raise RuntimeError('Fictional host interruption')
        with self.assertRaises(RuntimeError):
            h.run_with_host(self.root, 'cycle', fail)
        self.assertEqual(h.run_with_host(self.root, 'cycle', fail)['status'], 'waiting_for_original_reply')

    def test_invalid_reply_is_captured_and_stops_cycle(self):
        self.cycle(); h.advance(self.root, 'cycle')
        response = self.response(); response['reviewer_type'] = 'human'
        with self.assertRaisesRegex(ValueError, 'model-labelled'):
            h.advance(self.root, 'cycle', response)
        self.assertTrue((self.root/'cycle/failed.json').exists())
        with self.assertRaisesRegex(ValueError, 'no automatic retry'):
            h.advance(self.root, 'cycle', self.response())

    def test_wrong_role_does_not_advance_and_duplicates_cannot_overwrite(self):
        self.cycle(); h.advance(self.root, 'cycle')
        with self.assertRaisesRegex(ValueError, 'pending role'):
            h.advance(self.root, 'cycle', self.response('editorial'))
        with self.assertRaises(ValueError):
            h.start(self.root, 'requests', 'cycle')

    def test_changed_sources_stop_even_completed_cycle(self):
        self.cycle(); h.run_with_host(self.root, 'cycle', lambda r: self.response(r['role']))
        (self.root/'source.txt').write_text('changed', encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            h.advance(self.root, 'cycle')

    def test_exact_complete_advisory_can_be_reused_without_model_handoffs(self):
        self.requests(); responses = [self.response(r) for r in a.ROLES]
        a.collect(self.root, 'requests', responses, 'prior')
        h.start(self.root, 'requests', 'cycle', 'prior')
        result = h.run_with_host(self.root, 'cycle', lambda _: self.fail('No callback expected'))
        self.assertEqual(result['cached_roles'], 3)
        self.assertFalse(list((self.root/'cycle').glob('issued-*.json')))

    def test_incomplete_cache_cannot_be_treated_as_completed_review(self):
        self.requests(); a.collect(self.root, 'requests', [self.response()], 'prior')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            h.start(self.root, 'requests', 'cycle', 'prior')

    def test_changed_draft_cache_does_not_match_new_requests(self):
        self.requests(); a.collect(self.root, 'requests', [self.response(r) for r in a.ROLES], 'prior')
        # A different draft makes the request manifest different, even with the same source case.
        a.prepare(self.root, 'prepared', 'new-requests', [{'id': 'S2', 'text': 'Changed draft', 'fact_id': 'F1'}])
        with self.assertRaisesRegex(ValueError, 'different requests'):
            h.start(self.root, 'new-requests', 'cycle', 'prior')

    def test_changed_prompt_alone_invalidates_cache(self):
        self.requests(); a.collect(self.root, 'requests', [self.response(r) for r in a.ROLES], 'prior')
        folder, manifest = b.verify_bundle(self.root, 'requests', 'cv_ai_review_requests')
        rows = b.read_rows(folder/'requests.jsonl')
        rows[0]['messages'][0]['content'] += '\nCheck prototype scope.'
        files = {name: (folder/name).read_bytes() for name in manifest['files']}
        files['requests.jsonl'] = b.rows_bytes(rows)
        b.bundle(self.root, 'changed-prompts', files, {k:v for k,v in manifest.items() if k != 'files'})
        with self.assertRaisesRegex(ValueError, 'different requests'):
            h.start(self.root, 'changed-prompts', 'cycle', 'prior')

    def test_lost_acknowledgement_is_idempotent_without_reissuing_next_role(self):
        self.cycle(); h.advance(self.root, 'cycle')
        h.advance(self.root, 'cycle', self.response())
        before = (self.root/'cycle/response-1.json').read_bytes()
        result = h.advance(self.root, 'cycle', self.response())
        self.assertEqual(result['status'], 'waiting_for_original_reply')
        self.assertEqual(result['role'], 'requirements')
        self.assertNotIn('request', result)
        self.assertEqual((self.root/'cycle/response-1.json').read_bytes(), before)
        conflicting = self.response(); conflicting['model_id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'Conflicting replay'):
            h.advance(self.root, 'cycle', conflicting)

    def test_lock_and_corrupted_response_fail_closed(self):
        self.cycle(); (self.root/'cycle/write.lock').write_text('other writer')
        with self.assertRaises(FileExistsError):
            h.advance(self.root, 'cycle')
        (self.root/'cycle/write.lock').unlink()
        h.advance(self.root, 'cycle'); h.advance(self.root, 'cycle', self.response())
        path = self.root/'cycle/response-1.json'; value = b.read_json(path)
        value['response']['model_id'] = 'tampered'; path.write_bytes(b.json_bytes(value))
        with self.assertRaisesRegex(ValueError, 'reply changed'):
            h.advance(self.root, 'cycle')

    def test_cli_start_acknowledge_and_wait_without_replay(self):
        from scripts.cv_review_agents import main
        self.requests()
        base = ['--root', str(self.root)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(base+['start', '--requests', 'requests', '--cycle', 'cycle']), 0)
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(main(base+['advance', '--cycle', 'cycle']), 0)
        self.assertEqual(b.decode(stream.getvalue())['request']['role'], 'evidence')
        (self.root/'reply.json').write_bytes(b.json_bytes(self.response()))
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(main(base+['advance', '--cycle', 'cycle', '--response', 'reply.json']), 0)
        self.assertEqual(b.decode(stream.getvalue())['request']['role'], 'requirements')
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(main(base+['advance', '--cycle', 'cycle']), 0)
        self.assertEqual(b.decode(stream.getvalue())['status'], 'waiting_for_original_reply')


if __name__ == '__main__':
    unittest.main()
