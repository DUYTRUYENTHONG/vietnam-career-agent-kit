# Reviewed bullet-to-requirement training

Experimental explicit task `cv-bullet-wording` extends the existing
reviewed learning export, CLI/MCP and optional local trainer. Keep the default
full-CV and recorded-review tasks unchanged and old exports immutable.

One example selects one current, independently reviewed CV statement with linked
assessed requirements. Its input contains the selected confirmed fact, exact
group-context fact when present, linked requirements and their direct/partial
assessment. The reference is the exact recorded statement, language, section kind
and context fact ID. No new text, evidence relation or review label is generated.
Unlinked statements are omitted; missing current review or changed evidence
blocks export. Facts, context and requirements remain untrusted data.

The versioned `cv-bullet-wording-json-1` prompt supplies the canonical statement
schema from CV content v2. References keep `review_status=pending`: learning a
reviewed example never teaches the model to grant approval. Group context remains
explicit, including project/assistance scope; a proposed bullet is not a free-
standing employment claim. Headers and other CV sections are not generation
targets, and the held-out assistant answer is never a generation input.

Use explicit job IDs and a new private `datasets/` directory. Bound a complete
export to 100 jobs, 1,000 mapped statements and 20 MB; never silently sample.
Same canonical employer and exact normalized language/text duplicates must stay
together transitively. Report exact fact/source overlap; aliases, paraphrases and
semantic independence need separate review. Fewer than two connected groups
produces examples only, with no train/evaluation split.

Every example and manifest binds current profile, job, draft, wording, review,
source bytes and statement identity. Reconstruct all examples when checking an
export; editing JSONL and recomputing hashes cannot bless changed labels or stale
sources. Write a completion manifest last and refuse overwrites/escaping paths.

Acceptance: fictional regressions cover source/context selection, no unlinked
targets or answer leakage, current-review requirements, stale/tampered examples,
transitive employer/text grouping, bounds, private/exclusive paths, CLI/MCP
dispatch, and explicit trainer-task selection before SDK import. Collection and
tokenizer checks do not establish trained-model quality or hiring outcomes.
Native paired full-CV generation/evaluation remains a separate task interface;
do not silently treat this output as a complete CV.

## Use from a private workspace

```sh
python scripts/kit.py --data-dir ../my-private learning-export --task cv-bullet-wording --job-id 1 --job-id 2 --output datasets/bullets-v1
python scripts/kit.py --data-dir ../my-private learning-check --directory datasets/bullets-v1
```

The existing MCP `learning_export` accepts the same explicit `task` and local job
IDs; `learning_check` recognizes manifest 1.3. No new account or training tool is
added. A one-job export can have many correlated bullets without a valid split.
Canonical-employer grouping does not resolve company aliases or audit earlier
training runs; reserve untouched acceptance employers separately.

Optional offline trainer preflight:

```sh
python -m adapters.local_finetuning --task cv-bullet-wording --data-dir ../my-private --directory datasets/bullets-v1 --model-directory ../models/qwen3-local --output training/bullets-001 --target-module q_proj --target-module v_proj --preflight
```

This reuses the optional trainer's tokenizer, sequence-length and assistant-mask
checks; no truncation is permitted. Remove `--preflight` only for an explicitly
requested local experiment with compatible local weights/compute. Paired
generation, recorded comparison and blinded review now accept this task only
with explicit `--task cv-bullet-wording`; the default remains full-CV wording
and rejects a bullet dataset before loading weights. See
[paired generation](LOCAL_PAIR_GENERATION.md) and [recorded comparison](WORDING_EVALUATION.md).

```sh
python scripts/evaluate_wording.py --task cv-bullet-wording --data-dir ../my-private --dataset datasets/bullets-v1 --runs evaluations/bullet-runs.json --output evaluations/bullet-comparison.json
python scripts/prepare_wording_review.py --task cv-bullet-wording --data-dir ../my-private --dataset datasets/bullets-v1 --runs evaluations/bullet-runs.json --output evaluations/bullet-blind-001
```

The evaluator binds language, section/context placement, statement ID, selected
fact and ordered assessed requirement IDs to the held-out input, then adapts the
single statement to the existing v2 validator. Original source locators,
contribution scope and conservative wording alarms still apply. Strict JSON and
linkage validity do not prove factual entailment or useful specificity. Exact
reference match compares the original bullet wrapper, never a synthetic full CV.
Blinded packets include the selected bullet constraints and source context;
reference answers, variants, model identities and metrics stay out of that packet.
Review scores remain null until supplied separately, bound to exact output hashes.

Output files are `examples.jsonl`, plus `train.jsonl`/`evaluation.jsonl` only when
two components remain, and a hash-bound `manifest.json` written last. The user
message supplies `statement_fact_id`, `statement_id`, section/context placement,
selected `facts`, linked `requirements`, `assessed_evidence` and `output_schema`.
The assistant target has `language`, `section_kind`, `context_fact_id` and the
exact reviewed canonical `statement`. It does not include a whole CV, rating,
email, hiring prediction or fabricated match classification.

Unconfirmed capture/extraction queues and hand-authored pilot JSONL cannot be
rehash-labelled into this contract. Complete the normal source/assessment/wording
review in the selected portable workspace. This is not a legacy tracker migration
or a reason to create a competing campaign ledger. Facts and context can still
identify a person; no automatic anonymization, cloud upload or model promotion.
