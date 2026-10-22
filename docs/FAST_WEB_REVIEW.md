# Firecrawl research release review

Bounded self-review of the first public research slice, 22 October 2026. This is
not independent peer review, live-provider certification or release promotion.

- Correctness: paid intents precede dispatch; IDs precede collection; terminal
  provider success still requires captured output. Partial/empty/error states
  remain explicit. Missing timestamps, salary and liveness are not inferred.
- Architecture: one SQLite workspace, additive schema 5, guards and old
  initializers preserve the newer schema. No application state-machine change,
  SDK, second tracker, background daemon or cloud browser.
- Security/privacy: fixed provider origin, no redirects/proxies in transport,
  source scope plus DNS checks before dispatch, exact safe pagination binding,
  no candidate inputs in research. Public remote navigation is not sandboxed;
  returned destination validation cannot prevent prior upstream redirects.
- Recovery: lost start response remains uncertain; partial-index single-flight
  prevents replacement; uncertain cancel is not repeated. Immutable canonical
  evidence precedes derived file export, allowing interrupted export recovery.
- Performance: explicit per-domain server concurrency one and configurable
  account bound; warm cache requires no provider credentials or DNS. Local
  measurements cannot establish Internet or application throughput.
- Fixes verified during implementation: stricter TTL/source keys, immutable
  repeated-page exports, pagination cursor recovery, cancellation uncertainty,
  newer-schema preservation, cross-platform timestamp fixture stability, and uncertain unexpected HTTP
  redirect/timeout/conflict responses.

Remaining limits: no configured credentials/live test; local credit reservations
are estimates, not provider-enforced billing caps; account quota is caller
configured; semantic normalization is reviewed by the host. TinyFish research
and direct Browser execution remain unsupported. Approval/file/form/submission
checks are never cached. Existing application/privacy/CAPTCHA restrictions remain.

Actual regression and benchmark results are recorded in PERFORMANCE.md and the
PR. CI is a separate gate; publication does not imply merge or deployment.
