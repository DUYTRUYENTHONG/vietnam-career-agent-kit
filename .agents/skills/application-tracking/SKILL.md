---
name: application-tracking
description: Report and resume canonical private job/application state with current hashes, explicit unknown outcomes and duplicate protection.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Report and resume canonical private job/application state with current hashes, explicit unknown outcomes and duplicate protection.

## Inputs

One selected workspace and existing canonical tracker; observed evidence or separately labelled candidate reports.

## Required capabilities

Local resume/report and SQLite schema 3. Execution records distinguish durable attempts, host-observed confirmations and unknown outcomes; host receipts are not independent employer verification.

## Steps

Read resume before continuing. Check current source/profile/JD/artifact fingerprints and prior applications. Keep prepared/approved/confirmed/user-reported/unknown distinct. Report exceptions/coverage and next action. Preserve submitted snapshots and never infer submission from a draft/upload/click.

## Outputs

Return a timestamped Markdown tracker table after every application pass, including
when the pass is blocked. Include employer/role, source URL, recorded status,
blocker, next step and last update. Link the complete private report for longer
campaigns. Keep host-observed confirmations, candidate-reported prior applications
and uncertain attempts separate; always distinguish prepared from submitted.

Use `tracker --format md --output reports/tracker.md` for fast catch-up output.
It is a ledger projection, not a content/approval/liveness check. Use resume and
the normal action checks before actual work. No visualization file is required
for a table. Never describe the tracker as a background employer-response monitor.

## Failure behavior

Uncertain outcomes require reconciliation, not another final attempt. Changed/missing artifacts block handoff until reviewed.

## Side-effect limits

Local tracker/report only; no mailbox scan, withdrawal, scheduler or automatic cleanup.

## Tests and examples

python scripts/kit.py --data-dir PATH resume; tests/test_preparation.py and tests/test_kit.py.
