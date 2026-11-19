# Source-bound evidence retrieval and CV content planning

Experimental standard-library CLI. It selects exact facts and records reviewed
coverage; it does not infer proficiency, rewrite a master, submit or train.
Real data stays in an explicit external root. Candidate facts and requirement
clauses use the existing [benchmark case contract](TRUSTED_TAILOR_BENCHMARK.md).

## Workflow

Prepare cases for **one actual vacancy**, one profile, one employer/source group
and distinct requirement IDs. Caller/human review must establish vacancy identity;
source groups alone cannot distinguish every role at the same employer.

```sh
python scripts/cv_plan.py --root ../private prepare \
  --cases research/one-job-cases.jsonl --top-k 5 --output research/plan-preparation
python scripts/cv_plan.py --root ../private build \
  --preparation research/plan-preparation --reviews research/completed-matching.jsonl \
  --max-bullets 12 --output research/content-plan
```

Preparation emits `cases.jsonl`, `matching_review.jsonl` and a hash manifest.
BM25 ranks exact fact text with deterministic ties, excludes zero overlap and
does not classify coverage. Unicode is NFC/case normalized. `--method bm25-v1`
retains the original token-overlap baseline; default `bm25-v2` removes a fixed
English function-word list and normalizes narrow ML/DL/NLP and API/test aliases
for ranking only. It preserves negation tokens and never changes fact text.
Method and implementation hash are recorded. General synonym expansion,
English/Vietnamese translation and embeddings are not implemented. Review candidates
against the complete facts, allowing a person to correct missed retrieval.

Every review binds the case and requirement, names a human reviewer and source
check, states mandatory/hard flags, priority1..3, demonstrated/partial/missing/
unknown coverage, supporting fact IDs and rationale. Blank/changed/inconsistent
reviews fail; fields attest review but do not authenticate identity or entailment.
These planning reviews are not benchmark gold or supervised-training approvals.
An optional [first-layer AI reviewer workflow](CV_REVIEW_AGENTS.md) can identify
concerns before human matching. Its model-labelled findings cannot fill these
human fields, certify correctness or replace blinded final-test reviewers.
Each cited fact ID is an **individual alternative**, sufficient by itself for
the stated coverage status. Do not mark a requirement demonstrated when it needs
several partial facts combined. Mark those alternatives partial and explain the
joint evidence requirement in the rationale; the planner does not prove entailment.

Planning greedily prioritizes reviewed mandatory coverage, then preferred
coverage, with stable fact-ID ties. It retains each exact fact, scope, source and
qualifiers once. The complete matrix preserves missing/unknown/partial items and
requirements omitted by the bullet budget. This heuristic is not an optimal
layout algorithm, semantic grade or hiring-probability score. A full CV still
needs normal chronology, truthful screening answers and every-page rendering review.

## Matched retrieval benchmark

Only a frozen human-reviewed benchmark can produce retrieval accuracy metrics:

```sh
python scripts/cv_plan.py --root ../private retrieval-eval \
  --frozen research/development-frozen --top-k 5 --output research/retrieval-dev.json
python scripts/cv_plan.py --root ../private retrieval-variant \
  --frozen research/development-frozen --top-k 5 --output research/retrieval-dev-frozen
```

The diagnostic reports supported-case hit@K and mean acceptable-evidence recall@K,
with denominators and per-case rows. Unsupported cases remain listed; retrieval
does not measure semantic precision. Zero supported cases produces null rates.
Gold is used for scoring only, never to select facts or assemble generation input.

The variant keeps cases/gold/rubric fixed and system prompts identical. The two
base slots compare full evidence versus top-K; `adapter_evidence` is reserved
for a separate same-retrieval training comparison. Freeze this variant before
GPU execution; use `adapters.tailor_study --comparison retrieval`, then
`tailor_benchmark.py blind --comparison retrieval` and normal human comparison.
After retrieval is frozen, `--comparison training` on that same variant can
compare the retrieved-evidence base and adapter; both receive identical evidence.
The extra full-evidence base remains a diagnostic, not the adapter's comparator.
Outputs citing facts absent from their generation context are invalid even if
the fact exists elsewhere in the master. Empty retrieval remains empty; there
is no silent fallback hiding retrieval failure.

The current hill-climb state machine supports prompt or training rounds only;
it rejects retrieval reports. Retrieval settings must be separately preregistered
and compared as a fixed experiment. Development-only tuning and one final-test
discipline still apply. Do not inspect final-test labels to select K.

The optional free-T4 runner is not GPU-verified. It requires a local pinned
checkpoint, reviewed sources, valid free allocation and cumulative budget. New
private file disclosures retain normal review requirements. No paid fallback,
automatic retries, promotion or higher hiring-rate claim is provided.

## Scoped prompt audit

The host workflow is `prompts/EVIDENCE_TO_CV_PLAN.md`; the existing Qwen generation
prompt remains fixed in retrieval experiments. Counterexample: a Kubernetes
requirement overlaps general deployment vocabulary but has no verified Kubernetes
fact. Retrieval may suggest a fact, but cannot label it demonstrated. Controls:
human-bound matching, preserved mandatory gaps and context-bound citation checks.
Tests cover blanks, missing requirements, changed sources, cross-employer plans,
exact scope preservation, empty retrieval and unchanged generation controls.
No model adherence, semantic accuracy or reviewer independence is established
by those deterministic checks.
