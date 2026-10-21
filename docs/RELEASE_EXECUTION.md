# Host-mediated execution evidence — 2026-10-21

## Implemented

- Schema 3 adds execution runs, one pending action, unique durable attempts and append-only confirmation snapshots to the existing private SQLite workspace. Schema 2 upgrade/reinitialization retains reviewed documents and approvals.
- An optional exact bridge/runtime scope must be reviewed in a new manifest. Preparation-only approvals remain disabled. Runtime is 1..60 minutes, bounded by expiry.
- The designated agent follows inspect → permitted fill/upload → review → single submit → verify. ASSIST ends after review. Browser access comes from the host; no browser driver, extra model API, credentials export or background worker is bundled.
- Fresh form observations stop changed/missing required answers, consent drift, challenges and file-format mismatch. Final visible values/choices/document hash must match. check-action rechecks the issued request immediately before the host action.
- A unique immutable attempt consumes its slot before submit is returned. Missing submit acknowledgement recovers as verify only. Unknown stops further jobs. Read-only reconciliation survives expiry/revocation and cannot retry.
- Reports distinguish successful host action receipts, durable attempts, host-observed confirmations and unknown states. Receipts do not independently authenticate the host or employer outcome.

## Executed checks

Windows, bundled Python 3.12.14:

```text
python -m unittest discover -s tests -v
77 tests passed
python scripts/generate_adapters.py --check
No drift; no active settings touched
python scripts/check_repository.py
Passed bounded public-source/skill checks
```

The execution suite includes the actual CLI request/check/receipt/report loop,
ASSIST, sequential multi-entry budgets, coordinator races, receipt replay,
scope binding, additive migration, stale files, revoked/expired approval,
fresh form drift, final-review mismatch, bridge interruption at submit and
later read-only reconciliation. A bounded independent review found three
issues (late blockers, missing required answers, misleading preparation reports);
all were corrected with regressions. Existing preparation/hooks tests remain intact.

Separately, Codex desktop's supported in-app-browser tools on Windows filled the
loopback fictional portal, selected the fixed file through its chooser, clicked
submit once and observed “Fictional application submitted,” FICT-1, Negotiable,
the filename and its exact file hash. The portal accepts only fixed fictional
values and rejects duplicate submissions. It has no external resources or telemetry.

Private screenshot evidence: JPEG, 1280×720, 42,158 bytes,
SHA-256 `ff3a7ba1d837b7c4f196dc36b97b54e308348c3feadf7db7047ac028fa2013e0`.
Screenshot bytes remain outside public Git.

## Limits

The HTTP UI smoke is separate from HTTPS engine contract tests: no production
HTTP exception, certificate bypass or real employer end-to-end test was added.
Native Codex skill discovery/hooks, Claude execution and unidentified Grok
integration remain unverified. Employer-specific mappings and current operation
permission require separate evidence; no LinkedIn automation is enabled.
Optional preparation-only hooks still deny browser control and are never
disabled by this engine. A host denial requires manual handling.

Existing Linux optional rendering evidence is unchanged. Local Windows has no
LibreOffice; new Linux CI must recheck real rendering after the shared document
snapshot refactor. See execution.md for the complete operation protocol.
