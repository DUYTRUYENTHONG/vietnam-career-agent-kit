import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from adapters.qwen35_pairing import checkpoint_binding
from experiments.qwen35_study.evaluate_pair import main
from scripts.evidence_bench import FIXTURE


class EvaluationPreflight(unittest.TestCase):
    def test_changed_base_or_adapter_cannot_use_training_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, adapter = root/'base', root/'adapter'
            for directory in (base, adapter):
                directory.mkdir()
                (directory/'test.safetensors').write_bytes(b'fictional-test-only')
            record = root/'training.json'
            record.write_text(json.dumps({'training_completed': True,
                'model': 'Qwen/Qwen3.5-4B', 'checkpoint_binding': checkpoint_binding(base),
                'adapter_binding': checkpoint_binding(adapter)}))
            argv = ['evaluate', '--dataset', str(FIXTURE), '--model-dir', str(base),
                '--adapter', str(adapter), '--training-record', str(record),
                '--budget-file', str(root/'budget.json'), '--output', str(root/'output')]
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()) as output:
                main()
            self.assertFalse(json.loads(output.getvalue())['inference_started'])
            self.assertFalse((root/'output').exists())
            for directory in (base, adapter):
                weight = directory/'test.safetensors'
                weight.write_bytes(b'changed')
                with patch.object(sys, 'argv', argv), self.assertRaisesRegex(ValueError, 'bytes differ'):
                    main()
                weight.write_bytes(b'fictional-test-only')

    def test_exposed_test_requires_explicit_acknowledgement(self):
        argv = ['evaluate', '--dataset', str(FIXTURE), '--partition', 'test']
        for name in ('model-dir', 'adapter', 'training-record', 'budget-file', 'output'):
            argv += ['--'+name, 'not-opened']
        with patch.object(sys, 'argv', argv), self.assertRaisesRegex(ValueError, 'exposed regression'):
            main()
