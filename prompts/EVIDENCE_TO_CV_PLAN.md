# Evidence retrieval → requirement review → CV plan

Consumer: host career agent; optional generation consumer: pinned Qwen3.5-4B.
Use the current job-seeker policy and exact disclosure controls. This prompt
does not authorize a cloud upload, training, model promotion or application.

1. Select one vacancy and its complete captured requirements. Identify mandatory
   versus preferred conditions from the advert; never infer an experience count,
   salary basis, work authorization or proficiency from keywords.
2. Use confirmed source-bound experience atoms with contribution, scope and
   qualifiers. Retrieve candidates using `scripts/cv_plan.py prepare`. A retrieval
   score measures text overlap, not truth, semantic relevance or candidate fit.
3. Review every requirement against the full evidence pool, not only top-K.
   First-layer AI reviewer roles may propose concerns using CV_REVIEW_AGENTS.md;
   capture them as model proposals, never human answers or independent gold.
   Complete actual human matching review: demonstrated, partial, missing or unknown;
   cite supported facts and explain the decision. A missing retrieval hit is not
   proof that the candidate lacks the skill. Keep partial experience partial.
   Each cited fact must individually support its assigned coverage status; do
   not turn a collection of partial alternatives into full coverage.
4. Build a bounded content plan using the reviewed matrix. Select strongest relevant
   evidence and preserve all mandatory gaps, including budget omissions. The
   plan contains exact source statements; it is not a new master CV or approval.
   Group selected statements under their recorded employer/project scope and
   preserve employment chronology; retrieval rank is not a chronology order.
5. Draft only inside selected evidence budgets. Describe supported action,
   system, method and validation. Never add tools, metrics, tenure, ownership,
   production scale or mastery from the job description. Keep dates and material
   qualifiers. Full CV chronology and rendered pages require their normal reviews.
6. Benchmark retrieval against frozen human annotations first. Then compare full
   evidence with top-K using identical model, system prompt, cases and decoding.
   Keep missing/invalid generations in the denominator. Do not use gold to retrieve.
7. Inspect only development failures while changing retrieval settings. Freeze the
   selected setting before the final test. Do not train until reviewed targets,
   split review and free-compute budget/runtime checks pass. Compare an adapter
   against the improved base with the same retrieval; never merge both changes
   into one unexplained quality gain.
8. Keep actual outputs, token/timing observations, reviewer decisions and source
   hashes private. Report evidence retrieval, semantic writing, document quality
   and recruiter outcomes separately. No scores imply hiring probability.
