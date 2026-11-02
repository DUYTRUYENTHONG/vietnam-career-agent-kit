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

A separate next-run pack initially stopped at the free-GPU guard. That pack later
completed on a newly available free T4; its distinct observations are below.
A supplementary two-job evaluation set is preparation only; it has no model
outputs or quality score. Do not combine its case count with this run's seven.

## Subsequent 100/7 run: completed, still not accepted

The separately authorized fresh-base run completed on 2 November 2026. It used
100 reviewed training rows, seven held-out rows, two epochs and 50 optimizer
steps. Its pinned base revision and package versions match the table above.
The 48-source-fact corpus contains related examples, not 107 independent career
achievements. Evaluation still covers three facts and one held-out employer
group; this is not the supplementary two-job evaluation.

QLoRA settings were rank 8, alpha 16, dropout 0.05, learning rate 0.00005,
two warmup steps and gradient accumulation of four with microbatch size one.
The base used 4-bit NF4 double quantization and FP16 compute, with FP32 trainable
adapter parameters. Generation was greedy, non-thinking, one example at a time,
with a 384-new-token cap. No held-out generation reached that cap.

| Observation | Clean base | Final adapter |
|---|---:|---:|
| Held-out assistant-token NLL | 2.072818 | 0.724377 |
| Held-out perplexity | 7.947186 | 2.063446 |
| Strict JSON and exact source/requirement IDs | 7/7 | 7/7 |
| Correct evidence-relation label | 6/7 | 5/7 |
| Content passes in bounded maintainer review | 1/7 | 1/7 |
| Standalone rewrites retaining AI-assisted personal-project scope | 0/3 | 0/3 |
| Generation input tokens, seven cases | 1,928 | 1,928 |
| Generated output tokens, seven cases | 439 | 532 |
| Median generation latency, excluding loading/tokenization | 6,503.589 ms | 13,098.751 ms |

The training sequence contained 58,550 input tokens and 16,630 assistant
supervision tokens across its optimizer windows. Loading took 485,057.349 ms;
the training-loop measurement was 426,883.012 ms, including epoch evaluation
and checkpoint saves. Optimizer windows alone totaled 416,001.220 ms. These
boundaries are separate; do not add teacher-forced targets to generated-token
counts or present this as end-to-end application throughput.

The adapter generated more tokens and had higher median generation latency in
this small workload. It also produced a gap explanation denying data-quality
control evidence while describing the supplied validation checks. Both variants
dropped material assistance/personal-project scope from standalone rewrite
bullets. Lower reference loss therefore did not establish useful CV acceptance.
This was a non-blinded maintainer review of all seven outputs per variant, not
an independent benchmark, a causal comparison against the earlier training run,
or evidence of improved recruiter responses.

The completed cloud ZIP passed its source-side hash and archive checks. A host
download was initiated, but matching host bytes have not been verified. Keep
the runtime artifacts until that separate recovery gate passes. No private
corpus, prompts, raw outputs or weights are published here; no generated wording
or adapter has been promoted into application documents.

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
