# Faster preparation and execution

## Combined launch measurement, 22 October 2026

`python scripts/benchmark_launch.py --samples 7` compares the existing
authorize-manifest/start-execution/next-action CLI sequence with launch-execution.
Each sample uses a fresh equivalent single-job fictional workspace, approved
standing scope and mock renderer; setup is outside timing. Order alternates.
The full unit suite finished before this benchmark. Windows, Python 3.12.14;
elapsed milliseconds include subprocess startup and the same authorization,
start and initial-inspection checks, with no model/network/browser measurement.

| Path | CLI calls | Median ms | Range ms |
|---|---|---|---|
| Separate commands | 3 | 1017.035 | 850.130–1835.182 |
| Combined launch | 1 | 537.829 | 514.023–657.884 |

The measured median fell 47.1%, with nonoverlapping sample ranges. Keep the
composition: it removes transport overhead while preserving durable allocation,
run creation, fresh checks and interruption reconciliation. Machine load varies;
this is local launch latency, not application completion speed. The benchmark
asserts first-action inspection and zero submission attempts. Five behavioral
launch tests additionally cover partial failures, nonreplay and host blockers.
This establishes no token/cost saving or 100/hour employer throughput result.

For discovery bottlenecks, see [the primary-source workflow review](DISCOVERY_ACCELERATION.md).
Public bulk-list guidance remains instruction-only and has no measured speedup
or implemented network connector. Post-confirmation cleanup reduces open tabs,
but its browser latency has not been benchmarked.

## Earlier preparation measurements

Measured 21 October 2026 on Windows, Python 3.12.14. Standard-library core only;
no models, browser, employer service or real converter was timed.

## Measurements

`python scripts/benchmark_pipeline.py --jobs 100 --samples 7` creates and removes
an external fictional workspace. Each sample revalidates bytes; there is no warm
validation cache. Setup/import/assessment/draft creation is outside the timed
region. Baseline revision: d580ce5. Times are milliseconds.
The timing workspace has 100 prepared drafts and no renders or execution actions;
execution call counts use a separate single-job fake-converter CLI regression.

| Operation | Before median (range) | After median (range) | Deterministic work |
|---|---|---|---|
| One selected CV content model, 100 prepared jobs | 1044.398 (800.248–1636.510) | 48.209 (37.829–57.552) | JD reads: 101 → 2 |
| Full resume, unchanged semantics | 873.854 (788.913–1815.094) | 1113.636 (1059.642–1381.373) | 100 JD reads; no speed claim |
| Ledger-only tracker, new operation | — | 4.843 (3.981–6.030) | 0 JD/file reads; one database snapshot |
| Six-phase CLI execution, excluding setup/start | 19 calls | 13 calls | Initial next + six checks + six acknowledgements; acknowledgement now returns successor |

The selected-CV median improved approximately 21.7× in this run; ranges do not
overlap. Machine load affects timings. The tracker deliberately does less than
resume: it does **not** certify files, current approvals or live vacancy status.
The CLI call reduction is tested, not an end-to-end employer latency measurement.
Real conversion time, agent reasoning, browsing, challenges and employer responses
remain outside these numbers. No token, money, hiring or universal coverage claim.

## Architecture decision

Keep the local modular core and one canonical SQLite writer. A 100-job campaign
does not justify another service, queue broker, model API or browser fleet.

```mermaid
flowchart LR
  P[Confirmed facts + job evidence] --> J[Selected-job validation]
  J --> D[Tailored draft + rendered review]
  D --> M[Exact finite manifest]
  M --> E[Sequential execution coordinator]
  E --> C[Fresh action check]
  C --> B[Supported host browser]
  B --> A[Receipt + next request]
  A --> E
  E --> L[(Canonical SQLite)]
  L --> T[Fast tracker table]
```

1. **Validate the selected job on selected-job paths.** `job_checkpoint` and full
   resume share `draft_status`, preserving source/profile/JD/file checks. Rendering
   no longer scans all other drafts for each content check. A full manifest still
   validates all its entries; no permission or hash cache crosses action boundaries.
2. **Separate observation from authorization.** `tracker` uses a single SQLite
   read transaction and bounded table scans, without artifact I/O. It is safe for
   frequent catch-up output. Resume, content checks and check-action still gate
   actual work. Tracker output never grants permission to act.
3. **Combine transport calls, preserve durable steps.** `advance-execution`
   records a receipt, commits it, then requests one successor in a second
   transaction. Returning a submit request still reserves the unique attempt
   first. If the second step blocks, `receipt_recorded=true` preserves that fact.
   A lost response requires execution-status reconciliation, never replay.

Preparation can be reasoned about independently per job, while canonical writes
and browser submissions keep one coordinator. This change does not implement
parallel browser submissions or background workers. Research permission checks,
fresh UI inspection and candidate-only challenges stay at their existing boundary.

## Experiment ledger and regression guard

| Idea | Verdict | Evidence / trade-off |
|---|---|---|
| Replace all-job draft scan with selected-job validation | Kept | 101 → 2 JD reads; approximately 21.7× measured median improvement |
| Separate frequent status output from full resume | Kept as distinct read model | About 5 ms; explicitly does not validate artifacts |
| Combine receipt acknowledgement and successor issuance | Kept | 19 → 13 CLI calls in the real subprocess regression |
| Cache approval/file validation between browser actions | Rejected before implementation | Expiry, revocation and changed bytes must remain observable |
| Parallel browser writers / new distributed services | Deferred | No measured need; would complicate duplicate and interruption recovery |

Tests enforce selected-job-only reads, stale affected drafts, the 13-call loop,
immutable attempts, read-only tracker semantics and a lost combined response
before submit. CI uses deterministic work budgets rather than flaky wall-clock
thresholds. Re-run the benchmark when these paths change; a runtime-specific
browser benchmark is still required before claiming a faster live campaign.

Local verification: all 83 standard-library tests passed, including the real
subprocess loop and existing stale-source/approval/duplicate/recovery cases.
Repository hygiene and generated-wrapper synchronization passed. Optional real
conversion remains a separate Linux CI gate; no local LibreOffice run is claimed.

## Execution validation experiment, 21 October 2026

Reproducible command:

```sh
python scripts/benchmark_execution.py --jobs 100 --samples 7
python scripts/benchmark_execution.py --jobs 10 --samples 7
```

Python 3.12.14 on Windows; fictional jobs and a **mock renderer**. Setup,
rendering, review and approval are outside the timed region. No model, network,
browser, live application or real document converter is timed. Each timed sample
still runs full manifest validation. Timings are milliseconds.

| Workload | Baseline median (range) | Experiment median (range) | Decision |
|---|---|---|---|
| 100-entry check-manifest | 4474.023 (2442.255–6701.950) | 4477.160 (2980.021–5081.499) | Revert profile sharing: no timing gain |
| 100-entry check-action | 2107.154 (1622.352–4267.408) | 3517.190 (2633.276–6022.372) | Revert: slower median, broad overlapping variance |

The experiment shared one validated profile within a pass and reduced profile
validations from 201 to 2 while retaining 200 JD reads. That work-count reduction
did **not** establish a reliable latency improvement. Its production changes were
removed. Reference baseline was main at `73a77b7`, run in a detached disposable
worktree with the same benchmark script; the experiment followed sequentially.
An earlier run overlapped the test suite and is excluded from the comparison.
No speedup or token/cost saving is claimed from this rejected experiment.

The final implementation retains per-entry validation and adds a final
source/expiry/runtime recheck for long passes. Its separate **10-entry** operating
point measured:

| Operation | Median (range), ms | Profile validations | JD reads |
|---|---|---|---|
| check-manifest | 239.146 (236.155–255.462) | 22 | 20 |
| check-action | 155.628 (147.441–158.724) | 22 | 20 |

This is a different batch size, not a before/after speedup on identical work.
Use small finite batches as described in [THROUGHPUT.md](THROUGHPUT.md), measure
the actual host/employer steps, and preserve the same checks per manifest entry.
The [deterministic routing planner](MODEL_ROUTING.md) adds no model calls for
classification, tests or metrics. Its native host dispatch and token savings are
unmeasured. A 100/hour live KPI remains unverified; `throughput` reports actual
rolling qualifying confirmations rather than treating local benchmark capacity
as applications.
