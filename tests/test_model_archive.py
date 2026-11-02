"""Fictional ZIP bytes only; no models, downloads, accounts or candidate data."""
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from core.model_archive import verify_archive

ROOT = Path(__file__).resolve().parents[1]
ENTRY = 'fictional-run/adapter/adapter_model.safetensors'
CONFIG = 'fictional-run/adapter/adapter_config.json'
WEIGHTS = b'fictional bytes, not loadable model weights'


class ModelArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / 'fictional.zip'
        self.metadata = json.dumps({'peft_type': 'LORA', 'task_type': 'CAUSAL_LM',
                                    'base_model_name_or_path': 'fictional/base'})
        self.make_archive()

    def make_archive(self, extra=(), *, config=None):
        with zipfile.ZipFile(self.archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(ENTRY, WEIGHTS)
            bundle.writestr(CONFIG, self.metadata if config is None else config)
            for name, value in extra:
                bundle.writestr(name, value)

    def invoke(self, **changes):
        args = {'archive_path': self.archive,
                'expected_sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                'adapter_entry': ENTRY,
                'expected_adapter_sha256': hashlib.sha256(WEIGHTS).hexdigest()}
        args.update(changes)
        return verify_archive(**args)

    def test_matching_archive_verifies_selected_bytes_without_loading_or_extracting(self):
        before = self.archive.read_bytes()
        result = self.invoke()
        self.assertEqual('1.0', result['schema_version'])
        self.assertEqual(hashlib.sha256(before).hexdigest(), result['archive']['sha256'])
        self.assertEqual(hashlib.sha256(WEIGHTS).hexdigest(), result['adapter']['sha256'])
        self.assertEqual('fictional/base', result['adapter']['declared_base'])
        self.assertEqual('not_assessed', result['training_status'])
        self.assertEqual('not_assessed', result['quality_status'])
        self.assertFalse(result['promotion_performed'])
        self.assertFalse(result['archive_extracted'])
        self.assertEqual(0, result['provider_calls'])
        self.assertEqual([self.archive], list(self.root.iterdir()))
        self.assertEqual(before, self.archive.read_bytes())

    def test_wrong_hashes_and_missing_adapter_fail(self):
        for changes in ({'expected_sha256': '0' * 64},
                        {'expected_adapter_sha256': '0' * 64},
                        {'adapter_entry': 'other/adapter_model.safetensors'},
                        {'expected_sha256': 'invalid'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.invoke(**changes)

    def test_flat_adapter_archives_are_supported(self):
        with zipfile.ZipFile(self.archive, 'w') as bundle:
            bundle.writestr('adapter_model.safetensors', WEIGHTS)
            bundle.writestr('adapter_config.json', self.metadata)
        result = self.invoke(adapter_entry='adapter_model.safetensors')
        self.assertEqual('adapter_model.safetensors', result['adapter']['entry'])

    def test_corrupt_zip_fails_even_when_its_outer_hash_matches(self):
        self.archive.write_bytes(b'not a ZIP file')
        with self.assertRaises(ValueError):
            self.invoke()

    def test_unsafe_and_case_colliding_entries_fail_without_extraction(self):
        for name in ('../outside', '/absolute', 'C:/absolute', 'a\\b',
                     'a//b', 'a/./b', 'aux.txt', 'path/CON', ENTRY.upper()):
            with self.subTest(name=name):
                info = zipfile.ZipInfo('placeholder')
                info.filename = info.orig_filename = name
                self.make_archive([(info, b'unsafe')])
                with self.assertRaises(ValueError):
                    self.invoke()
        link = zipfile.ZipInfo('linked.safetensors')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.make_archive([(link, b'outside')])
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertEqual([self.archive], list(self.root.iterdir()))

    def test_bounded_archive_and_declared_uncompressed_sizes(self):
        with patch('core.model_archive.MAX_ARCHIVE_BYTES', 1), self.assertRaises(ValueError):
            self.invoke()
        with patch('core.model_archive.MAX_UNCOMPRESSED_BYTES', 1), self.assertRaises(ValueError):
            self.invoke()
        with patch('core.model_archive.MAX_MEMBERS', 1), self.assertRaises(ValueError):
            self.invoke()

    def test_central_directory_is_bounded_before_zipfile_allocates_members(self):
        with patch('core.model_archive.MAX_MEMBERS', 1):
            with patch('core.model_archive.zipfile.ZipFile', side_effect=AssertionError('too late')):
                with self.assertRaises(ValueError):
                    self.invoke()
        # A forged EOCD count must not conceal additional actual headers.
        raw = bytearray(self.archive.read_bytes())
        end = raw.rfind(b'PK\x05\x06')
        struct.pack_into('<HH', raw, end + 8, 1, 1)
        self.archive.write_bytes(raw)
        with patch('core.model_archive.zipfile.ZipFile', side_effect=AssertionError('too late')):
            with self.assertRaises(ValueError):
                self.invoke()

    def test_corrupt_deflate_returns_cli_blocked_json_without_traceback(self):
        with zipfile.ZipFile(self.archive) as bundle:
            info = bundle.getinfo(ENTRY)
            offset = info.header_offset
        raw = bytearray(self.archive.read_bytes())
        name_size, extra_size = struct.unpack_from('<HH', raw, offset + 26)
        start = offset + 30 + name_size + extra_size
        raw[start:start + info.compress_size] = b'\xff' * info.compress_size
        self.archive.write_bytes(raw)
        output = self.root / 'blocked.json'
        result = subprocess.run([sys.executable, str(ROOT/'scripts/verify_training_archive.py'),
            '--archive', str(self.archive), '--sha256', hashlib.sha256(raw).hexdigest(),
            '--adapter-entry', ENTRY, '--adapter-sha256', hashlib.sha256(WEIGHTS).hexdigest(),
            '--output', str(output)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertEqual('blocked', json.loads(result.stdout)['outcome'])
        self.assertEqual('', result.stderr)
        self.assertFalse(output.exists())

    def test_zip64_locator_disguised_as_a_member_comment_is_rejected_early(self):
        info = zipfile.ZipInfo(CONFIG)
        info.comment = struct.pack('<4sLQL', b'PK\x06\x07', 0, 0, 1)
        for comment in (b'', b'x' * 65535):
            with self.subTest(comment_bytes=len(comment)):
                with zipfile.ZipFile(self.archive, 'w') as bundle:
                    bundle.writestr(ENTRY, WEIGHTS)
                    bundle.writestr(info, self.metadata)
                    bundle.comment = comment
                with patch('core.model_archive.zipfile.ZipFile', side_effect=AssertionError('too late')):
                    with self.assertRaises(ValueError):
                        self.invoke()

    def test_metadata_is_bounded_strict_data_and_never_executed(self):
        for content in ('[]', '{"peft_type":"LORA","peft_type":"OTHER"}',
                        '{"peft_type":"LORA","task_type":"CAUSAL_LM","base_model_name_or_path":NaN}',
                        self.metadata.replace('LORA', 'OTHER')):
            with self.subTest(content=content):
                self.make_archive(config=content)
                with self.assertRaises(ValueError):
                    self.invoke()
        self.make_archive()
        with patch('core.model_archive.MAX_METADATA_BYTES', 1), self.assertRaises(ValueError):
            self.invoke()

    def test_changed_archive_is_rejected_before_receipt(self):
        from core import model_archive
        digest = model_archive._stream_sha256
        calls = []

        def altered(stream):
            value = digest(stream)
            calls.append(value)
            return value if len(calls) < 3 else '0' * 64

        with patch('core.model_archive._stream_sha256', side_effect=altered), self.assertRaises(ValueError):
            self.invoke()
        self.assertEqual(3, len(calls))

    def test_cli_writes_new_external_receipt_and_never_overwrites(self):
        output = self.root / 'receipt.json'
        command = [sys.executable, str(ROOT / 'scripts/verify_training_archive.py'),
                   '--archive', str(self.archive), '--sha256', hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                   '--adapter-entry', ENTRY, '--adapter-sha256', hashlib.sha256(WEIGHTS).hexdigest(),
                   '--output', str(output)]
        first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        receipt = output.read_bytes()
        second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(2, second.returncode)
        self.assertEqual(receipt, output.read_bytes())
        command[-1] = str(ROOT / 'forbidden-archive-receipt.json')
        third = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(2, third.returncode)
        self.assertFalse((ROOT / 'forbidden-archive-receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
