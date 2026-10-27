# TinyFish runtime QA and performance evidence

Environment: Windows, Python 3.12.14. Maintainer fixtures only; no candidate data,
employer submission, live TinyFish request, paid model or optional-client install.

## Release checks

- Full standard suite: 255 tests passed in 392.925 seconds.
- After the final redirect/connection refinement: seven focused form regressions
  passed, including response-stage 307 rejection and reuse of one CDP connection.
- Final deadline/parallel suite: 13 tests passed, including an expired run's
  read-only verification, retained unique attempt, quarantined stall and a late
  completed result that must not be committed.
- Final TinyFish bridge suite: nine tests passed after the last bridge refinement.
- Repository source/skill hygiene: passed, 207 UTF-8 source files.
- Generated adapters: synchronized; inactive/global settings unchanged.
- Fictional preparation demo, CLI help/preview and changed Markdown links/fences:
  passed. QA preflight found zero conflict markers or suspicious patterns.
- Independent bounded review initially found origin interception, form drift,
  expired verification and upload MIME defects. All were fixed and rechecked;
  the final review reported no remaining required defect in its scope.

No native provider/CDP acceptance is claimed. CI state is reported separately in
the GitHub PR. Status: PASS_WITH_RISK for an explicitly experimental adapter;
not acceptance of unattended general-ATS or live throughput claims.

## Measured fixture timing

Command: `python scripts/benchmark_parallel.py --jobs 10 --latency-ms 100`.
One sample, run alongside the full QA suite; preparation excluded. The fake
bridge exercises the real coordinator and ledger, not the TinyFish adapter.

| Workers | Seconds | Peak concurrent calls | Calls | Attempts | Confirmed fixture receipts |
|---|---:|---:|---:|---:|---:|
| 1 | 46.475 | 1 | 60 | 10 | 10 |
| 10 | 42.782 | 3 | 60 | 10 | 10 |

Observed ratio: 1.086. This loaded single sample does not establish a before/after
improvement or live rate. Short simulated I/O leaves canonical validation and
coordinator overhead significant; configuring ten slots does not guarantee ten
active calls. Provider creation latency, eligibility, rendering/review and real
portal behavior are absent. Do not extrapolate to applications/hour or cost.

The concrete runtime gains are bounded return on stalled callbacks, continued
independent lanes, and one persistent CDP connection per job instead of a new
connection for every action. Connection reuse is regression-tested; its live
latency benefit is unmeasured. Provider account capability, controlled native
tests and separate stage timing remain necessary before increasing concurrency.
