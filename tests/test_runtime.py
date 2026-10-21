import unittest
from unittest.mock import patch

from core.runtime import diagnose


class RuntimeTests(unittest.TestCase):
    def test_generic_verification_is_limited_to_recorded_platform_matrix(self):
        with patch('core.runtime.platform.system', return_value='UnrecordedOS'):
            self.assertEqual('Experimental', diagnose().data['native_compatibility'])
        with patch('core.runtime.platform.system', return_value='Windows'), \
                patch('core.runtime.sys.version_info', (3, 12, 14)):
            self.assertEqual('Verified', diagnose().data['native_compatibility'])
