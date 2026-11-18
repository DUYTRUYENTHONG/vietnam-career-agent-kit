#!/usr/bin/env python3
"""Private evidence retrieval, reviewed requirement matching and CV planning."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import cv_planning as c
from core import tailor_benchmark as b


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--cases', required=True); p.add_argument('--top-k', type=int, default=5)
    p = sub.add_parser('build'); p.add_argument('--preparation', required=True); p.add_argument('--reviews', required=True); p.add_argument('--max-bullets', type=int, default=12)
    for name in ('retrieval-eval', 'retrieval-variant'):
        p = sub.add_parser(name); p.add_argument('--frozen', required=True); p.add_argument('--top-k', type=int, default=5)
    for p in sub.choices.values():
        p.add_argument('--output', required=True)
    for name, p in sub.choices.items():
        if name != 'build':
            p.add_argument('--method', choices=c.METHODS, default='bm25-v2')
    a = parser.parse_args(argv)
    try:
        if a.command == 'prepare':
            c.prepare(a.root, b.read_rows(b.inside(a.root, a.cases)), a.output, a.top_k, a.method)
        elif a.command == 'build':
            c.plan(a.root, a.preparation, b.read_rows(b.inside(a.root, a.reviews)), a.output, a.max_bullets)
        elif a.command == 'retrieval-variant':
            c.retrieval_variant(a.root, a.frozen, a.output, a.top_k, a.method)
        else:
            result = c.retrieval_report(a.root, a.frozen, a.top_k, a.method)
            path = b.inside(a.root, a.output); path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(b.json_bytes(result))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'outcome': 'blocked', 'reason': str(exc)})); return 1
    print(json.dumps({'outcome': 'ok', 'output': a.output, 'application_authority': False})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
