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

Local create-manifest, approve-manifest, check-manifest and revoke-manifest. Reviewed rendered artifacts are required. Host-mediated execution needs a separately reviewed execution scope; no browser is acquired by approval.

## Steps

Identify recipient/requisition and every disclosure. Build a finite plan from actually reviewed files, confirmed ordinary answers, explicit consents, per-host permission evidence, operations, UTC expiry and limits. For execution, bind the exact available bridge_id and runtime_minutes (1..60) before creating the manifest. Show its exact exported scope, then record actual explicit approval of that fingerprint. Plans without execution scope remain disabled. Never manufacture a proof file in place of the user's approval. Check intent hashes/destination/action before disclosure; the execution loop also uses check-action immediately before each browser action. Changed overlapping scopes revoke old approvals. Local records cannot authenticate a human or grant platform permission. See docs/documents-and-approval.md and docs/execution.md.

## Standing authorization

When the user requests automatic routine approvals, configure an opt-in standing
scope using docs/STANDING_AUTHORIZATION.md. Name recipients/HTTPS prefixes,
ordinary answer bank, exact consents, confirmed profile, bridge, shared cap and
expiry. Obtain actual approval once; never infer a proof from the phrase alone.
For later reviewed Strong/Plausible applications within that scope, use
authorize-manifest instead of requesting a second local batch proof. Exact
manifest hashes and reviews remain mandatory. check-authorization reports quota
allocations, not submitted jobs. Host-required specific disclosure/action-time
confirmations remain separate. New recipients/answers/consents stay exceptions.

## Outputs

Reviewable exact manifest or explicit needs_input/manual_required; never a manufactured approval.

## Failure behavior

Unknown required fields, stale files/review/permission/expiry or wrong destination/hash/action block validation. Unverified/manual platform scope produces manual_required. Legal/sensitive attestations stay with the user. Never claim legacy records have the new manifest guarantees or that validation executes an application.

## Side-effect limits

This skill only records/revokes exact local authorization. Use browser-application for guarded execution; approval alone never performs a disclosure or submission.

## Tests and examples

tests/test_manifests.py; tests_optional/test_rendering.py; docs/documents-and-approval.md.
