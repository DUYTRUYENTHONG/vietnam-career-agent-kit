#!/usr/bin/env python3
"""Prepare a private source-bound requirement corpus; no fetching or training."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.requirement_corpus import MAX_BYTES, apply_extractions, build_corpus, collect_legacy, write_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--snapshots', type=Path, help='explicit requirements-corpus-v1 JSONL')
    source.add_argument('--legacy-ledger', type=Path, help='existing jobs SQLite; read-only projection')
    parser.add_argument('--output', type=Path, required=True, help='new private directory outside clone')
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--extractions', type=Path, help='optional hash-bound host extraction sidecar; pending review')
    args = parser.parse_args()
    try:
        if not 1 <= args.limit <= 1000:
            raise ValueError('Record limit must be 1..1000')
        if args.legacy_ledger:
            records = collect_legacy(args.legacy_ledger, limit=args.limit)
        else:
            with args.snapshots.open('rb') as stream:
                raw = stream.read(MAX_BYTES+1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Snapshot JSONL exceeds 20 MB')
            records = [json.loads(line) for line in raw.decode('utf8').splitlines() if line.strip()]
            if len(records) > args.limit:
                raise ValueError('Snapshot count exceeds selected limit')
        if args.extractions:
            with args.extractions.open('rb') as stream:
                raw = stream.read(MAX_BYTES+1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Extraction sidecar exceeds 20 MB')
            records = apply_extractions(records, json.loads(raw.decode('utf8')))
        result = write_corpus(build_corpus(records), args.output)
        print(json.dumps({'status': 'ok', 'output': str(args.output.resolve()), **result}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, sqlite3.Error) as error:
        print(json.dumps({'status': 'needs_input', 'error': str(error), 'training_performed': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
