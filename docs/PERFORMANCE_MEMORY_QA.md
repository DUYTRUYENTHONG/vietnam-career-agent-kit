# Performance and career memory QA

Scope: local per-model observation imports/reports, confirmed-fact retrieval,
professional email context and reviewed CV wording exports. Fictional people
and temporary workspaces only. No candidate account, employer submission, paid
model, new dependency, model-weight training or application authority.

Observed locally on 27 October 2026, Windows/Python 3.12.14:

| Gate | Result |
|---|---|
| Full standard-library suite | **295 passed**, 455.117 seconds |
| Optional locked MCP/browser integration suite | **4 passed**, 43.105 seconds |
| Source hygiene / ten canonical skills | Passed, 267 UTF-8 source files, no flagged artifacts |
| Host-wrapper synchronization | Passed, no drift or active settings changes |
| Slice-1 and reviewed-wording fictional demos | Passed |
| Maintainer diff / whitespace review | Passed; this is not independent peer review |

## Reproduce

```sh
python -m unittest discover -s tests -v
python scripts/check_repository.py
python scripts/generate_adapters.py --check
python scripts/demo_slice1.py
python scripts/demo_wording.py
python scripts/benchmark_memory.py --facts 1000 --samples 10
# Optional locked MCP environment:
python -m unittest discover -s tests_plugins -v
```

Required protected-main CI retains the four OS/Python fictional-test jobs plus
document integration and local-plugin integration. Feature branches run that
suite on pull requests, with main push/manual dispatch retained. Removing the
duplicate feature-push trigger changes scheduling, not test content or required
checks. Final exact-commit CI evidence belongs in the linked PR checks.

## Observed local benchmark

Windows, Python 3.12.14, SQLite 3.53.1. Command above, 1,000 fictional confirmed
facts, 10 retrieval samples; full current source/profile validation and new
in-memory index per call. Measured wall-time p50 **25.665 ms**, maximum **27.401 ms**.
No timing threshold in unit tests; hardware/load affects repeat results.

| Four authored query labels | BM25 | Literal token-overlap baseline |
|---|---:|---:|
| Positive queries | 3 | 3 |
| Mean precision@1 / recall@1 / reciprocal rank | 1.0 / 1.0 / 1.0 | 0.667 / 0.667 / 0.667 |
| Negative queries / false positives | 1 / 0 | 1 / 0 |

The difference comes from the authored Vietnamese query without diacritics; it
does not establish semantic retrieval quality, broad language coverage, production
RAG, candidate/employer acceptance or application speed. No baseline latency or
model/token/dollar saving was measured. Host token usage stays unavailable.

## Bounded review findings addressed

- Unknown token/duration/charge values are distinct from zero; cache/reasoning
  subsets cannot exceed known totals or be added twice. Reports retain missing
  coverage and separate currencies, without pricing or quota inference.
- Source imports read bounded bytes and verify their hash. Immutable event IDs,
  append-only observations, unknown feature versions and export path confinement
  preserve application records and prior measurements.
- Retrieval revalidates current evidence and ignores pending facts. Queries are
  literal parameterized FTS terms; whole facts preserve qualifications. Missing
  FTS5 and unsupported schema versions produce handoffs instead of empty success.
- Dataset exports reuse current independent wording review, omit identity headers,
  keep model output pending and group same-job/exact-output duplicates. Checks
  parse the same bounded bytes they hashed, recheck current provenance and reject
  forged counts even when a manifest hash has been recomputed.
- Real MCP stdio tests exercise discovery, schema rejection, retrieval, evaluation,
  unreviewed-export refusal and opt-in configuration. Default email/browser setup
  remains compatible; there is no arbitrary-file, SQL, training or approval API.

## Limits

Telemetry import is caller-reported, source-hash-bound evidence, not automatic or
authenticated host metering. An email context is a draft brief, not a quality-rated
email example. Export checks detect stale data, not authentic reviewer identity.
Exact-output grouping does not eliminate semantic leakage or same-candidate fact
overlap. One group is a collection only, not a train/evaluation split.

Local stdio protocol tests do not certify native Codex/Claude marketplace install,
Grokbot/Muse tool availability, real Gmail OAuth, live browser submissions or an
hourly application KPI. Production hybrid retrieval and actual fine-tuning remain
future acceptance gates.
