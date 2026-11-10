# Compare CV fit before and after tailoring

The kit already records six 0–3 editorial dimensions, exports reviewed `cv-review`
training examples and supports that task in the optional local LoRA runner.
This increment compares actual captured reviews and evaluates recorded grader
predictions. It neither generates grades nor trains a model automatically.

Use [the refined workflow prompt](../prompts/GRADE_TAILOR_REGRADE.md). Independent
review and candidate disclosure rules remain unchanged. An accurate longer CV
can score worse for concision; improvement is never assumed.

## Capture each review while it is current

```sh
python scripts/kit.py --data-dir ../private learning-export --task cv-review --job-id 1 --output datasets/before-001
# Tailor, complete the independent factual/editorial review, then capture again:
python scripts/kit.py --data-dir ../private learning-export --task cv-review --job-id 1 --output datasets/after-001
python scripts/compare_cv_reviews.py compare --before ../private/datasets/before-001/examples.jsonl --after ../private/datasets/after-001/examples.jsonl --job-id 1 --output ../private/evaluations/before-after-001.json
```

The comparison accepts bounded archived `recorded_cv_review` JSONL examples from
the existing `cv-review-json-1` export. It checks stored identities, target hashes,
rubric bytes, all dimensions, 0–3 integer scores and exact CV statement citations.
Both versions must share job/group, candidate revision, JD requirements, language
and rubric. Changed facts/source hashes are flagged as an evidence confound.
Identical CV text with changed scores is review drift, not a tailoring gain.
Reviewer strings are claims, not authenticated identities. No aggregate ATS score,
offer probability or causal winner is produced.

`input_files` binds actual file bytes. No ledger is opened or changed. Output must
be a new explicit file outside the public clone; existing files are never replaced.
Each capture is at most 20 MB/100 rows. Duplicate JSON keys, non-finite numbers,
duplicate examples, missing job captures and unknown statement citations fail.

Historical comparisons deliberately do **not** call current `learning-check`:
the old CV may have been superseded. The report states
`current_evidence_revalidated=false` and is **not a training export**. Existing
training checks still reject stale/revoked/changed sources and reviews. Do not
rename a comparison report into a dataset or bypass that gate.

## Evaluate a grading model

Record predictions as a JSON array with `example_id` and `editorial`. `editorial`
has exactly the same six score/statement-ID/rationale objects as the grading
target. Model input contains only the system and user messages; never feed the
reference assistant target into inference.

```sh
python scripts/compare_cv_reviews.py evaluate --references ../private/runs/heldout-review-examples.jsonl --predictions ../private/runs/grader-predictions.json --output ../private/evaluations/grader-001.json
```

The denominator is the complete supplied reference cohort. Missing or malformed
predictions stay in it. Reports separate valid-only ordinal mean absolute error
from a full-cohort penalized error (maximum three points in each dimension for
every invalid/missing review). Exact six-score-vector rate also uses the full
cohort. Unknown/duplicate prediction IDs fail rather than silently disappearing.
This evaluates agreement with recorded judgments, not human-gold correctness,
factuality detection, visual layout, hiring outcomes or held-out independence.
Supply every reviewed evaluation example selected by the dataset manifest in the
reference capture. This diagnostic does not select or certify that partition;
passing an export's complete `examples.jsonl` also evaluates its training rows.
Never call such an in-sample result a held-out benchmark.

## Train with reviewed real data

Use [recorded review learning](REVIEW_LEARNING.md) and its existing separate
`cv-review` export/validator/LoRA task. Require current independent review,
rubric-bound grades, multiple actual split groups, full-context token checks,
candidate/source overlap reporting and clean-base comparison. Keep grading and
tailoring targets in different datasets. A self-generated advisory grade is not
an independently reviewed label; an application receipt is not a quality label.
Cloud/private-file uploads require their own exact authority. Free compute only
when requested; never substitute paid or CPU training silently.

## Acceptance scope

See [observed local acceptance and limits](CV_REVIEW_CYCLE_QA.md).

Local fictional regressions cover export compatibility, changed evidence/JD/
candidate/rubric, exact citations, malformed scores, invalid-output denominators,
private no-overwrite CLI output and unchanged ledger bytes. Native host grading,
real independent labels, actual model training and improved tailoring/hiring
performance are separate unproven gates.
