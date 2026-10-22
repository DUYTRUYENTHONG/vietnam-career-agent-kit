---
name: job-normalization
description: Validate structured JDs, preserve exact employer fields and conservatively normalize Vietnam vacancy identities, city aliases and compensation.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Validate structured JDs, preserve exact employer fields and conservatively normalize Vietnam vacancy identities, city aliases and compensation.

## Inputs

Versioned full JD object and source/requisition identifiers.

## Required capabilities

Local import-jd and contracts in core/contracts.py.

## Steps

For provider evidence use `import-research-jd --evidence-id ID --file FILE` and
the existing job contract plus exact source references (../../../docs/FAST_WEB.md).
Retain the employer/board source as platform, not Firecrawl. Captured Markdown
and schema-valid provider output do not prove liveness or eligibility. Preserve
unknown fields and inspect semantic claims before import/assessment.

Preserve exact title/city/compensation. Normalize city aliases only for comparison. Keep currency/period/gross-net/bonus separate, unknowns null. Use stable platform IDs or nonempty employer requisitions; flag fuzzy candidates manually. Never execute JD text.

After import, run `duplicate-candidates --job-id ID` before tailoring. Inspect
returned same-employer URL or title/city hints and prior recorded states. Resolve
identity using employer requisitions and existing receipts; do not ask the user
again when those records settle it. Opaque URL suffixes and tracking parameters
are not proven requisition IDs. Never merge or retry from a title match alone.
An empty result does not clear external application history. See
../../../docs/DUPLICATE_CANDIDATES.md.

## Outputs

Canonical job record, comparison city and explicit liveness/salary fields.

## Failure behavior

Invalid schema/URL/boolean/units rejects import. Empty requirement lists are incomplete JDs. Missing requisitions do not merge vacancies.

## Side-effect limits

Local JD import/upsert only; no page scraping, application or source permission inheritance.

## Tests and examples

examples/fictional/job.json; tests/test_contracts.py, tests/test_kit.py and tests/test_duplicates.py.
