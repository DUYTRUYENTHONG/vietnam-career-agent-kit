#!/usr/bin/env python3
"""Prepare first-layer reviewer requests and collect captured AI proposals."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import cv_review_agents as agents, tailor_benchmark as b
from core import reviewer_automation as host


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', type=Path, required=True)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('prepare'); q.add_argument('--preparation', required=True); q.add_argument('--draft')
    q = sub.add_parser('collect'); q.add_argument('--requests', required=True); q.add_argument('--responses', required=True)
    for name in ('prepare', 'collect'):
        sub.choices[name].add_argument('--output', required=True)
    q = sub.add_parser('start'); q.add_argument('--requests', required=True); q.add_argument('--cycle', required=True); q.add_argument('--reuse-advisory')
    q = sub.add_parser('advance'); q.add_argument('--cycle', required=True); q.add_argument('--response')
    a = p.parse_args(argv)
    try:
        if a.command == 'prepare':
            draft = b.read_json(b.inside(a.root, a.draft)) if a.draft else None
            agents.prepare(a.root, a.preparation, a.output, draft)
        elif a.command == 'collect':
            agents.collect(a.root, a.requests, b.read_rows(b.inside(a.root, a.responses)), a.output)
        elif a.command == 'start':
            host.start(a.root, a.requests, a.cycle, a.reuse_advisory)
        else:
            response = b.read_json(b.inside(a.root, a.response)) if a.response else None
            result = host.advance(a.root, a.cycle, response)
            print(json.dumps(result, ensure_ascii=False)); return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'outcome': 'blocked', 'reason': str(exc)})); return 1
    print(json.dumps({'outcome': 'ok', 'model_calls_performed': 0, 'application_authority': False})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
