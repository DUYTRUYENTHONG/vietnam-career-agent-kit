# Measured application throughput

For a target of 100 qualifying confirmations per rolling hour:

```sh
python scripts/kit.py --data-dir ../career-private throughput --target 100 --window-minutes 60
```

The read-only result reports the exact UTC window, qualifying count, remaining
count, other-fit confirmations, confirmations without frozen fit, and
`target_met`. A rolling 60-minute window means `(now - 60 minutes, now]`. The
recorded confirmation time is used, not the time the submit button was clicked.
`observed_per_hour` normalizes the measured count over the requested window; it
is not a prediction. Fifty confirmations in 30 minutes do not meet a target of
100 confirmations in that window.

Only unique `execution_submissions` records with an immutable snapshot containing
`fit_classification` of **Strong fit** or **Plausible fit** qualify. The engine
freezes the already assessed, source-bound draft classification before issuing
submit and retains it with the confirmation. The original fit assessment still
requires evidence review; the KPI does not independently verify suitability or
employer acceptance. Attempts, drafts, uncertain outcomes and user-reported prior
applications are excluded. Stretch/unclear/ineligible classifications are shown
separately. Historical snapshots lacking frozen fit remain unrecorded for fit;
the report never infers or rewrites their classification to inflate a KPI.

This is a ledger projection: it checks snapshot integrity but does not reread
artifact files, contact employers or authorize actions. An old workspace without
schema 3 needs compatible additive initialization. Legacy campaign databases are
not automatically imported, migrated or combined. The total campaign tracker and
the rolling KPI measure different things.

## Execution budget

100 confirmations per hour requires an average of **36 seconds per qualifying
application**, including the work inside the measured window. Discovery, fit,
tailoring, rendering, page review, required answers, browser steps and employer
response time all consume capacity if performed during that window. A local
validation benchmark alone cannot establish that capacity.

Use small, exact finite batches (start with 5–10 already reviewed jobs), measure
their gate/form/confirmation times, and adjust the next batch from the evidence.
All-entry freshness checks remain mandatory, so the same action in a 100-entry
manifest costs much more than in a 5-entry manifest. Across an N-job campaign
with batch size B, the six-phase protocol performs approximately `10 × N × B`
entry validations for request issuance and immediate action preflight, plus
startup and other bookkeeping. This is an operation-count model, not measured
employer throughput. Previously submitted entries still retain their historical
validation rules.

Prepare independent research and documents before browser execution when
possible; keep one canonical writer and a supported host browser operator. Reuse
the existing valid exact scope. Smaller batches do not grant approval for jobs
outside that scope, eliminate host confirmations or permit replaying a pending
submit. Missing answers, challenges, new agreements and unknown outcomes still
need their existing handling. There is no standalone background worker or
verified employer adapter in this release.

Report actual `target_met` with the tracker after each pass. Keep the campaign
goal active while the target remains unmet. Neither the kit nor a user-specified
KPI can guarantee that enough suitable live vacancies or sufficiently fast
permitted employer forms will exist. See [local measurements](PERFORMANCE.md) and
[model/context efficiency](MODEL_ROUTING.md).
