"""Verify explicitly selected downloaded adapter bytes without extracting/loading.

Checksums must come from a separately trusted source. Matching bytes do not prove
publisher identity, valid tensors, training success, compatibility or CV quality.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import zipfile
import zlib

MAX_ARCHIVE_BYTES = 1024 ** 3
MAX_UNCOMPRESSED_BYTES = 1024 ** 3
MAX_MEMBERS = 200
MAX_METADATA_BYTES = 1024 ** 2
MAX_DIRECTORY_BYTES = 1024 ** 2
_RESERVED = {'con', 'prn', 'aux', 'nul'} | {f'{p}{i}' for p in ('com', 'lpt') for i in range(1, 10)}


def _stream_sha256(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    return digest.hexdigest()


def _entry_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', name):
        raise ValueError('Archive entries must use portable relative names')
    clean = name[:-1] if name.endswith('/') else name
    parts = clean.split('/')
    if (not clean or PurePosixPath(clean).is_absolute() or
            any(p in ('', '.', '..') or p.endswith('.') or
                p.split('.')[0].casefold() in _RESERVED for p in parts)):
        raise ValueError('Unsafe archive entry')
    return clean


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate adapter metadata key')
        value[key] = item
    return value


def _constant(_value):
    raise ValueError('Nonfinite adapter metadata')


def _identity(value):
    # Windows path.stat/fstat expose different ctime meanings. Identity, size,
    # mtime and the second full content hash remain comparable across platforms.
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _bounded_directory(stream, size):
    """Bound classic single-disk ZIP headers before ZipFile allocates ZipInfos.

    Layout reference: PKWARE APPNOTE 6.3.10 sections 4.3.12 and 4.3.16.
    ZIP64, split archives and signed directories are outside this small profile.
    """
    tail_size = min(size, 65535 + 22)
    stream.seek(size - tail_size)
    tail = stream.read(tail_size)
    end = tail.rfind(b'PK\x05\x06')
    if end < 0 or len(tail) - end < 22:
        raise ValueError('Missing classic ZIP end record')
    absolute_end = size - tail_size + end
    if absolute_end >= 20:
        stream.seek(absolute_end - 20)
        if stream.read(4) == b'PK\x06\x07':
            raise ValueError('ZIP64 directory lookup is unsupported')
    _, disk, start_disk, disk_count, count, length, offset, comment = struct.unpack_from('<4s4H2LH', tail, end)
    if (disk or start_disk or disk_count != count or not 1 <= count <= MAX_MEMBERS or
            not 1 <= length <= MAX_DIRECTORY_BYTES or offset + length != absolute_end or
            end + 22 + comment != len(tail)):
        raise ValueError('Unsupported or oversized ZIP directory')
    stream.seek(offset)
    directory = stream.read(length)
    cursor, actual = 0, 0
    while cursor < length:
        if directory[cursor:cursor + 4] != b'PK\x01\x02' or length - cursor < 46:
            raise ValueError('Invalid ZIP directory header')
        name, extra, note, member_disk = struct.unpack_from('<4H', directory, cursor + 28)
        cursor += 46 + name + extra + note
        actual += 1
        if member_disk or actual > MAX_MEMBERS or cursor > length:
            raise ValueError('Unsupported ZIP member directory')
    if actual != count:
        raise ValueError('ZIP directory count differs from actual headers')
    stream.seek(0)


def _inspect(bundle, adapter_entry, expected_adapter_sha256):
    infos = bundle.infolist()
    if not 1 <= len(infos) <= MAX_MEMBERS:
        raise ValueError('Archive member count exceeds the supported bound')
    entries, names, total = {}, set(), 0
    for info in infos:
        # ZipInfo normalizes OS separators and truncates NULs in filename.
        # Check the original central-directory spelling before that normalization.
        name = _entry_name(info.orig_filename)
        key = name.casefold()
        mode = stat.S_IFMT(info.external_attr >> 16)
        if (key in names or info.flag_bits & 1 or
                info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or
                mode not in (0, stat.S_IFREG, stat.S_IFDIR)):
            raise ValueError('Duplicate, encrypted or special archive entry')
        names.add(key)
        total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ValueError('Declared uncompressed size exceeds the supported bound')
        if not info.is_dir():
            entries[name] = info
    config_entry = str(PurePosixPath(adapter_entry).parent / 'adapter_config.json')
    if adapter_entry not in entries or config_entry not in entries:
        raise ValueError('Exact adapter tensor and adjacent config entries are required')
    config_info = entries[config_entry]
    if config_info.file_size > MAX_METADATA_BYTES:
        raise ValueError('Adapter metadata exceeds the supported bound')
    config = json.loads(bundle.read(config_info).decode('utf8'),
                        object_pairs_hook=_object, parse_constant=_constant)
    if (not isinstance(config, dict) or config.get('peft_type') != 'LORA' or
            config.get('task_type') != 'CAUSAL_LM' or
            not isinstance(config.get('base_model_name_or_path'), str) or
            not config['base_model_name_or_path'].strip()):
        raise ValueError('Expected causal LoRA metadata with a declared base')
    info = entries[adapter_entry]
    if info.file_size < 1:
        raise ValueError('Adapter tensor entry is empty')
    with bundle.open(info) as stream:
        digest = _stream_sha256(stream)
    if digest != expected_adapter_sha256:
        raise ValueError('Adapter tensor checksum differs from the expected source')
    return {'entry': adapter_entry, 'bytes': info.file_size, 'sha256': digest,
            'declared_base': config['base_model_name_or_path']}, len(infos)


def verify_archive(archive_path, expected_sha256, adapter_entry, expected_adapter_sha256):
    """Read-only exact-byte verification; does not inspect any candidate workspace."""
    if any(not isinstance(v, str) or not re.fullmatch(r'[a-f0-9]{64}', v)
           for v in (expected_sha256, expected_adapter_sha256)):
        raise ValueError('Use separately obtained lowercase SHA-256 digests')
    if (_entry_name(adapter_entry) != adapter_entry or
            PurePosixPath(adapter_entry).name != 'adapter_model.safetensors'):
        raise ValueError('Select the exact adapter_model.safetensors entry')
    path = Path(archive_path).expanduser().resolve(strict=True)
    try:
        with path.open('rb') as stream:
            initial = os.fstat(stream.fileno())
            if not stat.S_ISREG(initial.st_mode) or not 1 <= initial.st_size <= MAX_ARCHIVE_BYTES:
                raise ValueError('Select a regular local archive within the 1 GiB limit')
            digest = _stream_sha256(stream)
            if digest != expected_sha256:
                raise ValueError('Archive checksum differs from the expected source')
            _bounded_directory(stream, initial.st_size)
            with zipfile.ZipFile(stream) as bundle:
                adapter, members = _inspect(bundle, adapter_entry, expected_adapter_sha256)
            stream.seek(0)
            if (_stream_sha256(stream) != digest or
                    _identity(os.fstat(stream.fileno())) != _identity(initial) or
                    _identity(path.stat()) != _identity(initial)):
                raise ValueError('Archive changed during verification')
    except (zipfile.BadZipFile, UnicodeError, RuntimeError, zlib.error, RecursionError) as error:
        raise ValueError('Unreadable or invalid adapter archive') from error
    return {'schema_version': '1.0', 'verified_utc': datetime.now(timezone.utc).isoformat(),
            'archive': {'path': str(path), 'bytes': initial.st_size, 'sha256': digest, 'members': members},
            'adapter': adapter, 'verification_scope': 'archive_and_selected_adapter_bytes_only',
            'training_status': 'not_assessed', 'quality_status': 'not_assessed',
            'archive_extracted': False, 'promotion_performed': False,
            'provider_calls': 0, 'ledger_opened': False}
