#!/usr/bin/env python3
"""Disposable fictional LCEL smoke: quote-copy callback, not AI generation."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.langchain_career import run_drafting
from core.execution import Executor
from scripts.demo_slice1 import demo


def quote_copy(brief):
    fact = brief['context']['facts'][0]
    return {'schema_version': '1.0', 'brief_fingerprint': brief['brief_fingerprint'],
            'blocks': [{'kind': 'cv_bullet', 'text': fact['quote'], 'fact_ids': [fact['id']]}]}


def main():
    with tempfile.TemporaryDirectory(prefix='career-kit-fictional-rag-') as temporary:
        workspace = Path(temporary)/'private'
        demo(workspace)
        result = run_drafting(Executor(workspace),
            {'job_id': 1, 'kind': 'cv', 'language': 'en', 'limit': 5}, quote_copy)
        print(json.dumps({'fixture': 'fictional quote-copy callback; no model/API',
                          'result': result.json()}, indent=2))
        return 0 if result.outcome == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
