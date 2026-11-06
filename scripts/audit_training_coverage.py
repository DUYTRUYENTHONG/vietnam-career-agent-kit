#!/usr/bin/env python3
"""Print a private read-only coverage report for external candidate_fact JSONL pilots."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.training_coverage import audit_coverage

MAX_BYTES = 20_000_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected', type=Path, required=True, help='JSON array of explicit id/text facts')
    parser.add_argument('--train', type=Path, required=True, help='candidate_fact chat JSONL')
    parser.add_argument('--evaluation', type=Path, help='optional candidate_fact chat JSONL')
    parser.add_argument('--aliases', type=Path, help='optional explicit external-to-expected ID object')
    args = parser.parse_args()
    hashes = {}
    total = 0

    def read(path, label, jsonl=False):
        nonlocal total
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        total += len(raw)
        if total > MAX_BYTES:
            raise ValueError('Combined inputs exceed 20 MB')
        hashes[label] = hashlib.sha256(raw).hexdigest()
        text = raw.decode('utf8')
        # JSONL records end at LF; U+2028/U+2029 are valid inside JSON strings.
        return [json.loads(line) for line in text.split('\n') if line.strip()] if jsonl else json.loads(text)

    try:
        expected = read(args.expected, 'expected')
        train = read(args.train, 'training', True)
        evaluation = read(args.evaluation, 'evaluation', True) if args.evaluation else None
        aliases = read(args.aliases, 'aliases') if args.aliases else None
        report = audit_coverage(expected, train, evaluation, aliases)
        report['input_file_sha256'] = hashes
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, RecursionError):
        # JSON and OS exception messages can expose private source lines or paths.
        print(json.dumps({'status': 'needs_input', 'error': 'Invalid, unreadable or oversized coverage inputs',
                          'training_performed': False, 'provider_calls': 0}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
