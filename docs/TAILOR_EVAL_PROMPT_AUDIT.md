# Tailoring evaluation prompt audit

Scope: canonical application-tailoring instructions, new host workflow,
`core/tailor_benchmark.py` message builder/output parser and optional experiment
consumer. Existing unrelated prompts, global settings, credentials, real datasets,
sealed labels and other projects are excluded from this prompt audit. Real private
data preparation is a separate explicit user workflow, not part of this audit.

Consumers: host agent (model not changed); pinned Qwen3.5-4B proposals; human
annotators and the strict single-statement parser. No Claude runtime is adopted.

| Finding | Evidence and consequence | Implemented check/control |
|---|---|---|
| A generic rewrite instruction does not teach selection/abstention | A request for deployment cannot turn a test script into production serving | Evidence-first system prompt names the boundary and not_demonstrated output; parser rejects unknown fact/requirement IDs. Human entailment review remains required |
| Scores can improve if broken or unreviewed rows are silently omitted | A missing candidate output would otherwise shrink its denominator | Blinded packets retain every case/condition; full-cohort zero penalty and no promotion for incomplete review |
| A changing prompt must not alter cases, answers or the comparator unnoticed | Rebuilding messages from current constants could change a frozen experiment | Generation hashes bind the frozen messages; prompt_variant preserves cases/gold/rubric and records its parent; tests prove the counterexample and unchanged controls |
| Reusing final-test feedback to choose another variant invalidates the holdout | A test report could be passed as a dev report | Hill-climb requires the development cohort hash; final result is exclusive and closes that study; remaining operator/exposure limitations documented |
| Valid citations do not prove factual or editorial quality | A generated bullet can cite a real fact while inventing Kubernetes | Source/JSON checks and actual human semantic checks remain separate; model-authored human labels fail the software gate |

Confidence: high for request/parser/state contract defects and deterministic
checks. Generation-quality effects are unmeasured. The baseline and improved
prompts use the same schema and facts; a Qwen comparison has not been run by this
audit. No claim of higher recruiter response, cache savings or model superiority.

Bounded fictional tests cover missing labels, distinct reviewers, disagreement,
changed sources, changed output, invented citations, qualifier judgments,
prompt/record bindings, invalid telemetry, disjoint families, spent-time history,
noisy changes and final-test identity. The optional GPU training path still needs
a free-T4 smoke, actual token budgets and reviewed private data before acceptance.

The implementation diff is the reviewable proposed/applied patch for this audit;
existing policy, assistance qualifiers, exact disclosure gates and release QA are
retained. No downloaded hook, upstream installer or global configuration changed.

## Evidence retrieval and planning extension

Scope: EVIDENCE_TO_CV_PLAN host prompt, canonical tailoring routing and the
fixed-prompt retrieval comparator. Requirements and exact facts remain data.
Counterexamples: overlap cannot certify Kubernetes experience; several partial
facts cannot become one fully demonstrated requirement; a model can guess a
real fact ID that was absent from its top-K context. Implemented controls:
reviewed single-fact alternatives, mandatory-gap and budget-omission preservation,
identical comparator prompts and context-bound citation invalidation. Retrieval
experiments cannot be mislabelled as prompt-only hill-climbs. Fictional tests
verify these boundaries; semantic relevance and model behavior remain unmeasured.
