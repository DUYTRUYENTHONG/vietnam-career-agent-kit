# CV evaluation skill and captured-grader cross-check

The project-local `cv-evaluation` skill routes explicit evaluation tasks to the
existing retrieval, bullet, whole-CV, first-layer review and outcome contracts.
It is not globally installed. Project discovery is distinct from native runtime
acceptance. Model identity remains the user's existing selected host unless the
user explicitly chooses another runtime; no new model service is supplied.

## Prepare judge inputs

Use recorded `cv-review-json-1` examples from the existing authorized export.
These are six-dimension editorial judgments, not bullet/source matching labels.

```sh
python scripts/cv_eval_crosscheck.py --references ../private/review-references.jsonl \
  --output ../private/judge-inputs.json
```

This emits only system/user inference messages, never the reference assistant
target. `inputs_sha256` binds the complete ordered request cohort. Feed each
grader those exact messages, the same rubric and case inputs. IDs are routing
metadata. Use suitable actual output/context limits for six scores, citations
and reasons; do not blindly reuse the bullet experiment's256-token output cap.
Unknown or truncated outputs remain invalid, not repaired into good grades.

Capture a JSON array of two to four passes. The prepared file supplies a complete
`grader_template` with null grades, empty citations and null rationales. Copy it
for each actual pass, give a distinct grader ID and replace blanks only with that
grader's captured results. Blank templates cannot score as valid predictions.
Do not fill them from reference answers. Each pass contains grader_id, model_id,
model_revision, inputs_sha256 and predictions. Dimensions are
relevance, specificity, coverage, clarity, concision and readability; each needs
an integer0..3, exact statement IDs and a brief reason. At least two passes are
required. Do not invent model IDs, revisions, human reviews or runtime metrics.

```sh
python scripts/cv_eval_crosscheck.py --references ../private/review-references.jsonl \
  --graders ../private/captured-graders.json --writer-model-id unknown \
  --output ../private/crosscheck.json
```

## Interpretation

- Each grader receives the existing complete-cohort penalized MAE report against
  recorded reference judgments; this is not accuracy against authenticated gold.
- Pairwise reports retain full-cohort exact score-vector rates, valid-pair ordinal
  differences and unresolved counts. Missing/invalid predictions stay in the
  denominator. No shared valid cases produces null mean difference, not zero.
- Per-case score spreads and missing/invalid graders form a human triage queue.
  No maximum score, majority vote or model consensus is promoted to truth.
- Distinct model IDs are caller declarations. Unknown IDs or multiple passes of
  one model cannot be called independent models; distinct IDs still do not prove
  independence or correctness. Same declared writer/judge models are flagged.
- Existing first-layer categorical findings are not automatically converted into
  these ordinal grades, benchmark labels or training targets.

Current real-data human annotations and actual captured eval-model predictions
are prerequisites for an honest calibrated model benchmark. Fictional tests
establish contract/denominator behavior only. Use model disagreement for review,
not automatic extra model calls. Preserve separate development/final cohorts and
calibrate future automated grading on actual human decisions before promotion.
No offer probability, ATS percentage, hiring-rate claim or application authority.

## Scoped skill/prompt audit

Applied prompt-engineer guidance to task-specific metrics, structured outputs
and one-change evaluation. Its generic80% example is not adopted as a CV quality
threshold. The kit retains factuality/qualifier gates and preregistered criteria.
Counterexamples: same-host agreement mistaken for independence; missing outputs
silently removed; reference assistant targets leaked into judge inference.
The parser and fictional tests enforce identity declarations, full denominators
and system/user-only inputs. Human authenticity, inference behavior and actual
grader quality remain unverified. No external skill code was copied or executed.
