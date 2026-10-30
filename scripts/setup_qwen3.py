"""Explicit public Qwen3-0.6B download; never processes candidate evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path

MODEL = 'Qwen/Qwen3-0.6B'
ROOT = Path(__file__).resolve().parents[1]


def download(destination):
    target = Path(destination).resolve()
    if target == ROOT or target.is_relative_to(ROOT) or target.exists():
        raise ValueError('Choose a new model directory outside the source checkout')
    from huggingface_hub import HfApi, snapshot_download
    revision = HfApi().model_info(MODEL).sha
    if not isinstance(revision, str) or not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('Hub did not return a pinned model revision')
    target.mkdir(parents=True, exist_ok=False)
    snapshot_download(MODEL, revision=revision, local_dir=str(target),
        allow_patterns=['*.json', '*.safetensors', '*.txt', '*.jinja', 'LICENSE', 'README.md'],
        max_workers=2)
    if not (target/'config.json').is_file() or not (target/'tokenizer_config.json').is_file() or not list(target.glob('*.safetensors')):
        raise ValueError('Model download is incomplete; no completion manifest written')
    hashes = {}
    for path in sorted(target.iterdir()):
        if path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    digest.update(chunk)
            hashes[path.name] = digest.hexdigest()
    (target/'download-manifest.json').write_text(json.dumps({'model': MODEL,
        'revision': revision, 'files': hashes, 'candidate_data_processed': False}, indent=2), encoding='utf8')
    print(json.dumps({'model': MODEL, 'revision': revision, 'files': len(hashes)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-directory', required=True)
    parser.add_argument('--download', action='store_true', help='Explicitly download public weights/tokenizer')
    args = parser.parse_args()
    if args.download:
        download(args.model_directory)
    else:
        print(json.dumps({'model': MODEL, 'download_performed': False,
                          'next_step': 'Review model card/license, then rerun with --download'}))


if __name__ == '__main__':
    main()
