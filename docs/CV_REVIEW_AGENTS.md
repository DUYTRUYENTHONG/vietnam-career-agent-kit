# First-layer CV reviewer roles

Status: experimental offline request preparation and advisory validation. Three
portable agent prompts are provided; native agent registration, autonomous model
dispatch and cloud execution are not installed. The user's host can run each
role against its exact request using an already authorized model/runtime.

| Role | First-layer task |
|---|---|
| Evidence | Unsupported claims, dropped qualifiers and conflicting sources |
| Requirements | Relevant evidence, partial coverage and unresolved conditions |
| Editorial | Specificity, repetition, order and concrete supported detail |

```sh
python scripts/cv_review_agents.py --root ../private prepare \
  --preparation research/plan-preparation --draft research/draft-statements.json \
  --output research/first-review-requests
python scripts/cv_review_agents.py --root ../private collect \
  --requests research/first-review-requests --responses research/model-reviews.jsonl \
  --output research/first-review-advisory
```

The optional draft is a JSON array of `{id,text,fact_id}` statements. Without a
draft, agents can inspect evidence/questions but cannot establish draft readiness.
Requests include exact case/source/draft bindings and separate system/user text.
No benchmark gold or another reviewer's answers are supplied. Run roles separately;
the same model may serve several roles, but this is not independent verification.
Calls and charges are not performed or measured by these offline commands.

Each captured response is exactly `{role,reviewer_type,input_sha256,model_id,
findings}`. `reviewer_type` must be `model`; use the actual model ID or `unknown`,
never invent runtime provenance. Findings cite known case/fact/statement IDs,
category, severity, reason and proposed action. The validator rechecks source
bytes, rejects unknown citations, relabelling and stale/duplicate role results.
It does not verify semantic correctness, model identity or prompt adherence.

Missing roles remain explicit. Empty findings, a high model score or agreement
among these roles never approves a document or creates human benchmark labels.
Humans resolve findings before normal factual/editorial/layout and disclosure
gates. AI proposals and later human decisions remain separate artifacts. Keep
all real inputs/results private. Do not train the writer or grader on its own
unreviewed judgments. Use the existing reviewed exporter only after actual
independent review. Final-test reviewers should assess outputs independently of
these AI proposals to reduce anchoring; first-layer AI review serves development
and operational CV preparation, not replacement of blinded final evaluation.

Scoped prompt audit: only the three role prompts and their strict output consumer
are changed. Adversarial sources remain data. Tests reject machine→human
relabelling and invented citations; clean captured findings still require human
resolution. No extra model API, paid service, authority or active hook is added.
