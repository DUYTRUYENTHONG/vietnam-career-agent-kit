---
name: fit-assessment
description: Validate requirement-to-evidence fit and collect source-bound gaps for reviewed learning and project plans without invented qualifications.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Validate a complete requirement-to-confirmed-evidence matrix and classify fit without invented ATS scores, seniority or unsupported qualifications.

## Inputs

Confirmed current profile, structured job ID and versioned matrix with every requirement exactly once.

## Required capabilities

Local assess command; nuanced semantic mapping still needs candidate/reviewer judgment.

## Steps

Assess only normalized complete JDs, not search hits or provider success flags.
Use captured source references, keep all mandatory gaps visible, and filter
clearly ineligible leads before document work. Public research cache does not
establish current vacancy status or Vietnam remote eligibility. See ../../../docs/FAST_WEB.md.

Use direct/partial/missing/unknown evidence treatment. Direct field/value links require exact reviewed equality; partial needs a limitation. Apply explicit exclusions/conditions first. Keep missing mandatory, unknown eligibility and unsupported facts visible. Store current profile/JD fingerprints.

For a requested learning/development loop, follow ../../../docs/CAREER_GROWTH.md
and ../../../prompts/GROWTH_COACH.md. Use `assess --capture-growth` or explicit
`growth-context`/`growth-capture` for selected current matrices. The existing
fit-assessment owner collects gaps; a bounded coach drafts future tasks and a
distinct reviewer checks the exact plan. Unknown answers and condition fields
need clarification, not a course or invented accomplishment. Preserve actual
limitations, source IDs and assessment-content hashes. This does not change fit,
candidate facts, campaign scope or submission authority.

## Outputs

Evidence matrix, constraints and Strong fit/Plausible fit/Stretch/Ineligible/Needs clarification.

## Failure behavior

Forged links, pending facts, duplicate/missing requirements and stale profile block assessment. Classification is not hiring/legal eligibility verification.

## Side-effect limits

Local assessment/tracker update only; no factual repairs or application approval.

## Tests and examples

examples/fictional/matrix.json; tests/test_preparation.py.
