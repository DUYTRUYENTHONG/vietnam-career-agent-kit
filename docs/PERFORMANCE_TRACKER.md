# Model execution and token tracker

Record actual observations from your own host/provider exports. The kit does
not see Codex/Claude subscription usage automatically, call a second model,
estimate tokens from characters, infer a model ID or calculate a price from a
model name. Unknown values stay `null`, distinct from an observed zero.

## Record and report

1. Initialize/select your existing external private workspace.
2. Save a small source artifact from the host/provider in that workspace. Avoid
   credentials and raw prompts; retain only the evidence needed for usage review.
3. Prepare one [versioned observation](../schemas/performance.schema.json), using
   the exact reported model/effort and a stable observation ID. Bind the source
   file's actual SHA256. The [fictional template](../templates/performance.example.json)
   needs your real values and hash; its sample numbers are not measured usage.

```sh
python scripts/kit.py --data-dir ../my-career-private performance-record --file ../my-career-private/observations/call-1.json
python scripts/kit.py --data-dir ../my-career-private performance-report
python scripts/kit.py --data-dir ../my-career-private performance-report --phase generation --format md --output reports/performance/run-1.md
python scripts/kit.py --data-dir ../my-career-private performance-report --format csv --output reports/performance/run-1.csv
```

Choose new snapshot names; existing reports are not overwritten. Exports are
restricted to `reports/performance/`, so they cannot replace the workflow database
or a CV/source file elsewhere. JSON without `--output` returns the normal CLI
outcome envelope. `--model-id`, `--phase` and `--workload-id` filter reports.

## Whole agent turns versus model calls

Choose the unit your source actually measures:

| `measurement_scope` | `usage.kind` | Duration includes |
|---|---|---|
| `model_call` (default for legacy observations) | `per_call` | One model call as reported by the source |
| `agent_turn` | `per_turn` | The whole host turn, including tools, waits and orchestration |

For an explicitly measured whole turn, add `"measurement_scope": "agent_turn"`
and set `usage.kind` to `per_turn`. Set every token field and `cost` to `null`
when the host exposes only duration. A completed turn can have `accepted: false`
when its output has not passed QA. A configured model ID is caller-reported
metadata, not an authenticated provider record; use `null` if it is unknown.

The report groups these scopes separately even when model, phase and workload
match. Markdown and CSV include the scope. Never add a turn's usage/charges to
its constituent calls: they may describe the same work twice. Summed parallel
turn durations are worker time, not elapsed campaign time. This importer does
not extract native chat telemetry, dispatch chats or prove faster submissions.

## Interpret the table

- Compare the same provider/model/effort, phase, workload and measurement scope. Different tasks or
  quality standards are not a fair model benchmark. Acceptance is caller-reported,
  not an independent quality review.
- p50 is the median measured duration; p95 uses nearest rank. Missing duration
  observations are counted. Summed overlapping calls are not campaign wall time.
- Known token sums include only provided measurements, with known/missing counts.
  Input includes cached input; output includes reasoning in this normalized
  contract. Those subsets are displayed separately and never added twice.
- The importer rejects cumulative counters and scope/unit mismatches. Normalize an
  explicit export before importing; do not guess deltas across resets/models.
- Charges must be observed decimal amounts with currency. Currencies are kept
  separate; there is no implicit conversion, rate card or dollar-saving claim.
  API spending is not a measure of a subscription's remaining quota.
- A source hash proves the selected bytes at import, not who produced them or
  that their claims are true. Reports preserve historical values and do not
  silently reread or authenticate a changed/deleted source.

## Storage and limits

Observations are opt-in append-only records in the same private `workflow.sqlite3`.
Application schema remains 1–6; the optional performance tables have their own
format version 1 for call-only history. Importing an agent turn advances only
the performance feature marker to version 2, within the same transaction as
the new immutable record. Old performance readers then stop rather than mix
turns with calls. This reader supports versions 1 and 2; existing event bytes,
IDs and fingerprints remain unchanged. Older compatible application operations
leave those tables alone. Unknown feature/application versions block this
reader/writer. Upgrade the kit before reading a workspace containing turns;
do not reset its marker or remove observations to run an older reader.

Reimporting an identical event ID/content is idempotent. Reusing an ID for changed
content fails. No candidate/profile, approval, job or submission is created by
recording telemetry. Source artifacts must be inside the selected workspace,
nonempty and at most 1 MB. Reports are bounded to 10,000 observations; use filters
for a larger history. Keep measurements and exports out of public Git.

## Local QA

```sh
python -m unittest tests.test_performance -v
python -m unittest discover -s tests -v
python scripts/check_repository.py
```

The fictional regressions exercise a real CLI import, mixed scopes with matching
model/workload, unavailable usage, unchanged legacy reimports, invalid unit pairs
and export labels. They do not certify a host's telemetry or an employer portal.

## CI overhead

Before this change, head `b33056a` ran the same six jobs on both
[branch push](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/actions/runs/40453198636)
and [PR creation](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/actions/runs/40453242853).
The workflow now runs on every PR, pushes to `main`, and explicit manual dispatch.
It removes the duplicate feature-branch push run. All six required job names,
test commands, matrix entries, assertions and branch-protection rules are retained.
This is a trigger change, not evidence of lower model usage or a dollar saving.
