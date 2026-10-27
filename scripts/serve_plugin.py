#!/usr/bin/env python3
"""Run one explicitly configured optional local MCP plugin over stdio."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['email', 'browser', 'career'])
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--actor', default='local-user')
    parser.add_argument('--client-file', default='credentials/google-desktop-client.json',
                        help='relative path in the private workspace, email only')
    parser.add_argument('--connection', default='default')
    args = parser.parse_args()
    from core.parallel_execution import ParallelExecutor
    from adapters.plugin_server import make_server
    work = ParallelExecutor(args.data_dir, actor=args.actor)
    if not work.db_path.is_file():
        parser.error('Initialize this private workspace with scripts/kit.py first')
    # Never silently initialize or import a candidate when launching a plugin.
    client = None
    if args.kind == 'email':
        from adapters.gmail_client import GmailClient
        client = GmailClient(work, args.client_file, args.connection)
    make_server(work, args.kind, client=client).run(transport='stdio')


if __name__ == '__main__':
    main()
