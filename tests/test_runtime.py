import unittest
from unittest.mock import patch

from core.runtime import diagnose


class RuntimeTests(unittest.TestCase):
    def test_optional_adapter_is_not_mistaken_for_default_live_execution(self):
        for runtime in ('generic', 'codex', 'claude', 'grok'):
            with self.subTest(runtime=runtime):
                result = diagnose(runtime).data
                self.assertFalse(result['browser_execution'])
                self.assertFalse(result['network_execution'])
                self.assertFalse(result['execution_engine']['standalone_browser_worker'])
                adapter = result['optional_browser_runtime']['tinyfish_browser']
                self.assertEqual('Experimental', adapter['status'])
                self.assertFalse(adapter['live_acceptance_verified'])
                self.assertIn('Supported host bridge', adapter['requires'])
                self.assertFalse(result['optional_public_research']['candidate_uploads'])

    def test_generic_verification_is_limited_to_recorded_platform_matrix(self):
        with patch('core.runtime.platform.system', return_value='UnrecordedOS'):
            self.assertEqual('Experimental', diagnose().data['native_compatibility'])
        with patch('core.runtime.platform.system', return_value='Windows'), \
                patch('core.runtime.sys.version_info', (3, 12, 14)):
            self.assertEqual('Verified', diagnose().data['native_compatibility'])
