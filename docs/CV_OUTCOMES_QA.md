# CV outcome feedback QA — 31 October 2026

Scope: portable local CLI, core and optional career MCP; fictional candidates,
mock rendering and local evidence files. No real account, employer application,
mailbox, paid model or candidate training data used for product QA.
Local runtime: Windows, Python 3.12.14 and SQLite 3.53.1.

## Observed checks

- Complete local standard-library suite: **360 tests passed in 768.929 seconds**.
  That run loaded the feature before the final bounds regression was added.
  The final focused suite below covers the correction; the extra malformed-CLI
  assertion also passed separately in 4.466 seconds.

- Final focused core/CLI suite: **12 tests passed in 48.042 seconds**, including
  the corrected bounds regression. The final real MCP stdio rerun passed one
  test in 7.044 seconds. No dependency or provider was added.

- Eleven focused core/CLI tests passed before the final timestamp-size correction.
  They exercise actual engine-created fictional confirmation snapshots, repeated
  messages, explicit retractions, CV grouping/cohort denominators, source changes,
  historical CV-file changes, chronology, cross-application rejection, unsupported
  schema/feature versions and real CLI subprocess import/report.
- A consolidated read-only review found one input/write/read size mismatch:
  Python accepted long fractional timestamps that could exceed the report's
  event bound. A valid padded-timestamp regression first failed, then passed
  after timestamp and final serialized UTF-8 bounds were added before writes.
  The regression also rejects an oversized Unicode path without creating history.
  The reviewer inspected the focused fix and confirmed the reported gap closed.
- Real hash-locked MCP stdio: one test passed in 5.603 seconds. It checks the
  two tool names/annotations, empty confirmed report and invalid-observation
  envelope using an explicitly initialized fictional portable workspace.
- Repository hygiene: 312 UTF-8 sources and ten canonical skill/wrapper sets
  passed; wrapper synchronization and diff whitespace checks passed.

All six app-pinned protected-branch checks are required on the final PR head
before merge. See [PR #35 checks](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/35/checks)
for current exact-head Linux/Windows Python 3.11/3.12, document and local-plugin
results. A pushed or draft branch is not a merged/released feature.

## Limits that tests do not close

Labels and source provenance are caller-supplied; hashing does not authenticate
an employer or establish the meaning of a message. Extra confirmations in the
cohort test are explicitly seeded frozen fictional records; this is aggregation
coverage, not proof of another real submission. The feature supports portable
execution schema 3–6 and does not migrate the earlier legacy campaign database.

The report is a SQLite read snapshot followed by bounded source checks, not an
atomic filesystem snapshot. A source is checked once per path/hash per report;
later edits are found on subsequent reports. Unavailable evidence is excluded
from evidenced numerators. A recorded retraction conservatively suppresses the
original classification even if its proof later becomes unavailable.

No live inbox audit, hiring-rate uplift, causal inference, comparative model
quality, native host installation, training run or model promotion is claimed.
This slice does not consume outcomes as training examples or change any facts,
CV wording, application authority, counts or execution transitions.
