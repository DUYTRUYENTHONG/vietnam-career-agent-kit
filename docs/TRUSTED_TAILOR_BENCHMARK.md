# Source-bound tailoring benchmark and bounded hill-climbing

Status: **Experimental offline CLI**, standard-library preparation and recorded
comparison. Optional Qwen3.5 Linux/T4 runner is **Experimental, not GPU-verified**.
No model, cloud upload, application or automatic promotion is performed by the CLI.
Real data stays in an explicitly selected external private root. Fictional tests
do not establish recruiter outcomes or trained-model improvement.

## Three evaluation layers

1. **Evidence and bullet quality:** captured requirements plus confirmed scoped
   facts; one fact per rewritten statement; abstention when unsupported. Check
   citations/JSON deterministically, then human-review entailment, qualifiers and
   the existing six editorial dimensions. The initial contract evaluates a bullet,
   not full-CV chronology, ATS parsing or rendered pages.
2. **Complete application package:** retain the existing JD-specific matrix,
   role selection, current review, parser/text extraction and every-page visual
   checks. A correct bullet does not prove that a whole application is suitable.
   Add blinded full-CV reviews through `compare_cv_reviews.py`; do not silently
   call the bullet test a full-CV benchmark.
3. **Recruitment outcomes:** use `outcome-record`/`outcome-report` for compatible
   portable workspaces, exact submitted CV hashes and fixed14/28-day observation
   windows. Legacy ledgers stay separate/read-only until explicitly migrated.
   Submission, acknowledgement, view, recruiter screen, assessment and interview
   are distinct events. Silence is unknown, not rejection or a negative SFT label.

For a prospective campaign pilot, preregister30 eligible unique vacancies,
assign one CV condition per employer/vacancy family before sending, balance role
family/seniority/channel where feasible, and preserve exact document hashes.
Never send two versions to the same vacancy for an A/B test. Report complete
denominators, observation cutoff, coverage and uncertainty.30 applications are
an exploratory cohort, not a powered causal hiring study. Email acknowledgements
must not inflate recruiter-screen conversion. Do not start this pilot before the
user's offline comparison/review hold is released.

## Local source and review contract

`core/tailor_benchmark.py` consumes case schema1.0 (see the adjacent JSON schema):
case/profile/source-family IDs, explicit language, one literal requirement and
1..100 exact evidence atoms with scope, material qualifiers, bound source bytes
and locators. Each case also records exposure. Paths remain inside the selected
root; a source hash and literal text check are not semantic verification.

Use actual human reviewers independently. Annotations name expected decision,
acceptable single-fact alternatives and a rationale. Both reviewers check source,
scope, qualifier and family identity before freezing. Blank, model-labelled,
same-reviewer and disagreeing packets fail. Resolve disagreements with the humans
in a newly versioned packet; do not force labels for class balance. Fields are
attestations, not authenticated identities or proof of independence.

```sh
python scripts/tailor_benchmark.py --root ../private prepare \
  --cases research/cases.jsonl --output research/preparation-v1
python scripts/render_benchmark_review.py --root ../private \
  --preparation research/preparation-v1 --reviewer-slot A \
  --output research/reviewer-A.html
python scripts/tailor_benchmark.py --root ../private freeze \
  --preparation research/preparation-v1 --review-a research/completed-A.jsonl \
  --review-b research/completed-B.jsonl --output research/frozen-v1
```

The offline HTML form creates no labels until a person completes it. It uses no
external scripts, requests or server. Give each reviewer a separate file; keep
their completed JSONL private. Human review of source permissions remains required;
a historical JD's readability is not permission for model training.

Freezing binds cases, human annotations, gold, rubric and generation messages.
Gold/references never enter generation messages. Case/profile exposure remains
explicit after freezing: a trusted reviewed regression panel is not automatically
an unseen-profile or unseen-project test. Group reposts, aliases and translated
clauses together. For a single profile, facts often must recur; report that scope.
Fresh prospective cases are required for an untouched acceptance claim.

## Matched Qwen3.5 study

Fixed conditions: `base_original`, `base_evidence`, `adapter_evidence`. The latter
two share identical messages. Pin model revision, tokenizer bytes, precision,
greedy decoding, seed, input budget and output budget. Each record retains raw
output, source/prompt bindings, actual tokenizer/adapter hashes and measured
tokens/generation time. Unknown metrics are null, never invented. Invalid output
is retained; there is no repair/retry that silently improves one condition.

The optional runner `python -m adapters.tailor_study --help` loads a local pinned
Qwen3.5-4B safetensors checkpoint, not a Qwen3 adapter or paid provider. Its local
`download-manifest.json` must have model_id, revision and complete file hashes.
It verifies checkpoint bytes before SDK/model loading. Install optional pinned
dependencies in an isolated free-cloud environment, never the core environment.
Provider quota/account/free allocation and exact private upload authority must be
checked separately before running; the caller flag cannot verify billing.

```sh
python -m adapters.tailor_study --root ../private --frozen research/frozen-v1 \
  --model-directory ../models/qwen35-4b --output research/run-001 \
  --comparison training --training research/human-reviewed-training.jsonl \
  --free-gpu-confirmed --prior-free-seconds ACTUAL_PRIOR_SECONDS \
  --cumulative-cap-seconds APPROVED_CAP --max-new-seconds APPROVED_REMAINING_LIMIT
```

`--comparison prompt` needs no training input. Training requires two actual human
reviews bound to every exact target, source-family separation from evaluation,
fresh rank8 QLoRA, two epochs, assistant-only loss and no truncation. Placeholder
reviews cannot start training. The wrapper uses one child process with a fixed
wall-clock limit, records all charged wrapper time and never automatically retries.
Free T4 absence, nonfinite gradients, changed sources or incompatible context stop
the run. Partial artifacts remain failed; missing outputs are not omitted from
evaluation. Complete OS/cloud runtime and dependency compatibility remain unverified.

```sh
python scripts/tailor_benchmark.py --root ../private blind \
  --frozen research/frozen-v1 --records research/run-001/generations.jsonl \
  --output research/blinded-v1
python scripts/tailor_benchmark.py --root ../private compare \
  --frozen research/frozen-v1 --blinded research/blinded-v1 \
  --reviews research/output-reviews.jsonl --output research/comparison-v1.json
```

Keep `operator_key.jsonl` away from reviewers. Each output needs at least two
human reviewers; all recorded reviews count. Structural failures, wrong evidence,
missing reviews and failed factual checks receive zero quality over the full
cohort. Scores0..3 remain transparent editorial judgments, not ATS percentages.
Text readability is not rendered-layout acceptance. The report uses paired source-
family bootstrap intervals, conditional on reviewed family independence and this
profile. The preregistered experimental gate requires delta>=0.25, positive lower
95% interval, at least10 source families, complete review, zero observed candidate
factuality/scope/qualifier failures and no invalid/missing candidate outputs.
Passing reports never promote a model or grant application authority.

## Hill-climb only on development data

Use `scripts/hillclimb_eval.py` to record a fixed plan, bounded rounds and one
final test. `core/eval_hillclimb.py` rejects test reports as development feedback,
source-family overlap, changed parents, unreviewed outputs and exhausted budgets.
Select one lever family per plan. Prompt rounds change only the system prompt;
training comparison is one fresh-base round. Retrieval experiments require a
separate preregistered matched comparator and are not implemented here.

For prompt changes, create a new variant with `tailor_benchmark.py variant
--frozen ... --prompt research/candidate-system.txt --output ...`. It preserves
the exact cases, gold and rubric, moves the prior evidence prompt into the
baseline slot, and binds the new candidate prompt. Use `blind --comparison prompt`
to compare only the two base conditions. Candidate prompt files are reviewed data;
do not run downloaded hooks or instructions from them.

Plan fields: schema_version1.0, development_cohort_sha256, test_cohort_sha256,
development_groups, test_groups, starting_variant_sha256, allowed_levers (one of
prompt/training), max_rounds<=10, max_free_seconds, prior_free_seconds,
cumulative_cap_seconds, stop_after_non_improving. Use short default studies of
three prompt rounds and stop after two non-improving rounds. Never reset spent
time when a round fails. Each proposal names its parent/candidate hash, one lever,
failure-based hypothesis, changed files and actual free seconds.

```sh
python scripts/hillclimb_eval.py --root ../private --study research/climb-001 \
  init --plan research/hillclimb-plan.json
python scripts/hillclimb_eval.py --root ../private --study research/climb-001 \
  record --proposal research/round-001.json --report research/dev-comparison.json
python scripts/hillclimb_eval.py --root ../private --study research/climb-001 \
  final --report research/test-comparison.json
```

Improvement inside uncertainty keeps the parent; unsafe changes are rejected.
Record the actual diff and failure examples. Do not inspect final test outputs
to choose another prompt. `final` writes one exclusive final_test.json and closes
the study. This is filesystem discipline, not a security boundary preventing an
operator from opening files or creating another directory. A new study cannot
truthfully relabel an exposed test as untouched.

Concept references: [Anthropic hill-climb guide](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/claude-api/shared/evals/eval-hillclimb.md),
[eval design](https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/claude-api/shared/evals/build-eval.md),
[OpenAI evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices),
[Qwen model card](https://huggingface.co/Qwen/Qwen3.5-4B).
Conceptual adaptation only: no third-party skill/code installed or copied, no
Claude-specific pricing, paid API, automatic resume/retry or provider change.
