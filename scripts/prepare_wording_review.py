#!/usr/bin/env python3
"""Create private blinded draft/evidence packets and a separate operator key."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.documents import Documents
from core.wording_review import prepare_review


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--runs', required=True)
    parser.add_argument('--output', required=True, help='New evaluations/ directory; never overwritten')
    args = parser.parse_args(argv)
    work = Documents(args.data_dir)
    target, parent = work.inside(args.output), work.inside('evaluations')
    if target.exists() or target == parent or not target.is_relative_to(parent):
        raise ValueError('Select a new private evaluations/ subdirectory')
    packet, key = prepare_review(work, args.dataset, work.private_json(work.inside(args.runs)))
    target.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, value in [('reviewer-packet.json', packet), ('operator-key.json', key)]:
        with (target/name).open('x', encoding='utf8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        hashes[name] = hashlib.sha256((target/name).read_bytes()).hexdigest()
    with (target/'completed.json').open('x', encoding='utf8') as stream:
        json.dump({'files': hashes, 'cases': len(packet['cases']),
            'scores_created': False, 'provider_calls': 0, 'promotion_performed': False}, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'directory': str(target), 'cases': len(packet['cases']),
        'scores_created': False, 'promotion_performed': False}))


if __name__ == '__main__':
    main()
