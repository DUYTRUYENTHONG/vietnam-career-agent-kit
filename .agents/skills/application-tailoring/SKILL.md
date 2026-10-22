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

Local prepare command for source-bound Markdown, followed by optional render and explicit document review for DOCX/PDF. See docs/documents-and-approval.md for requirements and limits.

## Steps

Prepare/render only selected assessed jobs after source and duplicate checks.
Reuse unchanged current evidence/documents only under existing fingerprints and
byte checks. Public extraction is not a reason to send CVs to a cloud parser or
to relax source-bound claims, PDFium locking or converter isolation.

Use prepare with the versioned plan. Keep target headline distinct from historical titles. Select/reorder confirmed quotes; retain classroom/prototype/team/metric qualifiers. Keep source map out of the CV. Follow employer document language, with separate versions.

## Outputs

Markdown CV draft, private source map, hashes and review_required state.

## Failure behavior

Unconfirmed facts, wrong language, closed/unverified/ineligible vacancy or stale assessment block drafting. Missing renderer must not be described as a verified PDF/DOCX.

## Side-effect limits

Local draft artifacts only; no upload, approval or external messaging.

## Tests and examples

examples/fictional/plan.json; tests/test_preparation.py and tests/test_cli.py.
