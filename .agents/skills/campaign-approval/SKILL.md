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

Honor a candidate-requested CV enrichment/review hold before preparing any new
disclosure action; see ../../../docs/CV_ENRICHMENT.md. Do not derive authority
for a superseded attachment while its replacement review is pending. Keep prior
submission records immutable and use existing exact-version checks after review.
This is an agent instruction, not an additional CLI enforcement mechanism.

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

Prefer launch-execution with the exact manifest/standing fingerprints and reviewed
bridge/runtime to derive authority, start and return the first request in one
call. It does not create approval proof. If the response identifies an existing
run, reconcile its pending action; never replay launch or browser mutations.

## BrowserAct authorization

For BrowserAct, service `auth login` is separate from candidate authority. Bind
the exact execution scope to browser-act before using its session planner;
another bridge's approval cannot be borrowed. Upstream confirmation guidance
does not replace these checks or host action-time confirmations. See
../../../docs/BROWSERACT.md for the reviewed integration boundary.

## Outputs

Reviewable exact manifest or explicit needs_input/manual_required; never a manufactured approval.

## Failure behavior

Unknown required fields, stale files/review/permission/expiry or wrong destination/hash/action block validation. Unverified/manual platform scope produces manual_required. Legal/sensitive attestations stay with the user. Never claim legacy records have the new manifest guarantees or that validation executes an application.

## Side-effect limits

This skill only records/revokes exact local authorization. Use browser-application for guarded execution; approval alone never performs a disclosure or submission.

## Tests and examples

tests/test_manifests.py; tests_optional/test_rendering.py; docs/documents-and-approval.md.
