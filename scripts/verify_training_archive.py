#!/usr/bin/env python3
"""Verify a downloaded LoRA ZIP and write a new private byte-verification receipt."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.model_archive import verify_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--sha256', required=True, help='Expected archive hash from the separate source receipt')
    parser.add_argument('--adapter-entry', required=True, help='Exact nested ZIP member; no extraction')
    parser.add_argument('--adapter-sha256', required=True, help='Expected adapter tensor hash from the source')
    parser.add_argument('--output', required=True, help='New JSON receipt outside the source checkout')
    args = parser.parse_args()
    try:
        output = Path(args.output).expanduser().resolve()
        if output.is_relative_to(ROOT) or output.suffix != '.json' or output.exists():
            raise ValueError('Choose a new .json receipt outside the source checkout')
        result = verify_archive(args.archive, args.sha256, args.adapter_entry, args.adapter_sha256)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    except (OSError, ValueError) as error:
        print(json.dumps({'outcome': 'blocked', 'message': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({'outcome': 'ok', 'receipt': str(output),
                      'verification_scope': result['verification_scope'], 'promotion_performed': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
