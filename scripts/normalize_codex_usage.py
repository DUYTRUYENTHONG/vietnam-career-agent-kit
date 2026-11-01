#!/usr/bin/env python3
"""Offline preparation of sanitized observations from a selected CLI export."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.codex_usage import normalize_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='Explicit fresh-thread codex exec --json export')
    parser.add_argument('--output-dir', required=True, help='New private directory; never overwritten')
    for name in ('task-id', 'workload-id', 'phase', 'observed-utc'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--model-id', default=None, help='Caller-reported exact ID; otherwise unknown')
    parser.add_argument('--effort', default=None, help='Caller-reported; requires model ID')
    args = parser.parse_args()
    try:
        data = normalize_export(args.input, args.output_dir, task_id=args.task_id,
            workload_id=args.workload_id, phase=args.phase, observed_utc=args.observed_utc,
            model_id=args.model_id, effort=args.effort)
    except (OSError, ValueError) as error:
        print(json.dumps({'outcome': 'blocked', 'data': None,
            'message': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({'outcome': 'ok', 'data': data}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
