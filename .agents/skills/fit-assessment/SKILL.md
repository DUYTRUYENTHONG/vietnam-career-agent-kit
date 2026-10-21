---
name: fit-assessment
description: Validate a complete requirement-to-confirmed-evidence matrix and classify fit without invented ATS scores, seniority or unsupported qualifications.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Validate a complete requirement-to-confirmed-evidence matrix and classify fit without invented ATS scores, seniority or unsupported qualifications.

## Inputs

Confirmed current profile, structured job ID and versioned matrix with every requirement exactly once.

## Required capabilities

Local assess command; nuanced semantic mapping still needs candidate/reviewer judgment.

## Steps

Use direct/partial/missing/unknown evidence treatment. Direct field/value links require exact reviewed equality; partial needs a limitation. Apply explicit exclusions/conditions first. Keep missing mandatory, unknown eligibility and unsupported facts visible. Store current profile/JD fingerprints.

## Outputs

Evidence matrix, constraints and Strong fit/Plausible fit/Stretch/Ineligible/Needs clarification.

## Failure behavior

Forged links, pending facts, duplicate/missing requirements and stale profile block assessment. Classification is not hiring/legal eligibility verification.

## Side-effect limits

Local assessment/tracker update only; no factual repairs or application approval.

## Tests and examples

examples/fictional/matrix.json; tests/test_preparation.py.
