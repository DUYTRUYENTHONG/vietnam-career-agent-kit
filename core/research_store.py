"""Additive private research storage. No network imports or calls."""


def migrate(db):
    for statement in [
        'CREATE TABLE IF NOT EXISTS research_plans(fingerprint TEXT PRIMARY KEY,payload TEXT NOT NULL,created_utc TEXT NOT NULL,started_utc TEXT NOT NULL,requests INTEGER NOT NULL DEFAULT 0,reserved_credits INTEGER NOT NULL DEFAULT 0)',
        'CREATE TABLE IF NOT EXISTS provider_tasks(id TEXT PRIMARY KEY,plan_fingerprint TEXT NOT NULL REFERENCES research_plans(fingerprint),operation TEXT NOT NULL,cache_key TEXT NOT NULL,state TEXT NOT NULL,remote_id TEXT,payload TEXT NOT NULL,result TEXT,error_code TEXT,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL,failures INTEGER NOT NULL DEFAULT 0,not_before_utc TEXT,UNIQUE(plan_fingerprint,operation,cache_key))',
        "CREATE UNIQUE INDEX IF NOT EXISTS research_single_flight ON provider_tasks(cache_key) WHERE state IN ('intent','running','uncertain','cancel_requested')",
        'CREATE TABLE IF NOT EXISTS research_cache(cache_key TEXT PRIMARY KEY,payload TEXT NOT NULL,stored_utc TEXT NOT NULL,expires_utc TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS research_evidence(id TEXT PRIMARY KEY,task_id TEXT NOT NULL REFERENCES provider_tasks(id),url_key TEXT NOT NULL,payload TEXT NOT NULL,artifact_path TEXT NOT NULL,UNIQUE(task_id,url_key))',
        'CREATE TABLE IF NOT EXISTS research_metrics(id INTEGER PRIMARY KEY,trace_id TEXT NOT NULL,stage TEXT NOT NULL,seconds REAL NOT NULL,occurred_utc TEXT NOT NULL,detail TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS research_imports(id INTEGER PRIMARY KEY,job_id INTEGER NOT NULL REFERENCES jobs(id),evidence_id TEXT NOT NULL REFERENCES research_evidence(id),job_fingerprint TEXT NOT NULL,reference_json TEXT NOT NULL,created_utc TEXT NOT NULL)',
        "CREATE TRIGGER IF NOT EXISTS research_evidence_no_update BEFORE UPDATE ON research_evidence BEGIN SELECT RAISE(ABORT,'immutable research evidence'); END",
        "CREATE TRIGGER IF NOT EXISTS research_evidence_no_delete BEFORE DELETE ON research_evidence BEGIN SELECT RAISE(ABORT,'immutable research evidence'); END",
    ]:
        db.execute(statement)
    if db.execute('PRAGMA user_version').fetchone()[0] < 5:
        db.execute('PRAGMA user_version=5')
