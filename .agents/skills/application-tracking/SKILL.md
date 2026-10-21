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

Local resume/report and SQLite. Browser outcome/attempt integration remains gated in the roadmap.

## Steps

Read resume before continuing. Check current source/profile/JD/artifact fingerprints and prior applications. Keep prepared/approved/confirmed/user-reported/unknown distinct. Report exceptions/coverage and next action. Preserve submitted snapshots and never infer submission from a draft/upload/click.

## Outputs

Current JSON or Markdown checkpoint, stale flags, exceptions and truthful application counts.

## Failure behavior

Uncertain outcomes require reconciliation, not another final attempt. Changed/missing artifacts block handoff until reviewed.

## Side-effect limits

Local tracker/report only; no mailbox scan, withdrawal, scheduler or automatic cleanup.

## Tests and examples

python scripts/kit.py --data-dir PATH resume; tests/test_preparation.py and tests/test_kit.py.
