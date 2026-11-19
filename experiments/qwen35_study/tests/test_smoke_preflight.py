import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.qwen35_study.smoke_4b import main


class SmokePreflight(unittest.TestCase):
    def test_preflight_never_imports_or_runs_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / 'model'
            model.mkdir()
            (model / 'test.safetensors').write_bytes(b'unit-fixture-not-a-model')
            data = root / 'data.jsonl'
            data.write_text('{}\n' * 10000)
            argv = ['smoke', '--data', str(data), '--sha256', hashlib.sha256(data.read_bytes()).hexdigest(),
                    '--model-dir', str(model), '--output', str(root/'out'),
                    '--budget-file', str(root/'budget.json')]
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()) as out:
                main()
            self.assertFalse(json.loads(out.getvalue())['model_loaded'])
            self.assertFalse((root / 'out').exists())
            argv[argv.index('--sha256') + 1] = 'wrong'
            with patch.object(sys, 'argv', argv), self.assertRaisesRegex(ValueError, 'hash'):
                main()
