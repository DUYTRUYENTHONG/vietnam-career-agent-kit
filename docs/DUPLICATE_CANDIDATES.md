# Duplicate-candidate preflight

A vacancy can appear through different boards or changing page URLs. Before
creating another tailored package, inspect the selected private ledger:

```sh
python scripts/kit.py --data-dir ../my-private-career duplicate-candidates --job-id 12
```

The command reads one consistent SQLite snapshot, selecting other jobs with the
same normalized employer key or an identical stored URL. It returns candidates
with an identical stored URL even if the employer label, title or city differs,
or with the same employer and an equal normalized title and comparison city. City aliases use the existing
normalizer; title comparison ignores case, spacing and accents. It is not fuzzy
matching. Different employers are outside the search unless the stored URL is
identical. Other workspaces are always outside the search. URL matching is exact:
no redirect resolution, tracking-parameter removal or ATS-ID parsing is performed.

Each candidate includes its local ID, source IDs, employer label, requisition, URL, recorded state,
liveness and matching signals. Submitted, user-reported and uncertain records
remain visible even after closure, with `prior_attempt_needs_reconciliation`.
These are recorded states, not freshly validated receipts or vacancy status.

Use stable employer/source identifiers and saved receipts to resolve candidates.
Do not treat an opaque URL suffix as a verified requisition, strip arbitrary URL
parts into an identity, merge distinct requisitions, or retry an uncertain send.
Titles and URLs can be shared by genuinely different vacancies. The command
does not mutate jobs, approvals, events or counts, and does not block unrelated
work or confer submission authority. Unknown local IDs return `needs_input`.

`requires_identity_review` describes returned hints. `deduplication_complete` and
`external_history_checked` are always false: no hints cannot prove a job was never
applied for elsewhere. No profile, CV bytes, draft validation, network, model or
browser is accessed. This reduces redundant preparation, not employer form time;
no live applications-per-hour gain is measured.

Compatibility: additive CLI command on existing preparation schemas 1–4; no
migration or dependency. Seven fictional behavioral tests in
`tests/test_duplicates.py` cover alternate IDs, employer-label differences, uncertain/closed records,
workspace isolation, unchanged data/events, no artifact hashing and the real CLI.
