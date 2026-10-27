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

Measured handoff results and final command/CI outcomes follow below.
Full current/provider-only/evidence-reuse/pipeline comparison
of equivalent complete reviewed rendered packages, blind editorial comparison,
cost evaluation and live-provider/browser testing remain **pending**, as tracked
in QUALITY_FAST_PLAN.md. This checkpoint is the complete offline wording/review/
render-consumption slice, not completion of all six enhancement increments.

## Completed measurements

Implementation commit: `a8220e04abba636c9aae3d705c7fc9f995e2327b`.
Code/fixture fingerprint (paths and SHA256s in raw report):
`d913c4b864007c1aaa5cfa0212dbbd3d04e6338421a5e1364508fb48f6059c58`.
No suites ran during timing. Each wording sample used a fresh equivalent
workspace, alternated mode order, and asserted an identical complete review
packet digest for the same candidate. This is not a cold OS-cache experiment.
The three candidate workloads were frozen, not selected for easy form filling.

```sh
python scripts/benchmark_pipeline.py --jobs 100 --samples 7
python scripts/benchmark_wording.py --samples 7
```

| Review-ready import + packet | CLI starts | Completed-run median ms | Range ms |
|---|---|---|---|
| Separate commands | 2 | 710.513 | 599.595–813.782 |
| Combined command, same fresh validations | 1 | 446.410 | 372.101–807.994 |

Seven samples per candidate per mode (21 observations per mode), Windows,
Python 3.12.14. Per-candidate medians, separate → combined: data 710.513 →
420.043 ms; technical 668.106 → 457.602 ms; commercial 713.970 → 446.410 ms.
The completed-run pooled median fell 37.2%; ranges overlap. This measures only
deterministic import and review-packet handoff, excluding setup, semantic review,
rendering, human wait and application execution. No tokens/cost benefit is inferred.
The combined path was faster in 19 of 21 paired observations; two combined
observations were slower. All 42 completed packets passed identical-digest checks.

An earlier seven-sample run aborted on a 30-second local combined-command
subprocess timeout. Its partial timings were not recoverable as an aggregate
and were excluded. The cause is unconfirmed; no credentials/network were involved.
One isolated diagnostic passed, then one fresh bounded full cohort completed.
The failure is recorded in the raw report and limits robustness claims: do not
interpret the completed-run median as a worst-case latency guarantee. Keep the
transport composition for its verified 2 → 1 starts and equivalent checks;
further runtime reliability investigation is warranted if this recurs.

The required 100-job legacy benchmark ran at baseline and enhanced revisions,
seven samples each. Selected content medians 59.727 → 60.267 ms with exactly two
JD reads; full resume 1421.209 → 1447.840 ms with 100 reads; tracker 7.499 →
4.455 ms with zero reads. These unchanged paths establish **no speedup claim**;
raw samples/ranges are retained rather than interpreting machine-load variation.

## Real rendering and release checks

- Final local standard suite: **203 passed, 330.490 seconds**; clean baseline
  185 passed. These suite durations are not a performance comparison.
- Repository hygiene: 173 UTF-8 files at the implementation checkpoint, ten
  canonical skills; generated adapters, compile checks and fictional v1/v2 demos
  passed. No active/global hooks or settings changed.
- [Push CI run 39769610258](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/actions/runs/39769610258)
  at a8220e0 passed all four Ubuntu/Windows Python 3.11/3.12 jobs (**203 tests
  each**) and the optional real document job (**7 tests, 9.041 seconds**).
- LibreOffice **24.2.7.2**, actual locked Python document tools and embedded
  DejaVu Sans produced all three new v2 DOCX/PDF/PNG sets. Downloaded file/page
  hashes and PDF text/font checks were revalidated. Every new v2 page (three
  one-page fixtures) was visually inspected: readable sections, preserved context
  and qualifiers, no observed clipping, overlap or missing glyphs. This is a
  visual inspection, not blind editorial scoring or a real-user CV review.
- Duplicate PR run 39769692686 was cancelled; its standard jobs passed and its
  document job was cancelled. The complete push run above supplies the full
  passing implementation evidence; the cancelled run is not called successful.

Among the three real v2 render measurements, converter startup+conversion was
largest: median **838.882 ms**, range **812.177–852.850**. Version-inventory startup
median 64.626 ms; DOCX generation/reopen 28.283 ms; PDF/font verification 5.875 ms;
page images 38.433 ms. Sample size is three, one per fictional profile, **not**
seven per profile or an end-to-end package benchmark. No tail percentile or
converter-pool benefit is claimed. Preserve one isolated converter and PDFium
locking; evaluate any process reuse as a separately measured isolation change.

[Raw cohort, hashes, timing samples and CI provenance](benchmarks/quality-wording-20261022.json)
retain both the failed run summary and completed observations. No live application
was made and no personal campaign state was read or modified during development.

## Consolidated implementation review

One bounded maintainer review covered correctness (binding, qualifier/scope and
invalidation regressions), readability (one wording module and explicit states),
architecture (existing canonical writer/stdlib/optional boundaries), security
(private-path/size limits, no new external disclosure or approval bypass) and
performance (equivalent checks, observed startup reduction, retained timeout).
A racing superseded-review issue was corrected and regression-tested before
the implementation commit. No remaining material issue was found in this slice.
This is not an authenticated external peer review or proof that arbitrary agent
rewrites are correct; the factual-review and native-host trust boundaries above
remain effective.
