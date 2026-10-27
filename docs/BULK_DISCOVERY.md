# Bulk discovery performance increment

## Architecture review, 22 October 2026

The CLI already combines launch and successor actions, while retaining durable
attempt reservations and fresh disclosure checks. Existing measurements show
roughly half a second for a fictional local launch. That is not the main evidence
gap behind a 100-confirmations/hour target: browser navigation, employer forms,
fit verification, document review and receipt collection remain unmeasured.
The preparation/execution engine does not supply a native employer browser driver.

This increment replaces repeated per-job discovery navigation with one documented
public board read per explicitly named Greenhouse employer. Up to three independent
boards are read concurrently; all ledger and submission work remains sequential.
No model chooses routing or parses the feed. No candidate profile is read or sent.

```console
python scripts/kit.py discover-greenhouse --board EMPLOYER_TOKEN --board OTHER_TOKEN
python scripts/benchmark_discovery.py
```

The command emits a versioned outcome containing discovery schema `1.0`:
`observed_utc`, `source`, `boards`, `leads_count`, `failed_boards`, `notice`.
Each successful board includes its token, raw-response SHA-256, received count and
leads with `greenhouse:TOKEN:POST_ID` identity, title, location, URL and
normalized content fingerprint. Descriptions are omitted from compact output by
default to avoid sending every JD through model context. `--include-content`
includes full untrusted descriptions, suitable for tool-only storage outside the
clone and selected later review. Both modes fingerprint the full current JD.
Identical duplicate posts collapse; conflicting duplicate IDs invalidate that board. Stable fingerprints allow a host
to compare dated coverage before repeating expensive review. The command itself
does not persist a cache or consult applications, so it cannot skip already-applied
jobs without the host checking the canonical tracker.

Input bounds: 1–12 explicit board tokens, 1–3 workers, 4 MB/board, 5,000 records/board,
10-second socket timeout. The socket timeout is not an overall elapsed deadline.
Only the fixed HTTPS Greenhouse origin is contacted, with GET and no candidate
data, credentials, cookies, environment proxies, redirects or automatic retries.
429/errors become sanitized per-board failures; successful boards are preserved.
Any failure returns `manual_required`, not full coverage. Output URLs/content are
untrusted and never opened or executed. Tokens must come from verified employer
boards; this is not global job search or proof a company permits every operation.

These leads are deliberately not complete `import-jd` inputs. Fit, employment type,
Vietnam remote eligibility, current liveness and source-specific submission rules
require review. Do not auto-reject ambiguous remote locations or infer years of
experience from title keywords. No automatic application POST is implemented.

## Benchmark and acceptance

Seven alternating fictional runs, 12 boards × 100 posts, identical simulated
50 ms I/O per board: serial median **631.272 ms** (618.768–647.003), three workers
**215.581 ms** (208.794–219.894), about **2.93×** scheduling throughput. Both paths
produce 1,200 leads. This is a reproducible simulated scheduling result, not an
observed Internet speedup, application rate, token saving or dollar saving.
Deterministic tests verify the concurrency ceiling, duplicate request suppression,
stable order/identity, fail-closed normalization and explicit partial failures.

Next measurement gate: use a host bridge to record discovery, assessment, render,
browser navigation, fill/upload, agreement handling, submit and confirmation times
separately. Count only saved confirmed new suitable submissions. A 100/hour target
requires an average completion every 36 seconds; this change does not establish it.
Optimize the measured slow stage next. Never parallelize final clicks against the
same attempt, retry uncertain submissions or reuse stale authority/artifact checks.

## Primary references and compatibility

Checked 22 October 2026: [Greenhouse Job Board API](https://docs.greenhouse.io/job-board)
documents public GETs, `content=true`, post IDs and employer-key-authenticated
application POST. [Lever's official Postings API](https://github.com/lever/postings-api)
describes tenant listings, hosted application forms and authenticated application
integration. Lever is researched only, not implemented here. No third-party source
code or dependency was adopted.

Status: **Experimental** stdlib Greenhouse discovery, covered by fictional mocked
transport/CLI tests. No live employer/browser certification. Existing workspace
schema 1–4 and execution contracts remain unchanged. Discovery does not grant
submission authority or modify application/tracker counts. Failures must not be
reported as closed vacancies or successful complete searches.
