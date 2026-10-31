#!/usr/bin/env python3
"""Compare recorded base/adapter CV outputs locally; never generate or promote."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.documents import Documents
from core.wording_evaluation import compare


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--runs', required=True, help='Recorded paired runs JSON inside selected private workspace')
    parser.add_argument('--output', required=True, help='New evaluations/ report JSON inside that workspace')
    args = parser.parse_args(argv)
    work = Documents(args.data_dir)
    target = work.inside(args.output)
    if target.exists() or not target.is_relative_to(work.inside('evaluations')) or target == work.inside('evaluations'):
        raise ValueError('Select a new evaluations/ report; existing artifacts are never overwritten')
    runs = work.private_json(work.inside(args.runs))
    report = compare(work, args.dataset, runs)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'report': str(target), 'heldout_examples': report['heldout_examples'],
                      'promotion_performed': False, 'sent': False}))


if __name__ == '__main__':
    main()
