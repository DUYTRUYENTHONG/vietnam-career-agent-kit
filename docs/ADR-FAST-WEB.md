# ADR: opt-in public research adapters

Status: accepted for the Firecrawl research increment, 22 October 2026.

The offline kit already validates selected preparation packages and executes one
host-browser action at a time. Repeated page retrieval is a separate latency and
cost boundary. Adding a remote application agent would discard those controls.

Use original stdlib HTTP code under `adapters/providers/`, imported only by new
explicit research commands. Keep local initialization/import/rendering offline.
Schema 5 adds research plans, provider tasks, evidence, cache, import provenance
and numeric diagnostics to the same private `workflow.sqlite3`. Initializers and
execution/authorization/cleanup guards accept 5 and reject newer versions.

```mermaid
flowchart LR
  Plan[Reviewed public plan] --> Scope[Source permission and URL checks]
  Scope --> Cache[Eligible private evidence cache]
  Cache --> Provider[Firecrawl v2 search or selected extraction]
  Provider --> Task[Durable task ID and progressive status]
  Task --> Evidence[Immutable captured evidence]
  Evidence --> Import[Referenced normalized JD import]
  Import --> Existing[Existing assessment and selected preparation]
  Existing --> Host[Existing sequential host executor]
```

Search-only plans return leads. Selected URL plans use individual scrapes or
per-domain asynchronous batches. Each remote batch uses concurrency one; the
number of outstanding domains is clamped to the explicitly configured account
concurrency and plan bounds. Default account concurrency is one. SQLite writes
belong to one coordinator and transactions never span network waits. A partial
unique index deduplicates in-flight equivalent requests across coordinators.

Alternatives: an SDK would add a dependency/retry layer without a current need;
a second tracker/distributed queue would split authority; unconditional cloud
browser automation would require new disclosure and execution contracts. None
is introduced. TinyFish public research and direct sessions remain separate
increments, unsupported here. Existing manifests cannot authorize either vendor
to receive candidate data.

Trade-offs: polling is explicit, no background worker; the host still normalizes
and reviews semantic claims. Remote queue time and billing are unknown unless
reported. Provider-side navigation is not a local sandbox: initial DNS/URL checks
and returned-destination quarantine cannot prevent an upstream service following
a redirect before returning it. Use only independently permitted public sources;
do not use this adapter when that limitation is unacceptable.

See FAST_WEB.md for finite budgets, recovery and current verification limits.
