# Local Qwen3 smoke evidence — 30 October 2026

**Runtime passed; tailoring-quality acceptance did not pass. No model promotion.**

Environment: Windows x86-64, Python 3.12.14, approximately 16 GB system RAM, CPU
execution with OMP/MKL threads 4. Packages: torch 2.10.0+cpu,
transformers 4.57.6, peft 0.18.1. `pip check` passed. Model:
Qwen/Qwen3-0.6B, revision `c1899de289a04d12100db370d81485cdf75e47ca`.
Public model files were downloaded explicitly outside the checkout and hashed;
no weights, private workspace or runtime logs are distributed here.

Command: `scripts/demo_finetuning.py` with a new external fictional workspace and
that local model directory. This uses the explicitly labelled synthetic review
fixture, not a real candidate or human-review claim.

| Observation | Actual result |
|---|---|
| Data | One train example, 841 tokens; one held-out example, 843 tokens |
| Method | LoRA rank 8 / alpha 16 / dropout 0.05; q_proj/v_proj; one epoch/optimizer step |
| Trainable parameters | 1,146,880 |
| Base held-out assistant-token NLL / perplexity | 0.922531 / 2.515649 |
| Adapter held-out assistant-token NLL / perplexity | 0.828618 / 2.290152 |
| Training interval including epoch evaluation | 146,145ms |
| Base / adapter teacher-forced evaluation | 29,673ms / 50,239ms |
| Separate adapter generation | 48 input tokens, 28 output tokens, 29,026 ms excluding model loading |
| Provider calls / submissions | 0 / 0 |
| Process outcome | Exit 0; adapter, result and inference records created privately |

This tiny same-fixture test is functional evidence, not generalization, improved
writing, throughput or a speed comparison. Its train/eval grouping prevents exact
job/output overlaps but does not make these synthetic examples statistically
independent. Teacher-forced evaluation timings do not establish adapter overhead.

## Observed quality failure and next acceptance gate

The inference prompt supplied only the fictional fact “Used SQL to query a
fictional sales dataset.” The generated bullet added “analyzed trends in customer
behavior,” unsupported by the input. It also wrapped the JSON in Markdown fences,
so the raw response did not satisfy strict JSON parsing. A lower held-out loss did
not prevent this factuality failure. Do not import or send this output as fact.

The inference function returned `review_required=true`,
`semantic_truth_verified=false`, `authority_granted=false` and `sent=false`.
Those boundaries remain necessary. No automatic host integration is enabled.
Before any promotion: collect genuinely independently reviewed diverse wording,
test unseen JDs and absent-skill/adversarial cases against the unchanged base,
require exact output-contract validation and independent factual/specificity review,
measure end-to-end latency including load costs, and reject unsupported additions.
Do not fabricate candidate experiences or synthetic reviews to increase dataset size.

## Repository checks

- Full standard suite: 315 tests passed in 790.625 s, including the first five new
  preparation regressions; final eight targeted regressions passed separately.
- Source hygiene: 293 UTF-8 files / ten canonical skills passed the bounded checker;
  this is not exhaustive privacy/security detection.
- Adapter synchronization, fictional preparation demo, skill validation and
  staged whitespace check passed. No real applications were sent in this QA.
- Remote CI is tracked on the PR/main run, not assumed successful by this document.

The experimental dependency profile pins direct packages only, not the full
transitive binary closure. CPU runtime evidence above does not certify other
hardware, Intel acceleration, CUDA, QLoRA, model sizes or deployment readiness.

## Reviewed rewrite pilot — 1 November 2026

**Runtime completed; all four generated outputs failed the strict contract.
The adapter remains unpromoted.** This is a separate run, not a repair of the
30 October smoke or a claim that local fine-tuning improves admission rates.

The external fictional workspace contained eight job/project groups sharing one
candidate/source packet: six training groups and two held-out groups. Its 32
reviewed statements included 15 changed paraphrases and 17 exact selections.
The annotation review was a separately prompted agent pass, not human review.
This small, shared-source corpus is not adequate evidence of generalization to
new candidates or unseen kinds of jobs. Twelve separately reserved cases were
not used in this training or generation run.

The same Windows CPU environment, local Qwen3-0.6B files and package versions
listed above were used. Configuration: one epoch, six optimizer steps, batch
size 1, maximum length 2,048, learning rate 0.0002, warmup fraction 0.1, seed 42;
LoRA rank 8 / alpha 16 / dropout 0.05 on q_proj/v_proj. The adapter had 1,146,880
trainable parameters. No model provider API was called.

| Training observation | Base | Adapter after one epoch |
|---|---:|---:|
| Held-out assistant-token NLL | 0.519127 | 0.300560 |
| Held-out perplexity | 1.680560 | 1.350615 |
| Evaluated assistant tokens | 863 | 863 |

Training plus epoch evaluation took 1,707,944 ms. Supervisor wall time, including
startup and the initial baseline evaluation, was 1,946,401 ms. These are different
measurement boundaries, not two estimates of the same interval.

Matched generation used every held-out example with system/user messages only,
greedy decoding, thinking disabled and a maximum of 768 new tokens per call.
Reference assistant answers were excluded. Calls ran serially with the same
decoding limits; raw outputs were neither repaired nor retried.

| Generation observation, two calls each | Base | Adapter |
|---|---:|---:|
| Input tokens | 2,324 | 2,324 |
| Output tokens | 423 | 1,229 |
| Generation time excluding loading, ms | 296,176 | 694,739 |
| Call wall time including loading, ms | 412,618 | 727,139 |
| Strict contract-valid outputs | 0 / 2 | 0 / 2 |

The paired supervisor completed with exit 0 in 1,193,803 ms. Its runtime completion
does not make an output acceptable. Both base responses used Markdown fences and
omitted the required top-level structure. Both adapter responses contained
duplicate JSON keys. Different output lengths, loading costs and this tiny
workload prevent a general inference-speed or cost-saving claim. Host reasoning
tokens and subscription cost were unavailable; they are not recorded as zero.

A separately prompted agent reviewed four shuffled, opaque cases against their
complete JD/source packets without the operator key, model labels, timings or
reference assistant answers. All four output-hash bindings were verified before
mapping the returned judgments into a separate runs copy. Original runs remained
unchanged. The agent's actual model identity and usage were unavailable; this is
not authenticated or human review.

The review found source-entailed task prose in both variants. Both base drafts
preserved project scope; both adapter drafts placed classroom projects under
employment, introducing unsupported context despite retaining the original task
sentences. The reviewer therefore failed whole-draft factuality and qualifier
preservation for both adapter outputs. Each draft received an editorial
specificity score of 3/5. These four judgments are descriptive observations,
not a statistically established model ranking or approved training labels.

See the [blinded review procedure](WORDING_EVALUATION.md) for separate factuality,
qualifier and JD-specificity judgments. Favorable prose judgments cannot
override raw contract failures. Keep the existing reviewed writing workflow;
do not install this adapter as a default, import its wording into a CV, or infer
an interview-rate improvement. Private raw outputs, source packets, review keys,
model weights and runtime paths are excluded from the source distribution.
