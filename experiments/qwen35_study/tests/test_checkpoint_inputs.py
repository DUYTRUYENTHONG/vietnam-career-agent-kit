from pathlib import Path
import tempfile
import unittest

from adapters.qwen35_pairing import checkpoint_binding


class CheckpointInputs(unittest.TestCase):
    def test_tokenizer_merges_and_template_changes_invalidate_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'test.safetensors').write_bytes(b'unit-test-only')
            for filename in ('merges.txt', 'chat_template.jinja'):
                path = root / filename
                path.write_text('first')
                initial = checkpoint_binding(root)
                path.write_text('changed')
                self.assertNotEqual(initial, checkpoint_binding(root), filename)
