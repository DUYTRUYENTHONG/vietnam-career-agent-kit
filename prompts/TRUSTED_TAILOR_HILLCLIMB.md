# Real-evidence tailoring and evaluation workflow

Consumer: host job-seeking agent. Model experiment: pinned Qwen3.5-4B in the
optional benchmark runner. This prompt does not change the host model or grant
cloud, account, application, Git-publication or installation authority.

For retrieval and full-CV evidence selection, first use EVIDENCE_TO_CV_PLAN.md.
Compare retrieval as a separate fixed experiment with identical system prompts;
do not label a changed evidence context as a prompt-only improvement. The current
hill-climb recorder deliberately rejects retrieval reports.

1. Read the current application-tailoring skill and job-seeker policy. When the
   candidate requests evaluation before applying, record that disclosure hold
   privately. Preserve the canonical ledger and immutable submissions. Stop new
   applications until the requested comparison and document review are complete.
2. Diagnose recorded recruiter outcomes without inventing a response/admission
   rate. A receipt is not a successful screen. Do not infer that a model caused
   silence, or that an application used an experimental adapter without provenance.
3. Use only the explicitly selected candidate's reviewed facts and captured real
   job requirements. Keep reference CVs and aspirational keywords out of facts.
   Build the complete requirement map and select strongest relevant evidence
   before writing. Keep mandatory gaps in the private review and truthful answers.
4. Prepare the source-bound benchmark described in TRUSTED_TAILOR_BENCHMARK.md.
   Do not create human gold or mark AI suggestions independently reviewed. Resolve
   source/scope/family conflicts before freezing. Separate the bullet task from
   full-CV/layout checks and observed recruiting stages. Unknown stays unknown.
5. Select one fact per bullet. State action, named system/deliverable and supported
   method/check/result. Preserve contribution, assisted/prototype/local/synthetic
   scope, dates and metric units. Drop irrelevant repetition, unsupported mastery
   and keyword lists. Do not retain every master bullet as a tailoring requirement.
6. Start with the same frozen facts/JD under the existing base prompt and improved
   evidence-first prompt. A trained adapter must beat the improved base, not only
   a deliberately weak baseline. Use identical inputs, tokenizer, precision,
   decoding and budgets. Save raw output, tokens, timing and invalid generations.
7. Hill-climb only the reviewed development cohort. Record the failure example,
   one-variable hypothesis, focused diff, parent hash, comparison and actual spent
   time. Keep within the existing cumulative free-compute cap; no paid fallback,
   automatic retries or public/private data mixing. Never reduce source/factuality
   gates to obtain a higher score. Stop at budget, round or non-improvement limit.
8. Freeze the selected variant before the final test. Do not use test labels or
   outputs to tune another version. Blind actual human output reviews. Retain all
   cases, missing outputs and disagreements. Separate source-citation checks from
   semantic correctness; a schema-valid answer can still fabricate experience.
9. Report scoped before/after scores and uncertainty. Reused facts/clauses remain
   exposed regression data. Passing loss, model self-grades, synthetic matching
   or small-panel scores do not establish higher hiring probability. Never
   automatically promote a model, import its wording as fact or release the hold.
10. After explicit acceptance, prepare one actual job-specific full CV, run normal
    independent factual/editorial/rendered review and exact disclosure gates.
    Measure a prospective unique-employer cohort with fixed observation windows
    in the existing outcome tracker. Do not resend jobs to manufacture labels.

The model system prompts and output consumer live together in
`core/tailor_benchmark.py`. The user message contains only facts, scopes,
qualifiers and a requirement; generation never receives gold or a reference
assistant response. The existing canonical CV-review task remains the route for
future grader training after independent labels exist. Do not train the writer
and validate it solely with a grader trained on its own outputs.
