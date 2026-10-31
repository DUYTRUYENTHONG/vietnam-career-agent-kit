---
name: application-tracking
description: Report and resume private applications and source-bound recruiter outcomes by submitted CV version, with explicit unknowns and duplicate protection.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Report and resume canonical private application state and source-bound recruiter
outcomes by submitted CV version, preserving unknowns and duplicate protection.

## Inputs

One selected workspace and existing canonical tracker; observed evidence or separately labelled candidate reports.

## Required capabilities

Local resume/report and SQLite schema 3. Execution records distinguish durable attempts, host-observed confirmations and unknown outcomes; host receipts are not independent employer verification.

## Steps

Use `research-report --fingerprint HASH` for saved provider tasks/evidence and
`research-status` only for explicit remote reconciliation. Keep research pending,
partial, failed and uncertain distinct from application states. A provider task,
captured page or normalized JD never increases the submitted count. Both paths
use one private workflow.sqlite3; never copy public-provider diagnostics to Git.

Read resume before continuing. Check current source/profile/JD/artifact fingerprints and prior applications. Keep prepared/approved/confirmed/user-reported/unknown distinct. Report exceptions/coverage and next action. Preserve submitted snapshots and never infer submission from a draft/upload/click.

For a campaign spanning batches, follow ../../../docs/campaign-continuity.md.
Keep a user-requested persistent goal and private checkpoint tied to the same
canonical ledger. Count only qualifying confirmed new submissions toward the
target; keep prior reports and uncertain attempts separate. A finished batch is
a checkpoint, not campaign completion. Continue independent authorized work past
blocked vacancies without widening execution scope or repeating final attempts.

## Outputs

When the user sets a rate KPI, also run throughput --target N --window-minutes M.
Read ../../../docs/THROUGHPUT.md. Report the actual rolling qualifying count and
target_met; never replace it with extrapolated speed, attempt counts or old
records lacking frozen fit. Keep the campaign goal active while its target is
unmet. A local benchmark does not prove live employer throughput.

Return a timestamped Markdown tracker table after every application pass, including
when the pass is blocked. Include employer/role, source URL, recorded status,
blocker, next step and last update. Link the complete private report for longer
campaigns. Keep host-observed confirmations, candidate-reported prior applications
and uncertain attempts separate; always distinguish prepared from submitted.
Report tab cleanup separately using cleanup_status/cleanup_blocker. A failed
close does not change the confirmed application, and successful closure is not
an application blocker. Only the browser-application workflow handles closure.

Use `tracker --format md --output reports/tracker.md` for fast catch-up output.
It is a ledger projection, not a content/approval/liveness check. Use resume and
the normal action checks before actual work. No visualization file is required
for a table. Never describe the tracker as a background employer-response monitor.

## Failure behavior

For model/workload optimization use the opt-in private `performance-record` and
`performance-report` commands ([contract and setup](../../../docs/PERFORMANCE_TRACKER.md)).
Record only observed per-call time/usage with a private source hash. Unknown
tokens/cost remain null; cached/reasoning tokens are subsets. Compare equivalent
accepted workloads, distinguish task durations from campaign wall time, and never
infer subscription quota or savings. Telemetry never changes submission counts.

Use ../../../docs/CV_OUTCOMES.md for explicit source-bound recruiter observations
after a portable-engine confirmed submission. Record the exact frozen submission
and CV hashes; classify acknowledgment, screening, assessment, interview and
rejection separately. Retractions correct a recorded classification without
rewriting history. Use age-scoped reports and explicit comparable job cohorts;
no response is not rejection, and a per-CV rate is not causal model uplift.
Missing/changed proof stays visible and outside evidenced numerators. These
records never train or promote a model automatically. Honor source-use restrictions.

Uncertain outcomes require reconciliation, not another final attempt. Changed/missing artifacts block handoff until reviewed.

## Side-effect limits

Local tracker/report only; no mailbox scan, withdrawal, scheduler or automatic cleanup.

## Tests and examples

python scripts/kit.py --data-dir PATH resume; tests/test_preparation.py and tests/test_kit.py.
