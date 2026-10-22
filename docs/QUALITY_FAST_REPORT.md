# Wording v2: bounded release evidence

Date: 22 October 2026. Baseline: `5d5e4f33ad1c49b1865e0506e39212ad926021b3`.
Checkout began clean. The baseline was rerun from an isolated detached worktree;
185 tests passed in 408.150 seconds. A preliminary run overlapping edits was
discarded as baseline evidence. Test-suite elapsed times are validation records,
not throughput comparisons; concurrent local work affects them.

## Practical bottleneck map

| Boundary | Evidence | Decision |
|---|---|---|
| Tailoring to rendered document | Baseline `Documents.content_model` reconstructs selected exact fact quotes; renderer ignores external Markdown rewrites | First fix: import and review actual v2 wording, then consume it in every output |
| Host-process handoff | Existing CLI starts a process per command; equivalent import/packet composition is measurable offline | Combine only transport; retain identical current-source and packet checks |
| Selected versus full-workspace reads | Existing PERFORMANCE.md records selected-job validation and full-resume costs | Reuse selected-job paths; no competing state store or validation cache |
| Public retrieval | Firecrawl v2 is implemented; earlier fixed-workload fake-transport benchmark exists | Reuse it. No paid key/live measurement; TinyFish remains unsupported |
| Rendering | Local LibreOffice unavailable | Add separate DOCX, converter inventory, conversion, PDF/font and page-image timings; use real optional CI |
| Browser traversal/application | Existing one coordinator/pending action; host/employer delays not measured here | No browser/session/form-plan or live-submission speed claim in this slice |
| Agent context/model usage | Host-internal token/call counts not observable | Report unavailable, never estimated as observed |

## Implemented and tested scope

V2 supports optional coherent sections, source-backed history groups, exact
identity/contact/target binding, single-fact faithful rewrites/translations,
requirement links, qualifier/entity/number alarms and independently recorded
statement review. Markdown, DOCX and PDF share the same ordered approved wording.
Legacy exact-claim mode remains available. New review/model/source/JD bytes
invalidate current dependent renders and manifests; historic snapshots stay
historic. Review identity/independence assertions are not authenticated.

The new deterministic cases include ownership/statistic/tool/degree/language
inflation, omitted prototype qualifiers, cross-employer source mixing, a semantic
overclaim that passes linkage but fails independent review, EN-to-VI qualifiers,
source/profile/JD/review drift, rejection, racing review, candidate isolation,
private CLI inputs, and invalidation of an exact previously approved manifest.

Three fictional candidate families are authored fixtures: commercial customer
solutions, technical automation and data analysis. No real candidate is used.
`quality-corpus.json` freezes twelve EN/VI JD cases including one duplicate, closed
and unverified roles, missing qualifications, ambiguous pay, location uncertainty
and an explicit employment-gap caution. Six cases are designated held out for
future drafting/editorial evaluation; deterministic policy tests exercise all
twelve, so they are not a hidden black-box benchmark. No model was tuned here.

The example rubric reviews in `demo_wording.py` are synthetic test assertions,
not blind editorial findings or proof of document quality. No guarantee of
interviews, ATS performance, best-in-class writing or 100 applications/hour.

## Metrics and limits

`core.metrics.Trace` uses monotonic `perf_counter_ns` differences. Local wording
and renderer stages record milliseconds and observed counts. The converter
startup and actual conversion share one process and are reported together; the
separate version-inventory process is measured independently. Failure timing is
available through Trace but failed rendering does not register a document set.
Human wait and host tokens/tool/model calls remain unavailable. Queue wait,
remote wait/backoff, browser sessions and render-cache reuse are not instrumented
as an end-to-end pipeline in this slice. No queue, provider call or reusable
permission cache was added.

Measured handoff results and final command/CI outcomes are appended below after
the release checks. Full current/provider-only/evidence-reuse/pipeline comparison
of equivalent complete reviewed rendered packages, blind editorial comparison,
cost evaluation and live-provider/browser testing remain **pending**, as tracked
in QUALITY_FAST_PLAN.md. This checkpoint is the complete offline wording/review/
render-consumption slice, not completion of all six enhancement increments.
