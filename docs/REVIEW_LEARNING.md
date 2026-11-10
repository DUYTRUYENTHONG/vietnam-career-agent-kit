# Learn from recorded CV reviews

For before/after tailoring comparisons and full-cohort ordinal evaluation of a
grading model, use [the review cycle](CV_REVIEW_CYCLE.md). It reuses the exports
below; archived diagnostic reports never bypass current training-data checks.

`learning-export --task cv-review` collects the existing six editorial grades
and cited rationales from an exact, current independently reviewed v2 CV. It
does not invent scores, call a model, inspect an inbox or infer recruiter results.
The default `cv-wording` task is unchanged.

## Collect actual labels

Prepare/import your source-bound v2 wording and record its independent review
through the normal [tailoring flow](JD_SPECIFIC_TAILORING.md). The existing
[rubric](CV_QUALITY_RUBRIC.md) uses six dimensions, each 0–3 with statement IDs
and rationale. Repair factual findings before exporting; a high editorial grade
never overrides an unsupported claim.

The wording packet exposes `review_rubric_sha256`. After actually reviewing with
that rubric, include this value as `rubric_sha256` in the review JSON. Existing
reviews without it remain valid for their normal workflow, but cannot export
grading labels. A changed rubric requires an explicitly re-evaluated review;
do not attach a new hash to old scores without reassessing them.

```sh
python scripts/kit.py --data-dir ../my-private learning-export --task cv-review --job-id 1 --job-id 2 --output datasets/reviews-001
python scripts/kit.py --data-dir ../my-private learning-check --directory datasets/reviews-001
```

The existing MCP `learning_export` tool accepts the same optional `task` value;
`learning_check` detects and validates the version. No extra server or API is
needed. No user workspace is selected implicitly.

Each example contains the role, captured requirements, source-cited facts, CV
sections, dimension names and rubric. Its assistant target contains only the
recorded `editorial` object. Scores and reviewer claims are absent from the model
input. Direct candidate identity/contact headers are omitted, but source quotes,
professional contexts and provenance can still identify people. Keep exports
private; local storage does not prevent your chosen AI host from processing data.

All six dimensions stay in **one example per CV/job**. Six scores are not six
independent CVs. The existing splitter keeps same-job/revision and exact target
duplicates together. Identical reviews can leave multiple jobs with no usable
split. At least two resulting groups are required by the optional trainer;
that minimum alone does not establish enough data or a reliable benchmark.
Input fact/source overlap is reported, not hidden. Use separate held-out jobs
and independent adjudication; candidate-disjoint evidence is needed before any
claim of generalization to other people.

## Versioned task and evidence

Review exports use manifest **1.2**, `task=cv-review` and prompt
`cv-review-json-1`. Existing wording manifests 1.0/1.1 retain their original
contracts. An export binds the current profile/JD/draft/wording/review hashes,
reviewer claim and exact UTF-8 rubric-file digest. It revalidates the original evidence
and exact rows when checked or passed to the trainer. A changed rubric, review,
source or dataset requires a fresh reviewed export; do not rewrite manifests to
force acceptance. Existing directories are never overwritten.

The label kind is `recorded_editorial_judgment_not_hiring_outcome`. Reviewer
identity/type is not authenticated by these files, and an independent-pass flag
does not establish a human or blind review. Readability is **text-only**: this
export supplies no PDF images or rendered layout. Do not train it as a visual
layout evaluator, recruiter preference model or acceptance-probability estimator.

These CVs have already passed the existing factual review. This export does not
supply adjudicated fabrication-negative examples or make a trained grader a
factuality detector. Keep deterministic provenance checks and independent factual
review separate from editorial-score experiments.

## Optional local experiment

After reviewing the labels and selecting independent held-out groups, use an
explicit existing local model and the separate task:

```sh
python -m adapters.local_finetuning --help
python -m adapters.local_finetuning --data-dir ../my-private --directory datasets/reviews-001 --model-directory /path/to/local-qwen3 --output training/review-001 --task cv-review --target-module q_proj --target-module v_proj --max-length 8192 --preflight
```

Select target modules that exist in your chosen model. Provision the optional
environment and base model through [local fine-tuning](LOCAL_FINETUNING.md).
This example checks an explicit 8,192-token limit without loading weights; it
does not establish hardware fit for training. Preflight tokenizes the full CV context; overlength examples fail without silent
truncation or loading weights. A larger context setting requires separate hardware
validation. Do not place this data into a short one-bullet pilot or mix review,
wording and growth targets in one export by renaming the task.

Remove `--preflight` only for an explicitly chosen local training run. The runner
compares assistant-token loss with the clean base and records actual timing and
tokens; it does not establish semantic review quality or promote an adapter.
Before deployment, compare generated reviews with independently adjudicated
held-out judgments, check citations and unsupported claims, and report ordinal
score errors and sample/group counts. Never use a trained reviewer as authority
to approve its own generated CV claims.

## Acceptance scope

Fictional tests cover exact recorded grades, no candidate-header/target leakage,
one-example grouping, unchanged ledger bytes, edited/revoked labels, rubric
changes, task mismatch, the CLI and actual SDK MCP calls. They do not certify
model training, reviewer accuracy, a particular GPU fit or improved hiring rates.
Older campaign databases are not migrated; custom private review files must not
be imported by creating a competing tracker. See [source-memory bridge](SOURCE_MEMORY.md).

Local Windows Python 3.12 acceptance also used the pinned Qwen3-8B tokenizer
without base weights: two fictional reviews split one per train/evaluation group,
each 2,054 full-template tokens including 315 reference assistant tokens. A
128-token limit failed; an 8,192-token preflight passed without creating a run or
changing ledger bytes. These are reference-token counts, not generated tokens,
and they do not establish memory fit, kernels or performance of an 8B model.
