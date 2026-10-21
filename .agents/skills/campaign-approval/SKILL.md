---
name: campaign-approval
description: Prepare and check exact finite application disclosure/submission manifests after candidate review; no blanket recipient or artifact approval.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Prepare and check exact finite application disclosure/submission manifests after candidate review; no blanket recipient or artifact approval.

## Inputs

Candidate, finite jobs/destinations, current artifact/answer hashes, consents/actions/expiry/limits and actual explicit approval.

## Required capabilities

Local create-manifest, approve-manifest, check-manifest and revoke-manifest. Reviewed rendered artifacts are required. Browser and attempt/submission execution are unavailable.

## Steps

Identify recipient/requisition and every disclosure. Build a finite plan from actually reviewed files, confirmed ordinary answers, explicit consents, per-host permission evidence, operations, UTC expiry and limits. Create the manifest, show its exact exported scope, then record an actual explicit approval of that fingerprint. Check intent hashes/destination/action before any future disclosure; execution_enabled remains false in this slice. Changed overlapping scopes revoke old approvals. Local records cannot authenticate a human or grant platform permission. See docs/documents-and-approval.md.

## Outputs

Reviewable exact manifest or explicit needs_input/manual_required; never a manufactured approval.

## Failure behavior

Unknown required fields, stale files/review/permission/expiry or wrong destination/hash/action block validation. Unverified/manual platform scope produces manual_required. Legal/sensitive attestations stay with the user. Never claim legacy records have the new manifest guarantees or that validation executes an application.

## Side-effect limits

Local exact review/bookkeeping only; no live disclosure, attempt creation or batch execution.

## Tests and examples

tests/test_manifests.py; tests_optional/test_rendering.py; docs/documents-and-approval.md.
