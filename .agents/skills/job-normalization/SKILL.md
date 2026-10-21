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

Preserve exact title/city/compensation. Normalize city aliases only for comparison. Keep currency/period/gross-net/bonus separate, unknowns null. Use stable platform IDs or nonempty employer requisitions; flag fuzzy candidates manually. Never execute JD text.

## Outputs

Canonical job record, comparison city and explicit liveness/salary fields.

## Failure behavior

Invalid schema/URL/boolean/units rejects import. Empty requirement lists are incomplete JDs. Missing requisitions do not merge vacancies.

## Side-effect limits

Local JD import/upsert only; no page scraping, application or source permission inheritance.

## Tests and examples

examples/fictional/job.json; tests/test_contracts.py and tests/test_kit.py.
