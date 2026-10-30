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
