---
name: document-review
description: Review career documents for source grounding, role relevance, privacy, language and actual rendered layout; review is not candidate disclosure approval.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Review career documents for source grounding, role relevance, privacy, language and actual rendered layout; review is not candidate disclosure approval.

## Inputs

JD, source-backed profile, draft, source map and actual rendering evidence when available.

## Required capabilities

Local render, review-documents and reject-documents commands; optional locked Python packages, trusted LibreOffice Writer and DejaVu Sans fonts. Missing tools return manual_required.

## Steps

Run render on the current source-bound draft. Check every claim against evidence and exact scope. Distinguish prototype/production, evaluation/business impact and overlapping dates. Inspect content.json and EVERY current page image from the exact DOCX-to-PDF conversion. Record the fingerprint, all ordered page numbers and actual checks with review-documents using a private JSON file. Text extraction alone is not visual QA. Reject a bad set with reject-documents so dependent approval checks fail. See docs/documents-and-approval.md.

## Outputs

Precise blockers/improvements and factual/layout disposition with evidence locators.

## Failure behavior

Missing sources/rendering remain unverified. Reviewer critiques only and must not invent facts, confirmations or successful outcomes.

## Side-effect limits

Write review notes only; coordinator owns candidate facts, tracker and browser.

## Tests and examples

examples/fictional/; tests/test_documents.py; tests_optional/test_rendering.py; docs/documents-and-approval.md.
