#!/usr/bin/env python3
"""Local workflow ledger and content-bound approval checker; performs no web actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlsplit

STATES = ("discovered", "assessed", "draft_ready", "review_required",
          "approved_for_disclosure", "form_prepared", "awaiting_manual_submission",
          "confirmed_submitted", "user_reported_submitted", "submission_uncertain")
ACTIONS = {"fill", "upload", "submit"}


class PackageError(ValueError):
    """Package content or policy is unsafe or incomplete."""


class ConcurrentWrite(RuntimeError):
    """An optimistic update used a stale version."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def display_vietnam(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone(timedelta(hours=7))).isoformat(timespec="seconds")


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _key(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(c for c in folded if not unicodedata.combining(c)).split())


def _https(value: Any, label: str) -> Any:
    if not isinstance(value, str):
        raise PackageError(f"{label} must be an HTTPS URL")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise PackageError(f"{label} has an invalid port") from error
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.fragment or port is not None and not 1 <= port <= 65535):
        raise PackageError(f"{label} must be an exact HTTPS URL without userinfo or fragment")
    return parsed


class Kit:
    """Private SQLite workflow rooted outside the public repository."""

    def __init__(self, data_dir: str | Path, repo_root: str | Path | None = None,
                 actor: str = "local-user"):
        self.repo_root = Path(repo_root or Path(__file__).parents[1]).resolve()
        self.data_dir = Path(data_dir).expanduser().resolve(strict=False)
        if (self.data_dir == self.repo_root or self.data_dir.is_relative_to(self.repo_root) or
                self.repo_root.is_relative_to(self.data_dir)):
            raise ValueError("candidate data directory must be separate from the repository")
        if not actor.strip():
            raise ValueError("actor is required")
        self.actor = actor
        self.db_path = self.data_dir / "workflow.sqlite3"

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    def init(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "raw-jd").mkdir(exist_ok=True)
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            state_check = ",".join(repr(state) for state in STATES)
            db.executescript(f"""
            CREATE TABLE IF NOT EXISTS jobs(
              id INTEGER PRIMARY KEY, platform TEXT NOT NULL, platform_job_id TEXT NOT NULL,
              employer TEXT NOT NULL, employer_key TEXT NOT NULL, req_id TEXT NOT NULL,
              title TEXT NOT NULL, url TEXT NOT NULL, city TEXT NOT NULL, raw_jd_path TEXT NOT NULL,
              readable INTEGER NOT NULL, liveness TEXT NOT NULL CHECK(liveness IN ('active','closed','unverified')),
              state TEXT NOT NULL CHECK(state IN ({state_check})), version INTEGER NOT NULL DEFAULT 1,
              updated_utc TEXT NOT NULL, UNIQUE(platform,platform_job_id));
            CREATE UNIQUE INDEX IF NOT EXISTS jobs_employer_req ON jobs(employer_key,req_id) WHERE req_id<>'';
            CREATE TABLE IF NOT EXISTS approvals(
              id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL, destination TEXT NOT NULL,
              source TEXT NOT NULL, recorded_utc TEXT NOT NULL, invalidated_utc TEXT, reason TEXT);
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY, kind TEXT NOT NULL, object_id TEXT NOT NULL, actor TEXT NOT NULL,
              occurred_utc TEXT NOT NULL, detail TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
              BEGIN SELECT RAISE(ABORT,'events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
              BEGIN SELECT RAISE(ABORT,'events are append-only'); END;
            """)

    def _event(self, db: sqlite3.Connection, kind: str, object_id: Any, detail: str) -> str:
        stamp = utc_now()
        db.execute("INSERT INTO events(kind,object_id,actor,occurred_utc,detail) VALUES(?,?,?,?,?)",
                   (kind, str(object_id), self.actor, stamp, detail))
        return stamp

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def get_job(self, job_id: int) -> dict[str, Any]:
        with self._db() as db:
            row = self._row(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
        if row is None:
            raise KeyError(job_id)
        return row

    def add_job(self, *, platform: str, platform_job_id: str, employer: str, req_id: str,
                title: str, url: str, city: str, raw_jd: str, readable: bool = True,
                liveness: str = "active") -> dict[str, Any]:
        if not all(value.strip() for value in (platform, platform_job_id, employer, title, url)):
            raise ValueError("platform, platform_job_id, employer, title, and url are required")
        _https(url, "job URL")
        actual_liveness = liveness if readable else "unverified"
        if actual_liveness not in {"active", "closed", "unverified"}:
            raise ValueError("invalid liveness")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT id,raw_jd_path FROM jobs WHERE platform=? AND platform_job_id=?",
                             (platform, platform_job_id)).fetchone()
            if row is None and req_id.strip():
                row = db.execute("SELECT id,raw_jd_path FROM jobs WHERE employer_key=? AND req_id=?",
                                 (_key(employer), req_id.strip())).fetchone()
            stamp = utc_now()
            if row is None:
                cur = db.execute("""INSERT INTO jobs(platform,platform_job_id,employer,employer_key,req_id,
                    title,url,city,raw_jd_path,readable,liveness,state,updated_utc)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (platform, platform_job_id, employer, _key(employer), req_id.strip(), title, url,
                     city, "pending", int(readable), actual_liveness, "discovered", stamp))
                job_id = int(cur.lastrowid)
                relative = f"raw-jd/{job_id}.txt"
            else:
                job_id, relative = int(row["id"]), row["raw_jd_path"]
                db.execute("""UPDATE jobs SET employer=?,employer_key=?,req_id=?,title=?,url=?,city=?,
                           readable=?,liveness=?,version=version+1,updated_utc=? WHERE id=?""",
                           (employer, _key(employer), req_id.strip(), title, url, city, int(readable),
                            actual_liveness, stamp, job_id))
            (self.data_dir / relative).write_text(raw_jd, encoding="utf-8")
            db.execute("UPDATE jobs SET raw_jd_path=? WHERE id=?", (relative, job_id))
            self._event(db, "job_upserted", job_id, platform)
            db.commit()
        return self.get_job(job_id)

    def set_liveness(self, job_id: int, liveness: str, expected_version: int) -> dict[str, Any]:
        if liveness not in {"active", "closed", "unverified"}:
            raise ValueError("invalid liveness")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            stamp = utc_now()
            cur = db.execute("UPDATE jobs SET liveness=?,version=version+1,updated_utc=? WHERE id=? AND version=?",
                             (liveness, stamp, job_id, expected_version))
            if cur.rowcount != 1:
                db.rollback()
                raise ConcurrentWrite(f"stale version: {expected_version}")
            self._event(db, "liveness_changed", job_id, liveness)
            db.commit()
        return self.get_job(job_id)

    @staticmethod
    def hash_file(path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as source:
            for block in iter(lambda: source.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()

    def _artifact_path(self, raw: Any) -> Path:
        if not isinstance(raw, str) or not raw:
            raise PackageError("artifact path is required")
        path = (self.data_dir / raw).resolve(strict=True)
        if not path.is_relative_to(self.data_dir) or not path.is_file():
            raise PackageError("artifacts must be files inside the private data directory")
        return path

    def check_package(self, package: Mapping[str, Any], action: str | None = None) -> dict[str, Any]:
        required = {"company", "job_id", "destination", "artifacts", "answers", "consents",
                    "policy", "required_fields"}
        missing = required - package.keys()
        if missing:
            raise PackageError(f"missing package fields: {', '.join(sorted(missing))}")
        identities = (package["company"], package["job_id"])
        if any(not isinstance(value, str) or not value.strip() for value in identities):
            raise PackageError("company and job_id must be nonempty strings")
        destination = _https(package["destination"], "destination")
        policy = package["policy"]
        if not isinstance(policy, Mapping) or policy.get("mode") not in {"assisted_allowed", "manual"}:
            raise PackageError("policy mode is unknown")
        source = _https(policy.get("source"), "policy source")
        if destination.hostname.casefold() != source.hostname.casefold():
            raise PackageError("policy source host must exactly match destination host")
        try:
            checked = datetime.fromisoformat(str(policy["checked_utc"]).replace("Z", "+00:00"))
        except (KeyError, ValueError) as error:
            raise PackageError("policy checked_utc must be timezone-aware ISO-8601") from error
        if checked.tzinfo is None or checked.utcoffset() != timedelta(0):
            raise PackageError("policy checked_utc must be UTC")
        allowed = policy.get("allowed_actions")
        if not isinstance(allowed, list) or any(item not in ACTIONS for item in allowed):
            raise PackageError("policy allowed_actions are invalid")
        if action is not None and (action not in ACTIONS or policy["mode"] != "assisted_allowed" or action not in allowed):
            raise PackageError(f"policy does not allow assisted {action}")
        answers, fields = package["answers"], package["required_fields"]
        if (not isinstance(answers, Mapping) or not isinstance(fields, list) or
                not isinstance(package["consents"], list)):
            raise PackageError("answers, consents, or required_fields have invalid types")
        unknown = [name for name in fields if answers.get(name) is None or str(answers.get(name)).strip() == ""]
        if unknown:
            raise PackageError(f"required answers unresolved: {', '.join(map(str, unknown))}")
        artifacts = package["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise PackageError("at least one artifact is required")
        for artifact in artifacts:
            if not isinstance(artifact, Mapping) or not isinstance(artifact.get("sha256"), str):
                raise PackageError("artifact path and sha256 are required")
            path = self._artifact_path(artifact.get("path"))
            if len(artifact["sha256"]) != 64 or self.hash_file(path) != artifact["sha256"].casefold():
                raise PackageError(f"artifact bytes changed: {artifact.get('path')}")
        return {"fingerprint": canonical_hash(package), "destination": package["destination"],
                "action": action, "ready": True}

    def package_fingerprint(self, package: Mapping[str, Any]) -> str:
        return self.check_package(package)["fingerprint"]

    def record_approval(self, package: Mapping[str, Any], confirmation_file: str | Path,
                        *, reviewed: bool) -> dict[str, Any]:
        checked = self.check_package(package)
        if not reviewed:
            raise PackageError("reviewed content confirmation is required")
        confirmation = Path(confirmation_file).resolve(strict=True)
        if not confirmation.is_relative_to(self.data_dir):
            raise PackageError("confirmation must be in the private data directory")
        if confirmation.read_text(encoding="utf-8").strip() != f"APPROVE {checked['fingerprint']}":
            raise PackageError("confirmation text does not match the reviewed package fingerprint")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            stamp = utc_now()
            cur = db.execute("""INSERT INTO approvals(fingerprint,destination,source,recorded_utc)
                              VALUES(?,?,?,?)""",
                             (checked["fingerprint"], checked["destination"], "user_explicit", stamp))
            approval_id = int(cur.lastrowid)
            self._event(db, "approval_recorded", approval_id, "unverifiable_human_provenance")
            db.commit()
        return {"id": approval_id, "fingerprint": checked["fingerprint"],
                "source": "user_explicit", "provenance": "unverifiable_human_provenance"}

    def _marker_allows(self, recorded_utc: str) -> bool:
        marker = self.data_dir / "approvals-invalidated.json"
        if not marker.exists():
            return True
        try:
            value = json.loads(marker.read_text(encoding="utf-8"))
            invalidated = datetime.fromisoformat(value["invalidated_utc"].replace("Z", "+00:00"))
            recorded = datetime.fromisoformat(recorded_utc.replace("Z", "+00:00"))
            return bool(value.get("reason")) and invalidated.tzinfo is not None and invalidated < recorded
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return False

    def check_approval(self, package: Mapping[str, Any], action: str | None = None) -> bool:
        try:
            checked = self.check_package(package, action)
        except (PackageError, OSError):
            return False
        with self._db() as db:
            rows = db.execute("""SELECT recorded_utc FROM approvals WHERE fingerprint=? AND destination=?
                               AND invalidated_utc IS NULL ORDER BY id DESC""",
                              (checked["fingerprint"], checked["destination"])).fetchall()
        return any(self._marker_allows(row["recorded_utc"]) for row in rows)

    def invalidate(self, approval_id: int, reason: str) -> bool:
        if not reason.strip():
            raise ValueError("invalidation reason is required")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            stamp = utc_now()
            cur = db.execute("UPDATE approvals SET invalidated_utc=?,reason=? WHERE id=? AND invalidated_utc IS NULL",
                             (stamp, reason, approval_id))
            if cur.rowcount:
                self._event(db, "approval_invalidated", approval_id, reason)
            db.commit()
        return cur.rowcount == 1

    def status(self) -> dict[str, Any]:
        with self._db() as db:
            jobs = db.execute("SELECT count(*) FROM jobs").fetchone()[0]
            unrevoked = db.execute("SELECT count(*) FROM approvals WHERE invalidated_utc IS NULL").fetchone()[0]
            last = db.execute("SELECT occurred_utc FROM events ORDER BY id DESC LIMIT 1").fetchone()
        return {"jobs": jobs, "unrevoked_approval_records": unrevoked, "last_event_utc": last[0] if last else None,
                "last_event_vietnam": display_vietnam(last[0]) if last else None}

    def doctor(self) -> dict[str, Any]:
        return {"data_dir": str(self.data_dir), "data_dir_outside_repo": True,
                "network_execution": False, "browser_execution": False,
                "global_guard_provided": False, "approval_binding": "sha256_not_signature"}

    def load_private_json(self, path: str | Path) -> dict[str, Any]:
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_relative_to(self.data_dir):
            raise ValueError("input JSON must be inside the private data directory")
        value = json.loads(resolved.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON document must be an object")
        return value


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
