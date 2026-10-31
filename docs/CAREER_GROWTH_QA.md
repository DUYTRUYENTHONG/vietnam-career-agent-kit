# Career-growth feature QA

Scope: standard-library gap capture, private planning/review/evidence sidecars,
reviewed growth datasets, CLI/MCP transports and offline trainer preparation.
Only fictional workspaces and local resources were used for product QA.

## Local checks — Windows, Python 3.12

- Full standard-library suite: **349 passed**, 752.603 seconds, using
  `python -m unittest discover -s tests -v`.
- `test_career_growth.py`: **12 passed**, 17.215 seconds. Covers current source
  bindings, changed assessments with unchanged profile/JD, unknown versus missing,
  work-permit routing, unreadable-plan prevention, bounded altered-file reads,
  grouped splits, review requirements, workspace escape and no fact promotion.
- `test_growth_cli.py`: **8 passed**, 3.359 seconds. Includes real subprocess
  context/capture/assessment integration and mocked tool dispatch/failure handling.
- Existing `test_hooks.py`: **6 passed**, 0.029 seconds. Reminders retain control
  denial, approval invalidation and no transcript/background work.
- Existing `test_local_finetuning.py`: **8 passed**, 1.706 seconds after adding
  explicit task validation. Current growth tests additionally validate a reviewed
  two-group export through trainer preparation and reject a mismatched default task.
- Real hash-locked MCP stdio smoke: **1 passed**, 5.270 seconds. Discovers the
  added tools, checks annotations, retrieves gap context and captures a private
  snapshot; no account/provider/model requests.
- Source hygiene, generated-wrapper synchronization, fictional preparation demo
  and `git diff --check`: passed. The source checker is a bounded hygiene check,
  not a full privacy/security audit. CI status is recorded separately on GitHub.

## Consolidated review and fixes

One bounded read-only review identified three issues, fixed before publication:

1. Cap persisted growth JSON at 2 MB before creating a path, matching the normal
   private JSON reader; do not write plans that cannot later be reviewed.
2. Bound altered dataset reads by the exact expected byte length plus one.
3. Normalize common work-permit, eligibility and licence field aliases so these
   conditions require clarification rather than being treated as a project.

Regression tests cover all three and transitive overlapping-job split isolation.
The reviewer verified those deltas without accessing candidate workspaces or
rerunning the full suite. No unresolved concrete finding remained in that scope.

## What this does not establish

- No new growth-model training run, paired generated-plan quality measurement,
  learning-speed improvement, expertise gain or employment outcome was measured.
- A fake model config in a boundary test validates preparation only; no model
  weights were loaded there. Optional real training remains an explicit offline
  operation with base loss comparison and later task-quality review.
- Reviewer names and independence are caller-declared, not authenticated.
- A captured file hash proves bytes, not authorship, completion or expertise.
- Logical coach roles and native hook discovery/enforcement are instruction-only;
  no agent/global hook was installed. MCP smoke is not native host acceptance.
- Portable schemas 1–6 are supported; older campaign databases are not migrated
  and no competing tracker is initialized. Candidate facts/application state and
  execution authority remain unchanged by growth commands.

No new dependency, provider, copied external source or licence obligation was
introduced. New code/guidance uses the repository's existing MIT terms and keeps
DUYTRUYENTHONG attribution.
