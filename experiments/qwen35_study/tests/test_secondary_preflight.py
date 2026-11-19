import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.qwen35_study.evaluate_secondary import main
from scripts.evidence_bench import FIXTURE


class SecondaryPreflight(unittest.TestCase):
    def test_preflight_never_runs_inference_and_rejects_other_architecture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / 'model'
            model.mkdir()
            (model / 'test.safetensors').write_bytes(b'fictional-unit-test-not-a-model')
            config = model / 'config.json'
            config.write_text(json.dumps({'model_type': 'qwen3', 'hidden_size': 2560,
                                          'num_hidden_layers': 36}))
            argv = ['evaluate', '--dataset', str(FIXTURE), '--model-dir', str(model),
                    '--budget-file', str(root / 'budget.json'), '--output', str(root / 'output')]
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()) as out:
                main()
            self.assertFalse(json.loads(out.getvalue())['inference_started'])
            self.assertFalse((root / 'output').exists())
            config.write_text('{"model_type":"different"}')
            with patch.object(sys, 'argv', argv), self.assertRaisesRegex(ValueError, 'architecture'):
                main()

    def test_exposed_test_requires_acknowledgement(self):
        argv = ['evaluate', '--partition', 'test']
        for name in ('dataset', 'model-dir', 'budget-file', 'output'):
            argv += ['--' + name, 'not-opened']
        with patch.object(sys, 'argv', argv), self.assertRaisesRegex(ValueError, 'exposed regression'):
            main()
