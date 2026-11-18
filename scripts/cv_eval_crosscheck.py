#!/usr/bin/env python3
"""Prepare blinded judge inputs or cross-check captured CV graders; no inference."""
import argparse
import json
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import review_cycle as r
from core import tailor_benchmark as b


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--references', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--graders', type=Path)
    p.add_argument('--writer-model-id', default='unknown')
    a = p.parse_args(argv)
    try:
        output = a.output.resolve(); clone = Path(__file__).resolve().parents[1]
        b.require(not output.is_relative_to(clone) and not output.exists(), 'Use a new private output outside the clone')
        references, source = r.read_examples(a.references)
        files = [source]
        if a.graders:
            with a.graders.open('rb') as stream:
                raw = stream.read(20_000_001)
            b.require(len(raw) <= 20_000_000, 'Grader input exceeds 20 MB')
            result = r.crosscheck(references, r.decode(raw.decode('utf8')), a.writer_model_id)
            files.append({'path': str(a.graders.resolve()), 'sha256': b.digest(raw)})
        else:
            result = r.judge_inputs(references)
        for source in files:
            with Path(source['path']).open('rb') as stream:
                b.require(hashlib.file_digest(stream, 'sha256').hexdigest() == source['sha256'], 'Inputs changed during evaluation')
        result['input_files'] = files
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as stream:
            stream.write(b.json_bytes(result))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({'outcome': 'blocked', 'reason': str(exc)})); return 1
    print(json.dumps({'outcome': 'ok', 'model_calls_performed': 0, 'output': str(output)})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
