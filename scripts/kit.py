#!/usr/bin/env python3
"""Local CLI entrypoint. Legacy ledger imports remain compatible."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.ledger import ACTIONS, ConcurrentWrite, Kit, PackageError

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="private candidate directory outside this repository")
    parser.add_argument("--actor", default="local-user", help="actor label stored in append-only events")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="report local safety capabilities; data directory is optional")
    commands.add_parser("init", help="initialize the private SQLite ledger")
    commands.add_parser("status", help="show job, approval, and event status")
    add = commands.add_parser("add-job", help="add a job from a private JSON object")
    add.add_argument("--job", type=Path, required=True)
    for name in ("check-package", "check-approval"):
        command = commands.add_parser(name, help=f"{name.replace('-', ' ')} against current artifact bytes")
        command.add_argument("--package", type=Path, required=True)
        command.add_argument("--action", choices=sorted(ACTIONS))
    record = commands.add_parser("record-approval", help="record explicit content-bound user approval; executes nothing")
    record.add_argument("--package", type=Path, required=True)
    record.add_argument("--confirmation", type=Path, required=True)
    record.add_argument("--reviewed", action="store_true", required=True)
    invalidate = commands.add_parser("invalidate", help="invalidate one approval record")
    invalidate.add_argument("--approval-id", type=int, required=True)
    invalidate.add_argument("--reason", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor" and args.data_dir is None:
        result: Any = {"data_dir": None, "data_dir_outside_repo": None, "network_execution": False,
                       "browser_execution": False, "global_guard_provided": False,
                       "approval_binding": "sha256_not_signature"}
    else:
        if args.data_dir is None:
            raise SystemExit("--data-dir is required for stateful commands")
        kit = Kit(args.data_dir, actor=args.actor)
        if args.command == "init":
            kit.init(); result = {"initialized": str(kit.data_dir)}
        elif args.command == "doctor": result = kit.doctor()
        elif args.command == "status": result = kit.status()
        elif args.command == "add-job": result = kit.add_job(**kit.load_private_json(args.job))
        elif args.command == "check-package": result = kit.check_package(kit.load_private_json(args.package), args.action)
        elif args.command == "check-approval": result = {"approved": kit.check_approval(kit.load_private_json(args.package), args.action)}
        elif args.command == "record-approval":
            result = kit.record_approval(kit.load_private_json(args.package), args.confirmation, reviewed=args.reviewed)
        else: result = {"invalidated": kit.invalidate(args.approval_id, args.reason)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
