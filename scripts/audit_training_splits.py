#!/usr/bin/env python3
"""Print a private connectivity report for explicit external split groups."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.training_split_audit import audit_splits

MAX_BYTES = 20_000_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--groups', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.groups.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Input too large')
        report = audit_splits(json.loads(raw.decode('utf8')))
        report['input_file_sha256'] = hashlib.sha256(raw).hexdigest()
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, RecursionError):
        print(json.dumps({'status': 'needs_input',
                          'error': 'Invalid, unreadable or oversized split-group input',
                          'training_performed': False, 'provider_calls': 0}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
