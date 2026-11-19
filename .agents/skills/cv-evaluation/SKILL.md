---
name: cv-evaluation
description: Design and run source-bound CV tailoring benchmarks, cross-check captured grader outputs and triage evaluation disagreements without creating human labels or application authority.
---

Read ../../../docs/job-seeker-policy.md. This project skill serves explicit CV
evaluation, grader-comparison or benchmark requests, not ordinary editing alone.

Select the actual evaluation task before choosing a tool:

- Evidence retrieval: ../../../docs/CV_PLANNING.md, with human-reviewed gold and
  explicit hit/recall denominators. Overlap is not semantic fit.
- Bullet writing: ../../../docs/TRUSTED_TAILOR_BENCHMARK.md. Compare frozen base,
  improved prompt/retrieval and adapter conditions; tune on development only.
- Whole-CV editorial grading: ../../../docs/CV_EVAL_CROSSCHECK.md and the existing
  six-dimension review contract. Cross-check model passes and escalate disagreement.
- Operational first pass: ../../../docs/HOST_REVIEW_AUTOMATION.md. Same-host roles
  are model proposals, not independent human review.
- Recruitment outcomes: ../../../docs/CV_OUTCOMES.md. Keep submission, view,
  screen, assessment and interview separate; silence remains unknown.

Use the existing selected host unless the user explicitly chooses another runtime.
Do not introduce a service, paid API, model switch or automatic critic cascade.
Capture actual model identity/revision when available, otherwise unknown. Never
describe multiple passes of one model as independent models.

Keep references outside inference input. Preserve invalid/missing outputs in the
cohort. Calibrate automated grading against actual human decisions; agreement
between models alone does not establish correctness. Use task-specific frozen
criteria, not a generic accuracy threshold or ATS/hiring probability.

Apply ../../../prompts/CV_EVAL_CROSSCHECK.md for cross-checks. AI findings, human
adjudication, training targets and observed hiring outcomes stay separate.
No result automatically promotes a model, writes human gold or approves sending.
