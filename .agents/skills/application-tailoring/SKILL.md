---
name: application-tailoring
description: Draft job-specific CV wording and application emails from confirmed evidence, preserving factual qualifiers and the employer's language and format.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Draft job-specific CV wording and application emails from confirmed evidence.
Select and order relevant facts; improve readability without adding experience.

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

For source-bound rewriting, use the opt-in v2 contract in docs/CV_CONTENT_V2.md
and schemas/cv-content-v2.schema.json. Produce one structured wording pass from
selected exact facts, complete requirements and current matrix. Keep original
evidence unchanged. First v2 slice permits one fact per statement; employment/
project groups require approved matching scope#locator annotations. Missing
evidence returns needs_input before drafting. No invented synthesis or outcomes.
Use import-wording --include-review-packet to remove a separate packet CLI start
while retaining fresh checks. A separately prompted independent pass must review
every statement before review-wording; at most one focused repair, then block or
fall back to reviewed exact claims. Never use the fictional demo review helper
for an actual person. Metadata records the real observed host configuration or
an explicit unavailable value; it does not change the running host model.

For CV rewrites, cover notes or application emails, read
references/evidence-writing.md. Use its source-first draft, concise language edit
and fact comparison within the existing wording/review pass; do not add another
model call solely to remove generic phrasing. Preserve language, qualifiers and
metric units after editing or translation. New candidate facts require evidence,
not a more persuasive rewrite.

Email drafting returns a private draft and evidence map, not a send command.
Match the actual employer/requisition, published recipient, verified sending
mailbox, exact subject/body and reviewed attachment. For the Gmail plugin, use
the existing sender/to/subject/body answer-provenance contract; generated prose
is not candidate-confirmed merely because it was drafted. Follow the existing
manifest or standing-scope review before execution. See ../../../prompts/TAILOR_AND_EMAIL.md.

## Outputs

Markdown CV draft, private source map, hashes and review_required state.

V2 additionally returns the actual wording fingerprint and optional compact
review packet. Imported wording is pending, never disclosure authority. Markdown,
DOCX and PDF consume the same approved content model after factual review.

## Failure behavior

Unconfirmed facts, wrong language, closed/unverified/ineligible vacancy or stale assessment block drafting. Missing renderer must not be described as a verified PDF/DOCX.

## Side-effect limits

Local draft artifacts only; no upload, approval or external messaging.

## Tests and examples

examples/fictional/plan.json; tests/test_preparation.py and tests/test_cli.py.
