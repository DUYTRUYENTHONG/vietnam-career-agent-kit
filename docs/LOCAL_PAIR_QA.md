# Local paired-generation evidence — 31 October 2026

**Runtime completed; both generated outputs failed the strict JSON contract.**
No model was promoted, wording imported, independent factual review fabricated,
candidate trained on, provider contacted or application submitted by this QA.

Windows x86-64, Python 3.12.14; CPU Qwen/Qwen3-0.6B revision
`c1899de289a04d12100db370d81485cdf75e47ca`, OMP/MKL threads 4. Environment:
torch 2.10.0+cpu, transformers 4.57.6, peft 0.18.1.

The new CLI used the existing explicitly fictional legacy version 1.0 export
and its matching one-step LoRA run. There was one held-out job/output group;
fixture reviews were synthetic test data, not independent candidate reviews.
No new training or download occurred. Both variants received the same system/user
messages, without the reference assistant answer, with greedy decoding and
512 maximum new tokens. This does **not** evaluate the later version 1.1 prompt.

| Observed measurement | Base | LoRA |
|---|---:|---:|
| Input tokens | 418 | 418 |
| Output tokens | 380 | 306 |
| Generation time, excludes loading | 95,317 ms | 191,684 ms |
| Whole call time, includes loading/imports | 151,956 ms | 201,177 ms |
| Strict JSON contract validity | Failed | Failed |
| Independent factuality/specificity score | Not recorded | Not recorded |

Total runner time was 373,070 ms, including validation/hashing and both calls.
The raw outputs were kept without fence removal or repair. Private provenance,
partial evidence, paired runs, strict comparison and a final runtime marker were
written; three artifact SHA-256 bindings were verified. Missing factuality scores
remain null, not zero or a passing label.

In a separate explicit observation step, the two actual generation measurements
were imported into the existing performance tracker in the fictional workspace.
Both have accepted=false; costs, cached-input tokens and reasoning tokens remain
unknown. The paired runner itself does not write performance/database records.

An unblinded maintainer inspection of the raw text found that the base echoed
fact objects rather than the required language/sections output; the adapter
returned flat fact objects in sections plus an extra pending field. Neither
supplied the required grouped statement structure. This explains the observed
format mismatch, not its sole cause, and is not an independent semantic review.

Other focused/full regression tests ran concurrently for part of this observation.
The timings have different scopes and are not a controlled adapter-overhead,
optimization, throughput or previous-run comparison. This tiny same-fixture run
does not establish generalization, CV quality or an admission/interview uplift.

## Deterministic QA

- Eleven final focused orchestration tests passed in 123.031 seconds. They patch
  model generation and use fictional portable workspaces, including exact
  held-out prompts, raw failures, explicit caps without sampling, stale/revoked
  reviews, training/base identity mismatch, private paths and incomplete runs.
- Public-source hygiene passed for 316 UTF-8 files and ten skill/wrapper sets;
  generated-wrapper synchronization and diff whitespace checks passed.
- The generic preflight initially included ignored optional environments and
  hit its 80 third-party pattern limit. A source-only 315-file snapshot rerun
  found zero conflict markers and zero suspicious patterns. This is bounded
  source hygiene, not exhaustive security or dependency assurance.
- Complete standard-library suite: **372 tests passed in 1,321.277 seconds**.
  Part of the run overlapped local CPU model experiments; this is correctness
  evidence, not a speed comparison. Final source hygiene and wrapper checks passed.
- All six exact-head protected-branch CI checks remain required before merge.
  A completed local/model run does not establish remote CI success.

The actual model process loaded the runner before the final raw-text/symlink
guards were added; focused regressions cover those final guards separately.
The exercised normal local path and model outputs were within those bounds.
See [interface and limits](LOCAL_PAIR_GENERATION.md).

## Current version 1.1 prompt experiment

A second explicit experiment used the existing fictional
`cv-wording-json-2` export and a newly trained matching one-step LoRA adapter.
Same provisioned Qwen3-0.6B revision/environment, CPU and four OMP/MKL threads;
one training example and one held-out job/output group with synthetic fixture
reviews. No candidate data, new download or independent human-review claim.

The complete assistant-masked examples were 1,556 train / 1,558 held-out tokens,
within the unchanged 2,048-token training limit without truncation. Training plus
epoch evaluation took 301,239 ms. Held-out assistant-token NLL fell from
0.438964 to 0.318782 (perplexity 1.551100 to 1.375452); these are teacher-forced
loss measurements, not faithful or useful free-generation evidence.

Matched generation used only the same held-out system/user messages, greedy
decoding and 1,024 maximum new tokens:

| Measurement | Base | New LoRA |
|---|---:|---:|
| Input tokens | 1,133 | 1,133 |
| Output tokens | 1,024 | 757 |
| Generation time, excludes loading | 551,020 ms | 367,228 ms |
| Whole call time, includes loading/imports | 580,714 ms | 398,454 ms |
| Strict JSON contract validity | Failed | Failed |
| Independent factuality/specificity score | Not recorded | Not recorded |

Total runner wall time was 992,087 ms. Three final artifact hash bindings were
rechecked. Raw model outputs remain unchanged; there was no repair, fact/CV
import, positive review label or model promotion. Tests overlapped part of the
CPU experiment; this is one observed workload, not a controlled speed comparison.

Unblinded maintainer inspection found additional problems beyond fences: the
base hit its output cap mid-object, used source IDs instead of fact IDs, and
omitted the education statement's fictional qualifier. The adapter linked the
SQL fact F1 to unrelated employment, education and language statements and used
invalid locators; both supplied extra/wrong structural fields. This inspection
is separate from strict validation and is not an independent semantic score.

**Neither model is accepted for tailoring.** The lower loss and fuller prompt
did not establish valid, source-faithful generation in this fixture. Preserve the
working host-agent drafting/review flow. Before another quality experiment,
prepare diverse genuinely independently reviewed data, held-out/absent-skill and
qualifier cases, and an explicit hardware/latency plan. Do not repeat tiny-fixture
training to manufacture a passing quality claim. Larger Qwen variants remain
unbenchmarked candidates, not automatic upgrades or an approved default.
