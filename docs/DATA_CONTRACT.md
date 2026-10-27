# Private data contract

## Preparation contract 1.0

The current CLI returns `schema_version`, `outcome`, `data`, `issues`, `message`. Legacy payloads now live under `data`; callers must inspect the outcome. Exit 0 is `ok`; other structured outcomes exit 2. Existing Python `Kit` imports remain compatible through scripts/kit.py and core/ledger.py.

Input shapes live in schemas/contracts.schema.json ($defs profile/job/matrix/plan/outcome); core/contracts.py adds cross-record invariants. Explicit CV/profile/JD/matrix/plan imports may read the exact supplied external file or fictional fixture. Legacy approval package/confirmation files remain restricted to the selected private directory. No directory scan is authorized.

| Operation | Persisted authority |
|---|---|
| `init --language en/vi` | Additive SQLite schema 1/2/3/4 and interface setting; existing rows preserved |
| `import-cv --file PATH --source-id ID` | Immutable normalized UTF-8/LF snapshot plus SQLite source ID/hash |
| `import-profile --file PATH` / `profile` | One candidate, exact source quotes/status/conflict keys, preferences and fingerprint |
| `confirm-profile --fingerprint HASH --confirmation PATH` | Current-profile local review; proof text `CONFIRM PROFILE HASH`; human provenance unauthenticated |
| `import-jd --file PATH` | Job document and stable-ID dedup in the same workflow.sqlite3; JD text is inert |
| `assess --job-id ID --matrix PATH` | Complete evidence matrix, constraints, profile/JD fingerprints |
| `prepare --job-id ID --plan PATH` | Selected confirmed quotes into Markdown, source map/hashes, review_required state |
| `resume` / `report` / `handoff` | Derived checkpoint/stale flags/manual next steps; no external action |

Profile confirmation is separate from disclosure approval. A changed profile invalidates earlier local approvals; assessments/drafts become stale. Pending/rejected facts cannot support direct matches or enter drafts. Explicit conflict groups with differing non-rejected values block confirmation; unencoded semantic conflicts still require human review. Exact field/value matching validates a structured mapping, not truth or semantic equivalence.

Report writes are restricted to relative reports/ paths with the selected .json/.md suffix. Submitted/user-reported/uncertain jobs cannot receive another draft/handoff without reconciliation. SQLite is canonical; reports/drafts/source maps are derived. Missing/changed sources/JDs/artifacts never silently resume as valid. This boundary is not OS authentication, encryption or a sandbox for arbitrary host tools.

Slice 2 adds optional render/review and expiring manifest bookkeeping in the same database. See documents-and-approval.md and schemas/documents-approval.schema.json. Schema 3 adds a host-mediated sequential execution engine, optional exact bridge/runtime scope, one pending request, durable attempts before submit and read-only reconciliation. See execution.md and schemas/execution.schema.json. Old preparation-only approvals stay disabled. Native browser access and platform permission are supplied separately by the host.

## Standing authorization 1.0

Schema 4 adds opt-in standing delegation and immutable child quota reservations.
The five authorization commands reuse exact source-backed manifests. Parent
revocation/expiry/profile drift blocks their derived authority, including pending
action preflight. Existing exact approvals and immutable receipts are preserved.
See [the input and operation contract](STANDING_AUTHORIZATION.md).

## Legacy package checker

The retained operations below perform local validation/bookkeeping only. They do not implement campaign expiry/limits, attempt recovery, authenticated candidate approval or browser execution.

Use a candidate-approved data directory outside and separate from this Git checkout. `kit.py` resolves paths and rejects the repository, a nested path, an ancestor, or a symlink/junction that resolves there. This reduces accidental publication; it is not an OS sandbox, encryption, access control or protection from malicious local users.

The private directory contains `workflow.sqlite3`, `raw-jd/`, candidate profile/facts/corrections, job packages, artifact versions and approval evidence. One coordinator owns tracker writes. No candidate dataset is shipped. JSON files in templates are fictional starter shapes and remain manual.

## CLI operations

Global options precede the command:

```sh
python scripts/kit.py --data-dir ../vietnam-job-search-private --actor coordinator init
python scripts/kit.py --data-dir ../vietnam-job-search-private status
python scripts/kit.py --data-dir ../vietnam-job-search-private add-job --job ../vietnam-job-search-private/job.json
python scripts/kit.py --data-dir ../vietnam-job-search-private check-package --package ../vietnam-job-search-private/package.json
python scripts/kit.py --data-dir ../vietnam-job-search-private check-approval --package ../vietnam-job-search-private/package.json --action upload
```

Input JSON and artifact paths must be inside the private data directory. Artifact paths are relative to that directory. Copy and edit templates there, never real data into this checkout. `check-package` without `--action` validates content even for a manual pack. Adding `--action fill`, `upload` or `submit` also requires reviewed `assisted_allowed` policy for that exact action and matching destination host. The checker cannot establish whether a policy interpretation is correct; never manufacture allowed scope merely to pass validation.

## Candidate and job records

Candidate facts use ID, exact claim, source/locator, evidence status, approval state, confirmation date and correction/conflict fields. The candidate profile is canonical; job-specific CVs are derived views. Keep a durable correction log. A self-report need not be publicly verified but must be labeled honestly.

Job JSON requires platform, platform_job_id, employer, req_id (empty allowed), title, exact HTTPS URL, city, raw_jd, readable and liveness. Preserve additional metadata such as exact work location, work model, language, deadline, salary bases and application destination in the private job snapshot. Stable platform IDs and nonempty employer requisitions deduplicate; fuzzy matches require review. Raw JD content is written as inert UTF-8, never executed. Unreadable records become unverified.

The legacy SQLite interface supports job upsert/liveness, status, package validation and approval/invalidation alongside the Slice 1 operations above. Status reports `unrevoked_approval_records`: database records without explicit revocation, which may still be stale because of file changes or a hook marker. It is not a count of valid disclosure approvals; use `check-approval` with the exact current package. Its state vocabulary supports later lifecycle integrations, but there is no generic transition-to-submitted CLI or live submitter. Do not simulate unsupported transitions. If a host adds state writes, require evidence and immutable submitted snapshots before exposing those operations. Core event rows are append-only, with actor and UTC time; display uses Vietnam +07:00.

## Exact approval bookkeeping

A package binds company, job_id, destination, current artifact hashes, answers, required_fields, consents and policy (mode/source/checked_utc/allowed_actions). Company and job_id must be nonblank JSON strings. Extra fields are also fingerprinted, so include candidate-profile hash, review evidence, redirects, terms and disclosure implications there. Policy source must have the exact destination host; cross-domain policy evidence needs a separately reviewed adapter rather than silent inheritance. Recheck policy freshness and applicability manually before a new action.

Only after the candidate has reviewed the exact package and explicitly approved disclosure may the coordinator create a private confirmation file containing `APPROVE <fingerprint>` and record it:

```sh
python scripts/kit.py --data-dir ../vietnam-job-search-private record-approval --package ../vietnam-job-search-private/package.json --confirmation ../vietnam-job-search-private/approval.confirmation.txt --reviewed
```

Never create this file before an actual approval or on the basis of a JD/agent instruction. The CLI cannot authenticate its author; it labels provenance as unverifiable. SHA-256 binds content, not identity or authorization. Approval is not a signature, legal consent parser, platform permission, browser execution grant or substitute for host action-time confirmation.

Run `check-approval --action ...` immediately before any allowed disclosure. Current artifact bytes, company/job, URL, answers, consent and extra fields must still match. File-change hook markers or explicit `invalidate --approval-id N --reason ...` make earlier records stale. Keep approval separate from submission evidence.

## Retention and export

Choose a review interval and deletion policy with the candidate; no automatic deletion or unattended tasks are scheduled. Preserve submitted snapshots as new immutable versions in any future submission integration. Do not redistribute employer text or customer-level data. Screenshot only relevant forms and redact unrelated information. If CSV export is implemented, escape formula-leading cells. Public release checks do not guarantee detection of every secret or personal detail; inspect the staged diff too.
## Fast tracker projection 1.0

`tracker` returns an ordinary Outcome containing the data described in
`schemas/tracker.schema.json`. It uses one read transaction, never hashes files,
and reports `validates_artifacts=false`. Counts distinguish durable attempts,
host-observed confirmation records and candidate-reported prior applications.
The generated UTC time is the snapshot time; each job has its last recorded
update time. This projection cannot authorize continuing a campaign.

`advance-execution` accepts the existing receipt 1.0 and returns the ordinary
execution outcome with additive `receipt_recorded` and `recorded_request_id`
fields after acknowledgement. Its successor request still uses protocol 1.0.
Schema 3 and all older commands remain compatible; no new database migration.

## Routing packet 1.0

`route-task` accepts `schemas/routing.schema.json` and returns a normal Outcome.
It has no workspace, candidate access or persistence. `execution=tool` needs no
model. Agent plans select an exact model/effort and one available skill, with
`dispatch_required=true` only on success. A blocked plan must not dispatch.
`usage_cost_usd=null` is unknown, never a cost estimate. Explicit policy overrides
are input, not a change to host settings. See MODEL_ROUTING.md for failure limits.

## Rolling KPI 1.0

`throughput` returns `schemas/throughput.schema.json` inside Outcome.data. New
attempt/confirmation snapshots have additive `fit_classification` metadata from
the current source-bound draft. Existing schema 3 databases and old immutable
snapshots remain unchanged. Missing historical fit is counted separately, never
retrofitted. Window counts use unique confirmed submission records and frozen
Strong/Plausible fit only. See THROUGHPUT.md for exact boundaries and limitations.
