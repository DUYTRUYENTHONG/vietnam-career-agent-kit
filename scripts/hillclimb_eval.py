#!/usr/bin/env python3
"""Record bounded private development rounds and one final test; no model calls."""
import argparse
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import tailor_benchmark as b
from core import eval_hillclimb as h


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--study', required=True, help='Private study directory')
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('init'); q.add_argument('--plan', required=True)
    q = sub.add_parser('record'); q.add_argument('--proposal', required=True); q.add_argument('--report', required=True)
    q = sub.add_parser('final'); q.add_argument('--report', required=True)
    a = p.parse_args(argv)
    study = b.inside(a.root, a.study)
    read = lambda name: b.read_json(b.inside(a.root, name))
    try:
        if a.command == 'init':
            plan = h.validate_plan(read(a.plan))
            b.require(not study.exists(), 'Use a new study; never reset spent time')
            study.mkdir(parents=True)
            with (study/'plan.json').open('xb') as stream:
                stream.write(b.json_bytes(plan))
            result = {'initialized': True}
        else:
            plan = h.validate_plan(b.read_json(study/'plan.json'))
            b.require(not (study/'final_test.json').exists(), 'Final test already consumed; study is closed')
            # Exclusive single-writer lock: never discard another process's lock.
            lock = study/'write.lock'
            with lock.open('x', encoding='utf8'):
                pass
            try:
                history = [b.read_json(x) for x in sorted(study.glob('round-*.json'))]
                if a.command == 'record':
                    result = h.record_round(plan, history, read(a.proposal), read(a.report))
                    destination = study/f"round-{result['round']:03}.json"
                else:
                    result = h.final_test(plan, history, read(a.report))
                    destination = study/'final_test.json'
                with destination.open('xb') as stream:
                    stream.write(b.json_bytes(result))
            finally:
                lock.unlink()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'outcome': 'blocked', 'reason': str(exc)})); return 1
    print(json.dumps({'outcome': 'ok', 'result': result, 'model_promoted': False})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
