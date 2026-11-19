# Local evidence pairing pilot

This optional experiment matches an individual job seeker's confirmed quotes to individual requirements in a vacancy. Candidate-facing output consists of the requirement matrix, mandatory coverage, exact quotes for an extractive CV draft and the original record references where available. A person checks the evidence before using the existing assessment and draft commands. This pilot is Experimental. It does not estimate the probability of employment or send applications.

## Reproduce the public QA run

From the repository root, use a new private working directory outside the checkout. With only standard Python, run:

```bash
mkdir -p ../pairing-runs
python scripts/evidence_bench.py evaluate --output ../pairing-runs/lexical.json
python -c "import json; d=json.load(open('examples/fictional/evidence-pairing.json', encoding='utf8')); print(json.dumps(d['cases'][4]['packet'], ensure_ascii=False))" > ../pairing-runs/example.json
python scripts/evidence_bench.py preview --packet ../pairing-runs/example.json --output ../pairing-runs/preview.json
```

For an actual user, first follow the kit's normal local import and confirmation steps. An initialized, confirmed workspace with a structured job can export a read-only packet:

```bash
python scripts/kit.py --data-dir "$CAREER_WORKSPACE" evidence-packet --job-id 1 > ../pairing-runs/my-packet.json
python scripts/evidence_bench.py preview --packet ../pairing-runs/my-packet.json --output ../pairing-runs/my-review.json
```

Packet JSON contains private CV excerpts. Keep it outside Git. The projection includes only confirmed quotes in the listed work-relevant fields in core/evidence_pairing.py. Review omitted or custom field types, personal preferences and any identifiers within the quotes yourself. Re-export after any edit to source documents. Free-standing packets are not authenticated and do not update a workspace. The canonical assessment continues to include preferences, hard conditions and vacancy status. A research contradiction carries supporting evidence and needs human interpretation before using the canonical matrix's different vocabulary.

For Qwen, create a separate Python environment. The supplied historical report describes Python 3.12 on Linux, CPU bfloat16, torch 2.10.0+cpu, transformers 5.3.0, peft 0.18.1 and accelerate 1.15.0. Set the following variables in the same shell. Use Python from the environment for every model command.

```bash
python -m venv ../pairing-env
. ../pairing-env/bin/activate
python -m pip install 'torch==2.10.0' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-qwen35-pilot.in
export REV=2fc06364715b967f1860aea9cf38778875588b17
export MODEL_DIR=../pairing-runs/qwen35-08b
hf download Qwen/Qwen3.5-0.8B --revision "$REV" --local-dir "$MODEL_DIR"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=5 MKL_NUM_THREADS=5
python scripts/evidence_bench.py evaluate --backend qwen --model-dir "$MODEL_DIR" --model-revision "$REV" --output ../pairing-runs/base.json
python scripts/evidence_bench.py train --model-dir "$MODEL_DIR" --model-revision "$REV" --epochs 1 --seed 17 --adapter-dir ../pairing-runs/adapter --output ../pairing-runs/training.json
python scripts/evidence_bench.py evaluate --backend qwen --model-dir "$MODEL_DIR" --model-revision "$REV" --adapter ../pairing-runs/adapter --output ../pairing-runs/lora.json
python scripts/evidence_bench.py preview --backend qwen --model-dir "$MODEL_DIR" --model-revision "$REV" --adapter ../pairing-runs/adapter --packet ../pairing-runs/example.json --output ../pairing-runs/model-review.json
```

Training uses only the fixture train split, completion-only loss and rank-4 LoRA on language attention q/v projections. Inference is greedy with thinking disabled and up to 64 generated tokens. The revision flag records the caller's stated source; it is not authenticated upstream provenance. Each run records observed local checkpoint/adapter SHA-256 values and marks upstream origin unverified. Match those bytes to the upstream digest independently. JSON generation records actual input/output tokens and synchronized generation-only latency; choice decoding currently has no per-call generation telemetry. Select `--device cuda` explicitly for GPU work; unavailable CUDA fails without fallback. CPU is the explicit default. Training has 10% linear warmup, and never accepts model quality automatically. Base/adapter held-out comparison and independent semantic review remain separate required experiment steps. No automatic installation, download or remote inference takes place in the kit.

You can repeat evaluation with `--top-k 2` for lexical retrieval. With `--decoding choice --top-k 4` the model chooses one valid answer by next-token logits. This exploratory comparator was added after the original development/debug run; it supports at most four facts and pairs of citations. It is prompt-order sensitive and can still give an incorrect interpretation. The raw JSON mode has no evidence-set size-two restriction.

## Supplied historical observations — not reproduced by this integration

The fictional fixture has 7 independent author-constructed cases, 25 requirements, and Vietnamese, English and mixed pairs. Train has 10 requirements in 3 cases, development has 3 in 1, test has 12 in 3. Test contains three of each label. The split checker rejects cross-partition declared groups and normalized exact text matches. A semantic near-duplicate audit and independent human labels still need to be collected for a publication. These public cases have already been inspected. They cannot serve as the final sealed benchmark.

| Test system, same 12 requirements | Valid outputs | Jointly correct label and evidence | Label macro-F1 | Citation micro-F1 | False support among 6 unknown/conflict |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 + lexical coverage rule | 12 | 7 | .517 | .947 | 4 |
| Qwen3.5-0.8B, strict JSON | 0 | 0 | .000 | .000 | 0 (all invalid) |
| Same checkpoint + LoRA, strict JSON | 12 | 6 | .428 | .778 | 3 |
| Unadapted Qwen, bounded choice | 12 | 4 | .361 | .381 | 4 |
| Same adapter, bounded choice | 12 | 4 | .361 | .381 | 4 |

Study these as engineering observations. For example, the adapted JSON model labeled the night-shift conflict partial and the missing drone licence unknown. All three explicit contradictions were missed in that configuration. Learning to generate the contract improved validity while the lexical system retained the best observed joint count. In the equal-format bounded-choice comparison, adding the adapter changed none of the aggregate scores. Checking valid IDs by itself does not check entailment. Invalid answers remain in denominators. Citation F1 rewards locating the evidence even when its meaning is misclassified. This fixture has a single reference evidence set per requirement; accepting multiple adjudicated alternatives is a paper milestone.

The supplied historical package describes a separate pilot adapter. No adapter is distributed or runtime-verified by this integration; inspect the actual external artifacts before claiming one is available. The public code has no model or candidate binaries. Existing Qwen3 bullet-wording experiments are different tasks with different test cases, and must not be compared numerically with this table. See [prior experiment reports](../models/README.md).

## Research and validation still required

The bilingual candidate-side evidence-matching hypothesis needs a separately verified
literature review, licensed independent data and human labels. The supplied research
brief is a planning artifact; model revisions, external citations and historical
performance claims require verification before use in a publication. Neither the
synthetic fixture nor the reported scores establish CV quality or hiring outcomes.

The [research brief](../prompts/QWEN35_EVIDENCE_RESEARCH.md) describes the remaining
annotation, controlled-comparison and human-utility work. No research milestone is
completed simply by adding this optional experimental code.
