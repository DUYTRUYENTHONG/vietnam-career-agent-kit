# Private-data Qwen3-8B pilot: observed training, failed acceptance

An opt-in private Colab experiment completed on 2 November 2026. This report
publishes aggregate observations only. Candidate facts, employer clauses,
prompts, raw outputs, source packets and model weights remain private.

This corrects the catalog's earlier statement that no personal-data training
had completed. It does not make the adapter available or accepted for CV use.

## Selected completed run

| Setting | Observed value |
|---|---|
| Base | Qwen/Qwen3-8B |
| Revision | `b968826d9c46dd6066d109eabc6255188de91218` |
| Hardware | Tesla T4 |
| Method | Private notebook QLoRA experiment |
| Data | 94 training rows; 7 held-out rows |
| Training | 2 epochs; 48 optimizer steps |
| Environment | Torch 2.11.0+cu130; Transformers 4.57.6; PEFT 0.18.1; Accelerate 1.12.0; bitsandbytes 0.50.2; safetensors 0.7.0 |

The local kit runner was not changed to implement this notebook. Its existing
CPU/CUDA LoRA and reviewed-export contracts retain their documented limits.
The private experiment uses separate source-bound rewrite/assessment examples;
these are not interchangeable with the core's complete-CV wording schema.

## Measurements from this run

| Measurement | Value / scope |
|---|---|
| Model loading | 74,513.102 ms |
| Training loop | 466,955.970 ms, including epoch evaluation |
| Recorded training input tokens | 54,834 across optimizer-step windows |
| Recorded assistant supervision tokens | 15,748 across those windows |
| Held-out assistant-token NLL | Base 2.072818; epoch 1 0.789158; epoch 2 0.737334 |
| Peak allocated GPU memory | 11,319,843,840 bytes |

Training supervision tokens are teacher-forced targets, not generated output
tokens. Loading, training and generation have different timing scopes. These
numbers describe the selected run, not another recovery run, end-to-end campaign
latency, provider charges or subscription savings.

## Paired wording review

The seven cases span three held-out candidate facts, one employer's historical
requirements and two tasks: rewriting and requirement/fact assessment. The
review was non-blinded: variant identities, source packets and reference answers
were visible. It is a bounded maintainer review, not an independent blinded
benchmark or representative employer sample.

| Check | Clean base | Final adapter |
|---|---:|---:|
| Strict JSON and exact source/requirement IDs | 7/7 | 7/7 |
| Content passes | 1/7 | 1/7 |
| Correct evidence-relation label | 6/7 | 5/7 |
| Standalone rewrite bullets preserving AI-assisted personal-project scope | 0/3 | 0/3 |

The lower reference loss did not produce overall content acceptance. Failures
included lost contribution qualifiers, overstated evidence relationships and
insufficiently specific supported-aspect descriptions. Exact JSON and IDs did
not establish factual entailment. No generated wording was promoted automatically.

## Recovery and next gates

The completed training and observed cloud archive do not establish a verified
host checkpoint. A later runtime no longer contained those temporary artifacts;
host recovery was not verified. No private adapter is included in the release.

A separate next-run pack was prepared but had not started when free Colab GPU
allocation reported usage limits. It is not a running job or a completed result.
A supplementary two-job evaluation set is preparation only; it has no model
outputs or quality score. Do not combine its case count with this run's seven.

Before any promotion, retain a verified local checkpoint, generate matched raw
base/adapter outputs on broader held-out job groups, and review factuality,
contribution qualifiers, requirement fit and useful specificity. Keep familiar
facts/unseen requirements separate from unseen-fact cases. Recruiter response
rates need their own appropriately attributed observations; this pilot measures
neither CV admission nor interview improvement.

See [checkpoint verification](MODEL_CHECKPOINTS.md),
[paired wording evaluation](WORDING_EVALUATION.md) and the
[fork-and-train guide](FINE_TUNING_START.md). Use fictional fixtures for public
reproduction. Never publish a personal corpus or its weights by default.
