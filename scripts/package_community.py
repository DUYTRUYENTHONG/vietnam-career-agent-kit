#!/usr/bin/env python3
"""Build a checked source ZIP and digest manifest from the exact committed tree."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_repository import issues_for


def build(repo: Path, output: Path) -> dict:
    repo, output = repo.resolve(), output.expanduser().resolve()
    if output.is_relative_to(repo) or output.suffix != '.zip':
        raise ValueError('Choose a .zip output outside the checkout')
    manifest_path = output.with_suffix('.manifest.json')
    if output.exists() or manifest_path.exists():
        raise FileExistsError('Choose new artifact names; existing release files are never overwritten')
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, check=True,
                            capture_output=True, text=True).stdout.strip()
    raw = subprocess.run(['git', 'archive', '--format=zip', '--prefix=vietnam-career-agent-kit/', commit],
                         cwd=repo, check=True, capture_output=True).stdout
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or (info.external_attr >> 16 & 0o170000) == 0o120000:
                raise ValueError('Unsafe archive path or symlink: '+info.filename)
            content = archive.read(info)
            problems = issues_for(Path(*path.parts[1:]), content.decode('utf8'))
            if problems:
                raise ValueError(info.filename+': '+', '.join(problems))
            files[info.filename] = hashlib.sha256(content).hexdigest()
    result = {'format_version': '1.0', 'commit': commit, 'archive_sha256': hashlib.sha256(raw).hexdigest(),
              'file_count': len(files), 'files': files,
              'scope': 'Committed UTF-8 public source only; no untracked files, Git metadata, credentials or candidate workspaces. Bounded hygiene, not a full secret scanner.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(raw)
    with manifest_path.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(ROOT, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))


if __name__ == '__main__':
    main()
