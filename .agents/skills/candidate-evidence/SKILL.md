---
name: candidate-evidence
description: Import authorized CV evidence and validate one candidate profile with source quotes, conflicts and corrections for a private career workflow.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Import authorized CV evidence and validate one candidate profile with source quotes, conflicts and corrections for a private career workflow.

## Inputs

Explicit CV path, source ID and versioned profile JSON; no home-directory scan.

## Required capabilities

Local CLI; Slice 1 imports UTF-8 TXT/Markdown only.

## Steps

Run import-cv, then import-profile. Map exact claim/quote/source/locator/status and conflict keys. Inspect profile, ask only unresolved facts, then record confirm-profile only after actual review of its exact fingerprint. Never create user confirmation on behalf of a real person.

## Outputs

Immutable normalized UTF-8 evidence, profile fingerprint, conflicts and confirmation state.

## Failure behavior

Unsupported extraction returns manual_required. Missing/changed source, wrong candidate or unresolved conflicts block affected work.

## Side-effect limits

Local evidence/profile writes only; no upload, public biography or disclosure.

## Tests and examples

tests/test_preparation.py; examples/fictional/profile-a.json and profile-b.json.
