# Check recorded lead identities before import

`check-lead-identities` compares 1–50 explicitly supplied public lead identities
against one read-only snapshot of the selected portable workspace's existing
tracker. Use it before importing JDs, opening forms or generating CVs to surface
work that may already have been assessed, closed or attempted. It does not decide
that a lead is a duplicate, current, suitable or authorized.

```console
python scripts/kit.py --data-dir ../my-private-workspace check-lead-identities --file ../my-private-workspace/leads.json
```

The versioned input contract is
[`lead-identities.schema.json`](../schemas/lead-identities.schema.json); see the
[fictional packet](../examples/fictional/lead-identities.json). Each lead has a
unique caller-selected `id`, `platform`, `platform_job_id`, `employer`, `req_id`,
`title`, `city` and exact HTTPS `url`. Unknown identity fields may be empty strings
except `id` and `url`. Never invent an employer, requisition, remote eligibility
or provider ID from a board label. Input IDs must be unique; other fields may
repeat because two discovered leads can describe the same post.

This is a separate input from Greenhouse/Ashby discovery output. The host must
select relevant leads and supply known identity fields; feed results are not
silently imported or sent to a model. Existing `duplicate-candidates --job-id`
remains available after import.

The normal outcome envelope returns ordered `leads` with `candidates` and
`requires_identity_review`, plus checked/matched/unmatched counts. Candidates
include recorded job metadata, state, liveness and these signals:

| Signal | Comparison |
|---|---|
| `same_platform_job_id` | Both nonblank provider fields exactly match |
| `same_employer_requisition` | Normalized nonblank employer and exact nonblank requisition match |
| `same_url` | Exact stored URL matches, including its query string |
| `same_employer_title_city` | Nonblank normalized employer/title/city match |

Previously confirmed, candidate-reported or uncertain attempts are marked
`prior_attempt_needs_reconciliation`. Closed records remain visible. No match
clears a job for submission: aliases, changed URLs, different requisition formats,
email history and external portals may still conceal an earlier application.
The flag reflects those recorded job states only; execution-intent tables and
receipt artifacts are not inspected, so false does not establish no prior attempt.
`deduplication_complete` and `external_history_checked` always remain false.
Different roles can share URLs or titles; review actual identities and receipts.

The whole input is validated before opening SQLite. Missing workspaces are not
created. The command opens only the chosen database with SQLite `mode=ro`, reads
job metadata once and returns hints; it does not inspect CVs, source artifacts,
profiles, credentials or approvals. Input/output stay private, as tracker metadata
may describe a user's search. There are no network/model calls, imported jobs,
events, count changes, retries, authority grants or schema migrations.

Invalid shape/version, duplicate input IDs, unsafe URLs, excessive field lengths
or a batch outside 1–50 returns `needs_input`. SQLite failures remain `failed`;
they are not empty success or proof that no earlier application exists. Keep the
selected workspace and resolve access/lock/schema problems before proceeding.

**Experimental:** fictional tests cover exact and partial identities, employer
boundaries, prior uncertainty, missing and separate workspaces, invalid inputs,
unchanged records, CLI outcomes and one read-only SELECT for 50 leads. This is
not semantic deduplication, a discovery cache, live employer acceptance, a native
browser integration or a measured application/token speedup. Legacy private
campaigns require their existing owner/API; do not initialize or migrate a
second tracker to use this portable command.

## Observed local lookup workload

Five alternating runs on 3 November 2026 used 500 fictional stored jobs and the
same 50 incoming identities. One batch had a median **69.639 ms**; 50 separate
in-process calls to the same new method had a median **801.891 ms**. Every
returned candidate list was identical and the database hash stayed unchanged.
Raw batch times were 81.006, 81.057, 69.639, 64.767 and 66.501 ms; separate-call
times were 810.475, 1114.062, 743.799, 801.891 and 756.117 ms (`perf_counter`).
This compares local call batching, not the previous application system, model
usage, Internet latency or end-to-end submissions. It establishes no application
rate, token/cost saving or hiring improvement; results vary by workspace/host.
