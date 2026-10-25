import json
import unittest
from unittest.mock import patch
from adapters.providers.contracts import ResearchPlan, ProviderError, ContractError
from adapters.providers.tinyfish import TinyFish, HTTPTransport, ENDPOINT
from test_provider_contracts import plan


def dns(*args, **kwargs):
    return [(None, None, None, None, ('93.184.216.34', 443))]


def page(url):
    return {'url': url, 'final_url': url, 'text': '# Fictional vacancy'}


class TinyFishTests(unittest.TestCase):
    def test_ten_url_batch_order_and_partial_failure(self):
        raw = plan(); raw['urls'] = ['https://jobs.example.test/role?id='+str(i) for i in range(10)]
        calls = []
        def transport(method, endpoint, payload):
            calls.append(payload)
            self.assertEqual((method, endpoint), ('POST', ENDPOINT))
            self.assertEqual(payload, {'urls': raw['urls'], 'format': 'markdown'})
            return {'results': [page(u) for u in reversed(payload['urls']) if not u.endswith('3')],
                    'errors': [{'url': raw['urls'][3], 'message': 'SECRET'}]}
        results = TinyFish(transport, resolver=dns).fetch(ResearchPlan.parse(raw))
        self.assertEqual(len(calls), 1)
        self.assertEqual(results[3]['state'], 'manual_required')
        self.assertEqual(sum(r['state'] == 'completed' for r in results), 9)
        self.assertNotIn('SECRET', json.dumps(results))
        self.assertEqual(results[0]['data']['final_url'], raw['urls'][0])

    def test_uncertain_post_never_retries_or_leaks(self):
        calls = []
        def fail(*args):
            calls.append(args)
            raise RuntimeError('SECRET key')
        results = TinyFish(fail, resolver=dns).fetch(ResearchPlan.parse(plan()))
        self.assertEqual(len(calls), 1)
        self.assertTrue(results[0]['error']['possibly_accepted'])
        self.assertNotIn('SECRET', json.dumps(results))

    def test_scope_fails_before_network(self):
        calls = []
        provider = TinyFish(lambda *args: calls.append(args), resolver=dns)
        value = ResearchPlan.parse(plan())
        for urls in ([value.payload['urls'][0]]*11, ['https://evil.example/'], value.payload['urls']*2):
            with self.assertRaises(ContractError): provider.fetch(value, urls)
        self.assertEqual(calls, [])
        provider.resolver = lambda *a, **k: [(None, None, None, None, ('127.0.0.1', 443))]
        with self.assertRaises(ContractError): provider.fetch(value)

    def test_success_requires_valid_unique_exact_destination_evidence(self):
        value = ResearchPlan.parse(plan()); url = value.payload['urls'][0]
        for response in ({}, {'results': []}, {'results': [page(url), page(url)]},
                         {'results': [{**page(url), 'final_url': 'https://evil.example/'}]},
                         {'results': [{**page(url), 'text': ''}]}):
            result = TinyFish(lambda *a: response, resolver=dns).fetch(value)[0]
            self.assertEqual(result['state'], 'manual_required')

    def test_transport_has_fixed_origin_and_hides_errors(self):
        with self.assertRaises(ProviderError): HTTPTransport('bad\nkey')
        transport = HTTPTransport('fictional-key')
        with self.assertRaises(ProviderError): transport('POST', ENDPOINT+'/evil', {})
        with patch('adapters.providers.tinyfish.build_opener', side_effect=RuntimeError('SECRET')):
            with self.assertRaises(ProviderError) as ctx: transport('POST', ENDPOINT, {})
        self.assertEqual(str(ctx.exception), 'transport_failure')
        self.assertTrue(ctx.exception.possibly_accepted)
        self.assertFalse(TinyFish.capabilities.goal_interaction)
        self.assertFalse(TinyFish.capabilities.uploads)


if __name__ == '__main__': unittest.main()
