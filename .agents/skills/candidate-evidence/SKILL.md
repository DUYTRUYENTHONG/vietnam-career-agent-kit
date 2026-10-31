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

For candidate-requested CV enrichment, use ../../../docs/CV_ENRICHMENT.md.
Candidate-owned public code establishes implementation, not personal authorship,
paid tenure or measured business impact. Keep proposed additions separate from
confirmed facts until their actual review. Never borrow internet examples as
candidate accomplishments.

For development-plan artifacts, follow ../../../docs/CAREER_GROWTH.md.
`growth-evidence` records an existing file hash and contribution note as submitted
for candidate review; it does not establish completion, authorship, skill or
paid tenure. Review actual work and assistance, import its authorized evidence,
confirm the exact changed profile and reassess before any CV wording. Never
promote a proposed learning task, tutorial, course or model output as a fact.

Run import-cv, then import-profile. Map exact claim/quote/source/locator/status and conflict keys. Inspect profile, ask only unresolved facts, then record confirm-profile only after actual review of its exact fingerprint. Never create user confirmation on behalf of a real person.

For opt-in v2 grouped history, retain exact context facts and use reviewed
scope#location locators for each employment/project. Matching locator prefixes
are scope annotations, not proof of a source span. Reconfirm changed profile
annotations; do not rewrite evidence to fit a draft. Candidate-local working-set
and bullet-variant caches are not implemented in this slice. Keep original
qualifiers, dates and contribution scope in the authoritative facts.

## Outputs

Immutable normalized UTF-8 evidence, profile fingerprint, conflicts and confirmation state.

## Failure behavior

Unsupported extraction returns manual_required. Missing/changed source, wrong candidate or unresolved conflicts block affected work.

## Side-effect limits

Local evidence/profile writes only; no upload, public biography or disclosure.

## Tests and examples

tests/test_preparation.py; examples/fictional/profile-a.json and profile-b.json.
