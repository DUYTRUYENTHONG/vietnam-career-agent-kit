#!/usr/bin/env python3
"""Prepare, freeze and compare private source-bound tailoring experiments."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import tailor_benchmark as bench


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True, help='Explicit external private directory')
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--cases', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('freeze'); a.add_argument('--preparation', required=True)
    a.add_argument('--review-a', required=True); a.add_argument('--review-b', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('blind'); a.add_argument('--frozen', required=True)
    a.add_argument('--records', required=True); a.add_argument('--output', required=True)
    a.add_argument('--comparison', choices=['prompt', 'training', 'retrieval'], default='training')
    a = sub.add_parser('variant'); a.add_argument('--frozen', required=True)
    a.add_argument('--prompt', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('compare'); a.add_argument('--frozen', required=True)
    a.add_argument('--blinded', required=True); a.add_argument('--reviews', required=True); a.add_argument('--output', required=True)
    args = p.parse_args(argv)
    read = lambda name: bench.read_rows(bench.inside(args.root, name))
    try:
        if args.command == 'prepare':
            result = bench.prepare(args.root, read(args.cases), args.output)
        elif args.command == 'freeze':
            result = bench.freeze(args.root, args.preparation, read(args.review_a), read(args.review_b), args.output)
        elif args.command == 'blind':
            result = bench.blind(args.root, args.frozen, read(args.records), args.output, args.comparison)
        elif args.command == 'variant':
            result = bench.prompt_variant(args.root, args.frozen,
                bench.inside(args.root, args.prompt).read_text(encoding='utf8'), args.output)
        else:
            result = bench.compare(args.root, args.frozen, args.blinded, read(args.reviews))
            output = bench.inside(args.root, args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('xb') as stream:
                stream.write(bench.json_bytes(result))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'outcome': 'blocked', 'reason': str(exc), 'model_promoted': False}))
        return 1
    print(json.dumps({'outcome': 'ok', 'kind': result['kind'], 'output': args.output,
                      'model_promoted': False, 'application_authority': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
