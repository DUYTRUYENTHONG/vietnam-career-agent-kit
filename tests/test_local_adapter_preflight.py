"""Fictional metadata only: no model SDK, training, accounts or downloads."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adapters.local_qwen import generate


class LocalAdapterPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root/'base'; self.base.mkdir()
        self.adapter = self.root/'adapter'; self.adapter.mkdir()
        (self.base/'config.json').write_text('{}', encoding='utf8')
        (self.base/'model.safetensors').write_bytes(b'fictional base, not executable')
        (self.adapter/'adapter_model.safetensors').write_bytes(b'fictional adapter')
        self.config = {'base_model_name_or_path': str(self.base.resolve()),
                       'peft_type': 'LORA', 'task_type': 'CAUSAL_LM'}
        self.save_config()

    def save_config(self):
        (self.adapter/'adapter_config.json').write_text(json.dumps(self.config), encoding='utf8')

    def preflight(self):
        from adapters.local_model_preflight import preflight_adapter
        return preflight_adapter(self.base, self.adapter)

    def manifest(self):
        value = {'model': 'Fictional/Qwen3', 'revision': 'a'*40,
                 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in self.base.iterdir() if p.is_file()}}
        (self.base/'download-manifest.json').write_text(json.dumps(value), encoding='utf8')
        self.config['base_model_name_or_path'] = value['model']; self.save_config()
        return value

    def test_wrong_base_fails_before_optional_sdk_import(self):
        self.config['base_model_name_or_path'] = 'Fictional/Qwen2.5'; self.save_config()
        real_import = __import__
        def reject_sdk(name, *args, **kwargs):
            if name in ('torch', 'transformers', 'peft'):
                raise AssertionError('Optional SDK imported before identity rejection')
            return real_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=reject_sdk):
            with self.assertRaisesRegex(ValueError, 'base'):
                generate(self.base, [{'role': 'user', 'content': 'fictional'}],
                         adapter_directory=self.adapter, max_new_tokens=1)

    def test_same_explicit_local_base_is_supported(self):
        self.assertEqual(self.adapter.resolve(), self.preflight())

    def test_pinned_hub_reference_requires_all_manifest_bytes(self):
        self.manifest()
        self.assertEqual(self.adapter.resolve(), self.preflight())
        (self.base/'model.safetensors').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.preflight()

    def test_missing_malformed_or_oversized_config_is_rejected(self):
        path = self.adapter/'adapter_config.json'
        for content in ('[]', '{broken', '{"peft_type":"LORA","peft_type":"P_TUNING"}', ' '*1048577):
            path.write_text(content, encoding='utf8')
            with self.assertRaises(ValueError): self.preflight()
        path.unlink()
        with self.assertRaises(ValueError): self.preflight()

    def test_missing_weights_wrong_method_or_task_are_rejected(self):
        for field, value in [('peft_type', 'P_TUNING'), ('task_type', 'SEQ_CLS'),
                             ('base_model_name_or_path', ''), ('base_model_name_or_path', None)]:
            with self.subTest(field=field, value=value):
                old = self.config[field]; self.config[field] = value; self.save_config()
                with self.assertRaises(ValueError): self.preflight()
                self.config[field] = old
        self.save_config()
        (self.adapter/'adapter_model.safetensors').unlink()
        with self.assertRaises(ValueError): self.preflight()

    def test_other_local_directory_is_not_an_identity_alias(self):
        other = self.root/'other'; other.mkdir()
        self.config['base_model_name_or_path'] = str(other.resolve()); self.save_config()
        with self.assertRaisesRegex(ValueError, 'base'): self.preflight()

    def test_hub_revision_and_unsafe_manifest_paths_are_rejected(self):
        manifest = self.manifest()
        self.config['revision'] = 'b'*40; self.save_config()
        with self.assertRaisesRegex(ValueError, 'revision'): self.preflight()
        self.config.pop('revision'); self.save_config()
        manifest['files']['../outside.safetensors'] = '0'*64
        (self.base/'download-manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        with self.assertRaises(ValueError): self.preflight()

    def test_manifest_requires_config_and_base_safetensors(self):
        manifest = self.manifest()
        manifest['files'] = {'config.json': manifest['files']['config.json']}
        (self.base/'download-manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        with self.assertRaises(ValueError): self.preflight()

    def sharded_manifest(self):
        (self.base/'model.safetensors').unlink()
        (self.base/'model-00001-of-00001.safetensors').write_bytes(b'fictional shard')
        (self.base/'model.safetensors.index.json').write_text(json.dumps({
            'weight_map': {'fictional.weight': 'model-00001-of-00001.safetensors'}}), encoding='utf8')
        return self.manifest()

    def test_unlisted_monolithic_checkpoint_cannot_override_verified_shards(self):
        self.sharded_manifest()
        self.assertEqual(self.adapter.resolve(), self.preflight())
        (self.base/'model.safetensors').write_bytes(b'unverified higher-priority checkpoint')
        with self.assertRaises(ValueError): self.preflight()
        with patch.dict('sys.modules', {'torch': None, 'transformers': None, 'peft': None}):
            with self.assertRaises(ValueError):
                generate(self.base, [{'role': 'user', 'content': 'fictional'}],
                         adapter_directory=self.adapter, max_new_tokens=1)

    def test_shard_index_must_bind_every_referenced_file(self):
        manifest = self.sharded_manifest()
        manifest['files'].pop('model-00001-of-00001.safetensors')
        (self.base/'download-manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        with self.assertRaises(ValueError): self.preflight()

    def test_unknown_checkpoint_layout_and_unlisted_metadata_fail(self):
        manifest = self.manifest()
        (self.base/'model.safetensors').rename(self.base/'unknown.safetensors')
        manifest['files']['unknown.safetensors'] = manifest['files'].pop('model.safetensors')
        (self.base/'download-manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        with self.assertRaises(ValueError): self.preflight()

    def test_unlisted_tokenizer_metadata_is_not_loaded(self):
        self.manifest()
        (self.base/'tokenizer_config.json').write_text('{}', encoding='utf8')
        with self.assertRaises(ValueError): self.preflight()

    def test_case_variant_checkpoint_cannot_override_verified_shards(self):
        self.sharded_manifest()
        for name in ('MODEL.SAFETENSORS', 'model.SafeTensors'):
            with self.subTest(name=name):
                path = self.base/name
                path.write_bytes(b'unlisted case variant')
                with self.assertRaises(ValueError): self.preflight()
                path.unlink()
