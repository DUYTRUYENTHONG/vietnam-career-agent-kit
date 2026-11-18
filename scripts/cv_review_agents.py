#!/usr/bin/env python3
"""Prepare first-layer reviewer requests and collect captured AI proposals."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import cv_review_agents as agents, tailor_benchmark as b


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', type=Path, required=True)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('prepare'); q.add_argument('--preparation', required=True); q.add_argument('--draft')
    q = sub.add_parser('collect'); q.add_argument('--requests', required=True); q.add_argument('--responses', required=True)
    for q in sub.choices.values():
        q.add_argument('--output', required=True)
    a = p.parse_args(argv)
    try:
        if a.command == 'prepare':
            draft = b.read_json(b.inside(a.root, a.draft)) if a.draft else None
            agents.prepare(a.root, a.preparation, a.output, draft)
        else:
            agents.collect(a.root, a.requests, b.read_rows(b.inside(a.root, a.responses)), a.output)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'outcome': 'blocked', 'reason': str(exc)})); return 1
    print(json.dumps({'outcome': 'ok', 'model_calls_performed': 0, 'application_authority': False})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
