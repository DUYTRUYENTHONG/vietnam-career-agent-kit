# Bounded public Ashby discovery

`discover-ashby` reads explicitly named public Ashby boards without opening a
candidate workspace. Use names from verified employer career links, not guessed
tenant lists. This is discovery only; it never uploads or submits.

```console
python scripts/kit.py discover-ashby --board EMPLOYER_BOARD
python scripts/kit.py discover-ashby --board EMPLOYER_BOARD --board OTHER_BOARD --workers 2 --include-content
```

It shares the existing Greenhouse reader's bounded GET transport, ordered
concurrent merge and outcome envelope. No dependency, model API, credentials,
account connection, cache or ledger migration is added. Reading a board grants
no permission for an application or other platform operation.

## Output and identity

The outcome contains discovery schema `1.0`, source `ashby-public-board`, observed
UTC, per-board results, lead count and failed-board count. Successful boards
include the response SHA-256 and received record count. Leads contain:

- `ashby:BOARD:POST_ID` identity from the same-board hosted job URL;
- title, primary/secondary locations and available country metadata;
- raw workplace/remote and employment labels, department and team;
- published date, job URL and full normalized content fingerprint.

Descriptions are omitted by default. `--include-content` returns plain text, or
untrusted HTML if plain text is absent, with its format. Both modes use the same
fingerprint. Content is never executed or treated as instructions. Identical
duplicate IDs collapse; conflicting duplicates fail that board. Returned URLs
are never fetched automatically.

Only explicit `isListed: true` posts appear. Unlisted direct-link-only roles are
excluded. Missing listed status, unsupported API version, invalid field types
or unsafe/off-board URLs fail the affected board. Missing optional values stay
empty or unknown instead of receiving inferred defaults.

Ashby's `isRemote` may be true for **Hybrid** jobs. Preserve `workplaceType` and
location/country metadata; neither flag proves Vietnam remote eligibility.
`FullTime`, `PartTime`, `Intern`, `Contract` and `Temporary` remain distinct. A
full-time internship is still an internship. Fit, current availability and
application rules need separate review.

## Network and failure boundaries

Only the official public GET is contacted:
`https://api.ashbyhq.com/posting-api/job-board/BOARD`. Tokens contain 1–80 letters,
digits, underscores or hyphens. Limits: 1–12 boards, at most three workers,
4 MB and 5,000 records per board, ten-second socket timeout. This is not an
overall elapsed deadline. There are no cookies, authorization headers,
environment proxies, redirects, automatic retries or application POSTs.
Compensation is not requested.

Failures are sanitized per board; successful boards remain available. Any failed
board returns `manual_required`, not complete coverage or a closed-vacancy claim.

## Verification and limits

Fictional tests cover URL/board isolation, listed visibility, optional fields,
remote/hybrid distinctions, employment labels, content identity, bounds,
duplicates, concurrent reads, partial failures, no retry and CLI use without a
candidate workspace. Existing Greenhouse tests still pass.

One read-only Windows check on 31 October 2026 returned six listed postings from
an employer-linked board, matching its six visible browser entries. Local CLI
elapsed time was **1,269.991 ms**, including interpreter startup, network and
normalization. This single sample is not a serial/parallel comparison, general
provider certification, model-token saving or application-throughput result.
No application, candidate data or paid model was involved.

Status: **Experimental** stdlib CLI discovery with fictional transport tests and
that one public-board observation. It does not install native host tooling,
prove all tenants work, assess jobs or increase application counts.

## Primary references

Reviewed 31 October 2026: [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api)
documents the endpoint, API version, visibility, content/location/employment
fields and remote/hybrid distinction. Its [career-page integration guidance](https://docs.ashbyhq.com/using-the-lightweight-job-posting-api-to-list-openings-on-your-site)
describes listing postings then linking to hosted applications. No provider
source code or SDK was copied or installed.
