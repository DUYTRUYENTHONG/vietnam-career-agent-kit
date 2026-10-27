# Quality-gated fast pipeline: slice checkpoint

Development scope: reusable product, fictional candidates and controlled inputs.
No personal campaign, accounts, paid providers or employer submission tests.

| Slice | Acceptance | State in this change |
|---|---|---|
| Baseline and traces | Inspect provider/tailoring boundaries; reproduce legacy fictional preparation; monotonic local timings and explicit unavailable usage | Implemented; measurements in QUALITY_FAST_REPORT.md |
| Quality engine | Opt-in wording v2, current source/JD binding, independent review, shared Markdown/DOCX/PDF content, adversarial regressions | Implemented with conservative single-fact statements; optional real-converter CI is a separate gate |
| Fast preparation | Candidate-local evidence revisions/role sets, reviewed variant cache, dependency graph, bounded drafting/render selection | Pending; no permission or review cache introduced |
| Fast retrieval | Reuse Firecrawl, progressively consume results with bounded downstream queues; TinyFish only where supported | Existing Firecrawl increments retained; progressive end-to-end pipeline and TinyFish pending |
| Fast execution | Validated origin/tenant/form plans, compact bridge traversal, controlled session reuse | Pending; existing one pending action/coordinator preserved |
| Release comparison | Frozen 3-candidate/12-JD cohort, held-out/blind editorial comparison, equivalent complete rendered packages | Corpus added; full comparative evaluation pending |

The first intervention fixes the quality bottleneck: the previous renderer only
consumed exact selected quotes, regardless of a richer external rewrite. V2
imports actual wording and blocks unreviewed content at render/handoff. A combined
import plus fresh review packet removes one CLI startup without omitting checks.
This is not a complete-pipeline or live-application speed claim.

Subsequent work must measure generation/converter/PDF/page stages separately,
then optimize the largest observed stage. Do not infer that concurrency or a cache
will help. Keep the stdlib core, optional renderer dependencies, single SQLite
writer, no transactions over remote calls and sequential application coordinator.

Candidate working sets must retain original quotes/locators and scope; they are
indexes, never new evidence. Cache keys must bind candidate workspace, evidence
revision, exact JD, language, prompt/schema/configuration and review policy.
Rendering reuse additionally binds layout/font/converter versions and bytes.
Changed dependencies invalidate affected derivations; disclosure checks stay
fresh. No approval is cached.

Future balanced profile hypothesis: extraction 4, per-domain 1, public interaction
1, drafting 2, renderer 1, mutations 1; bounded queue depth and downstream
backpressure are required before enabling it. This configuration is **not yet an
implemented scheduler**. Unknown costs remain unknown; no paid top-ups.

Stop here after the complete wording/review/render-consumption slice. Do not
leave speculative queues, caches or form-plan modules half implemented.
