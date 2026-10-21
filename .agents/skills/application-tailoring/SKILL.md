---
name: application-tailoring
description: Prepare job-specific truthful draft content by selecting and ordering confirmed source evidence; do not invent experience to match a JD.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Prepare job-specific truthful draft content by selecting and ordering confirmed source evidence; do not invent experience to match a JD.

## Inputs

Current assessment, job ID, explicit language and ordered confirmed fact IDs.

## Required capabilities

Local prepare command. Slice 1 produces Markdown; DOCX/PDF rendering is a later measured capability.

## Steps

Use prepare with the versioned plan. Keep target headline distinct from historical titles. Select/reorder confirmed quotes; retain classroom/prototype/team/metric qualifiers. Keep source map out of the CV. Follow employer document language, with separate versions.

## Outputs

Markdown CV draft, private source map, hashes and review_required state.

## Failure behavior

Unconfirmed facts, wrong language, closed/unverified/ineligible vacancy or stale assessment block drafting. Missing renderer must not be described as a verified PDF/DOCX.

## Side-effect limits

Local draft artifacts only; no upload, approval or external messaging.

## Tests and examples

examples/fictional/plan.json; tests/test_preparation.py and tests/test_cli.py.
