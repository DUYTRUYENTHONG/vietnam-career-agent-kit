# Private data contract

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

The SQLite tool currently supports job upsert/liveness, status, package validation and approval/invalidation. Status reports `unrevoked_approval_records`: database records without explicit revocation, which may still be stale because of file changes or a hook marker. It is not a count of valid disclosure approvals; use `check-approval` with the exact current package. Its state vocabulary supports later lifecycle integrations, but there is no generic transition-to-submitted CLI or live submitter. Do not simulate unsupported transitions. If a host adds state writes, require evidence and immutable submitted snapshots before exposing those operations. Core event rows are append-only, with actor and UTC time; display uses Vietnam +07:00.

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
