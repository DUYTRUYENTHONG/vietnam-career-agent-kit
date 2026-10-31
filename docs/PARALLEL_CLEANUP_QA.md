# Parallel cleanup QA

Scope: the Python parallel execution runner on the Windows development host,
using fictional applications and bridge callbacks. No employer account,
candidate document, paid model or live browser provider was used.

## Problem and resulting behavior

Previously, processing a confirmed application synchronously waited for tab
cleanup. A slow close held coordinator receipt processing and the next action
of another application lane. Cleanup now uses a separate bounded worker pool;
the coordinator continues to validate and record application receipts.

The default is one cleanup worker. Existing bridges retain serialized closes;
only bridges verified for concurrent independent closes should opt into a larger
`cleanup_workers` value, bounded by the approved application worker count.

## Behavioral evidence

The first event-based regression failed against the old synchronous runner:
lane two could not reach verification while lane one's cleanup was waiting for
that event. It passed after cleanup dispatch moved out of that critical path.
The event ordering is the acceptance signal, not a wall-clock speedup estimate.

Six focused regressions pass on the final implementation:

| Scenario | Required observed result |
|---|---|
| Slow confirmed close | Another lane verifies without waiting for the close |
| Timeout and late close reply | Submission stays confirmed; cleanup is quarantined; late reply is ignored |
| Restart after unknown close | Durable intent prevents automatic replay; an actual observed receipt reconciles it |
| Wrong binding in receipt | No cleanup acknowledgment is recorded |
| Two opted-in cleanup workers | Callbacks overlap; all application and cleanup writes stay on the coordinator |
| Invalid worker capacity or changed confirmation evidence | Dispatch or acknowledgment is rejected; existing confirmation is preserved |

Final focused command:

```sh
python -m unittest discover -s tests -p test_parallel_cleanup_progress.py -v
```

Observed: six tests passed in 29.831 seconds. This duration includes fictional
workflow setup and local validation. It does not measure live applications per
hour, model usage, provider limits or ten independent native browser sessions.

## Recovery and review

An exclusive private intent is persisted before each optional close callback.
The callback receives a copy; the coordinator validates request, bridge and
binding identities against the original request. A returned result is not
accepted after its deadline. Daemon worker timeouts do not prove remote
termination or cancel a browser operation.

The maintainer self-review covered correctness, module boundaries, source and
binding checks, single-writer behavior, bounded callbacks, and compatibility.
It is not independent peer review. There are no new dependencies, model calls,
database migrations, CLI flags or disclosure permissions.

The complete standard-library suite passed: **380 tests in 677.233 seconds**
on the same Windows development host. Adapter synchronization, the bounded
public-source checker, `git diff --check` and the disposable fictional demo also
passed. Protected PR checks remain separate publication gates. See
[parallel execution](PARALLEL_APPLICATIONS.md) for host setup and reconciliation;
passing these fictional tests does not authorize or certify a live provider.
