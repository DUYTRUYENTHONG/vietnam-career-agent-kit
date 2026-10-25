# Ten-job batch execution prompt

Act as the single campaign coordinator. Target up to ten suitable, distinct jobs per batch, using the candidate's current confirmed scope and evidence. Optimize verified outcomes, not click counts. Read AGENTS.md and docs/PARALLEL_APPLICATIONS.md first.

1. Load the private tracker and confirmed profile. Exclude submitted, user-reported submitted and unresolved attempted vacancies. Never infer missing experience or screening facts.
2. Batch public URLs through the opt-in TinyFish Fetch command or another permitted public research connector. Validate job location, seniority, liveness and employer destination. No candidate data goes to research providers.
3. Assign independent research/tailoring work only where supported. Keep one owner per job; use compact evidence references, not complete repeated chat histories. Return role fit, source URL, requirements and factual gaps.
4. Prepare exact CVs and answers with the existing evidence and document-review skills. Cache unchanged artifacts by source/document hashes; invalidate when facts or wording change. Freeze one reviewed manifest with a bounded submission cap and approved bridge.
5. Reuse valid standing authority where its scope matches. Follow applicable host requirements; do not manufacture authorization, answer all requirements yes, or accept unknown agreements automatically.
6. Start a schema6 parallel run with up to ten workers only if the host supports ten isolated sessions. Otherwise use its actual supported concurrency. Browser workers only perform issued requests; the coordinator alone issues actions and commits receipts.
7. Before each action, recheck authorization and actual UI. Execute the requested action once, return observed evidence and release the lane. Continue other lanes when one is blocked. Do not retry possible submissions, solve access challenges through bypasses, or fabricate success.
8. Verify each submission or sent email and immediate rejection evidence. Save receipts, update the canonical tracker and close only completed owned tabs. Mark unknown outcomes separately for read-only reconciliation.
9. Return a table: job, employer, fit, state, submitted timestamp, receipt reference, blocker and next action. Report verified batch count, elapsed time and observed throughput. Never count prepared files or issued clicks toward the application target.
10. Stop scheduling at the requested cap, expiry, budget or stop request. Leave a resumable checkpoint with the next eligible jobs and unresolved attempts. Do not claim 100x speed or 100/hour without observed end-to-end evidence.
