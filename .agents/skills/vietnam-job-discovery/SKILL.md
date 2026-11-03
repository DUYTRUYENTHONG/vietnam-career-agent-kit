---
name: vietnam-job-discovery
description: Discover a finite Vietnam-relevant shortlist through permitted sources, or import supplied postings when browsing or connector permission is unavailable.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Discover a finite Vietnam-relevant shortlist through permitted sources, or import supplied postings when browsing or connector permission is unavailable.

## Inputs

Confirmed role/location constraints, finite source/query/date/job budgets and source registry.

## Required capabilities

Host search/browser or user-provided JD; no network connector is assumed from a registry entry.

## Steps

Prefer fresh eligible evidence or an existing documented feed before optional
cloud retrieval. For experimental Firecrawl research read ../../../docs/FAST_WEB.md
and preview with `discover --plan FILE --dry-run`. For experimental TinyFish
Fetch read ../../../docs/TINYFISH_SETUP.md and preview with
`tinyfish-fetch --plan FILE`; it accepts 1-10 selected public URLs, not search
or natural-language Agent goals. Live dispatch requires the exact finite reviewed
public plan with `--live --approve-plan HASH` and separately permitted sources.
No CV, account session, private contact or application answers enter research.
Reconcile existing uncertain tasks through their documented status/report path;
do not launch a replacement. A source block never permits provider hopping.

TinyFish Browser is a separate experimental guest-form execution adapter; Fetch
does not create application sessions. Route that work to ../browser-application/SKILL.md
and ../../../docs/TINYFISH_BROWSER.md with its additional provider disclosure and
execution scope. This discovery skill does not start browser/application runs or
establish live provider, billing or throughput compatibility.

Read connectors/registry.json and per-action policy evidence. Manual versioned import-jd works now. Treat snippets as leads; verify full duties/status when permitted. Preserve retrieval/coverage, inaccessible sources and duplicate leads. Do not activate reference installers.

For an ongoing campaign, read ../../../docs/campaign-continuity.md and the latest
private checkpoint before searching. Continue successive finite batches within
the confirmed scope; retain search coverage and blocked leads to avoid repeating
dead ends. Check the canonical ledger for prior and uncertain applications.
Do not expand location, seniority or fit merely to reach a numerical target.
When the candidate authorizes adjacent role families, use
../../../docs/DISCOVERY_ACCELERATION.md to broaden discovery while preserving
evidence-based assessment. Prefer permitted documented board lists, deduplicate
before full-JD reasoning and retain dated coverage. The guide alone grants no
source permission; the experimental Greenhouse reader is described below, and
other unsupported reads stay manual.

## Outputs

Before importing selected leads, use `check-lead-identities --file FILE` against
the explicitly selected private workspace. Supply 1–50 known identity records
under ../../../schemas/lead-identities.schema.json; unknown identity strings may
stay empty. Follow ../../../docs/LEAD_IDENTITY_CHECK.md. Recorded matches need
identity/receipt review; unmatched results do not prove a job is new or suitable.
No import, CV scan, account access or execution authority follows this read.
For an older canonical ledger, use `check-legacy-lead-identities --ledger FILE
--file FILE` instead, without `--data-dir`. This explicitly reads the older jobs
metadata projection only; missing/incompatible ledgers stay errors. Never run
init, migrate a campaign or create a second tracker to enable identity lookup.

For verified Greenhouse board tokens, use `python scripts/kit.py discover-greenhouse
--board TOKEN` to read up to twelve boards with at most three workers. See
../../../docs/BULK_DISCOVERY.md. This experimental read-only connector returns
untrusted leads and explicit partial failures, not assessed/imported jobs. Compare
stable IDs and fingerprints with dated coverage and the canonical application
tracker before full-JD reasoning. Never count discovery as an application or infer
Vietnam remote eligibility from a generic remote label. Other unsupported sources
remain manual; this command does not grant fill/upload/submission permission.

Dated source coverage and candidate job inputs with verified or explicitly unverified status.

For verified Ashby board names, use `discover-ashby` with the same board/worker
bounds. See ../../../docs/ASHBY_DISCOVERY.md. It returns listed posts only and
preserves raw workplace/employment metadata. Ashby's isRemote flag includes
hybrid roles: never infer Vietnam eligibility from it, and never treat Intern
as regular employment. Neither reader imports candidates or submits applications.

## Failure behavior

Unknown source permission stays manual. Blocked/unreadable is unverified, not closed; no universal coverage claim.

## Side-effect limits

Only permitted discovery/read; no candidate account, fill, upload or submit.

## Tests and examples

python scripts/kit.py source-registry; examples/fictional/job.json; tests/test_preparation.py.
