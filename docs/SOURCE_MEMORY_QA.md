# Source-memory exclusion diagnostics QA

Scope: additive `exclusion_reasons` metadata in the existing source-memory
context result. No new tool, dependency, schema migration, model call, evidence
write or candidate approval is introduced.

- The reproduction failed before implementation with missing diagnostic output.
- Eight focused fictional tests pass, including overlapping exclusion conditions,
  empty-context CLI output, count totals, excluded-claim absence and unchanged
  source/workspace bytes. Existing stale-source, escaping-path, malformed-input,
  identity and size-limit tests remain in the same passing run.
- Classification preserves the existing eligibility predicate. A record has one
  primary reason in documented order; an invalid qualifying source still aborts
  retrieval rather than producing a diagnostic partial success.
- Standard-library unit and CLI tests do not prove native Codex/Claude MCP
  discovery, employer integration, semantic accuracy or improved CV outcomes.
- Full-suite, wrapper, hygiene and protected-branch CI results are recorded with
  the publishing PR; focused success alone is not the release gate.

The source-memory MCP server still exposes only its existing read-only context
tool; the new field flows through the shared function. The real pinned MCP stdio
test passed in 2.695 seconds with fictional pending/unhashed records and a later
source mutation. It verified the diagnostic counts, unchanged read-only tool
inventory and stale-source rejection. This is separate from native host
integration and is not a performance comparison.

Local release verification on Windows/Python 3.12: all 374 standard-library
tests passed in 3474.304 seconds. Wrapper synchronization, the bounded repository
hygiene scan, fictional demo and whitespace checks also passed. This records
observed test execution, not an application-submission throughput benchmark.
Protected-branch CI remains a separate publishing gate.
