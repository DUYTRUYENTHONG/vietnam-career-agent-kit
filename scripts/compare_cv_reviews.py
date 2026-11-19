#!/usr/bin/env python3
"""Compare archived CV reviews or evaluate grader outputs; no inference/training."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.contracts import ContractError
from core.review_cycle import compare, decode, evaluate, read_examples


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    paired = commands.add_parser('compare')
    paired.add_argument('--before', type=Path, required=True)
    paired.add_argument('--after', type=Path, required=True)
    paired.add_argument('--job-id', type=int, required=True)
    graded = commands.add_parser('evaluate')
    graded.add_argument('--references', type=Path, required=True)
    graded.add_argument('--predictions', type=Path, required=True)
    for command in (paired, graded):
        command.add_argument('--output', type=Path, required=True, help='New private JSON outside the public clone')
    args = parser.parse_args(argv)
    try:
        target = args.output.resolve()
        if target.is_relative_to(ROOT) or target.exists():
            raise ContractError('Select a new output outside the public clone; never overwrite')
        sources = []
        if args.mode == 'compare':
            values = []
            for path in (args.before, args.after):
                rows, binding = read_examples(path); sources.append(binding)
                selected = [row for row in rows if row['provenance']['job_id'] == args.job_id]
                if len(selected) != 1:
                    raise ContractError('Each capture must contain exactly one review for the selected job')
                values.append(selected[0])
            report = compare(*values)
        else:
            references, binding = read_examples(args.references); sources.append(binding)
            with args.predictions.open('rb') as stream:
                raw = stream.read(20_000_001)
            if len(raw) > 20_000_000:
                raise ContractError('Prediction file exceeds 20 MB')
            sources.append({'path': str(args.predictions.resolve()), 'sha256': hashlib.sha256(raw).hexdigest()})
            report = evaluate(references, decode(raw))
        for source in sources:
            with Path(source['path']).open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != source['sha256']:
                raise ContractError('Input changed during comparison')
        report['input_files'] = sources
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'status': 'ok', 'report': str(target), 'training_performed': False}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print(json.dumps({'status': 'needs_input', 'message': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
