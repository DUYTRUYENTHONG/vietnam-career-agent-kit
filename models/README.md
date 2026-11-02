# Experimental CV-tailoring models

Made by **DUYTRUYENTHONG**, shared freely for community experimentation.
Kit source is MIT; Qwen derivatives retain their separate Apache-2.0 terms and
attribution. See the [upstream license](https://huggingface.co/Qwen/Qwen3-0.6B/blob/main/LICENSE).

**No released adapter is accepted for live CV tailoring.** Training completion
and lower loss do not demonstrate factual writing or better recruitment outcomes.
Start with the [fork-and-train guide](../docs/FINE_TUNING_START.md).

| Experiment | Data / runtime | Observed acceptance | Distribution |
|---|---|---|---|
| Qwen3-0.6B smoke, 30 Oct 2026 | Fictional; 1 train / 1 held-out example; Windows CPU | Unsupported addition and invalid JSON | Experimental research adapter |
| Qwen3-0.6B contract-v2, 31 Oct 2026 | Fictional; 1 train / 1 held-out example; Windows CPU | Invalid JSON/links; historical raw JD and structured requirements inconsistent | Experimental research adapter; preserve defect for inspection |
| Qwen3-0.6B rewrite pilot, 1 Nov 2026 | Fictional; 6 train / 2 held-out groups; Windows CPU | Both adapter outputs invalid JSON; project context incorrectly changed to employment | Experimental research adapter |
| Qwen3-8B QLoRA pilot, 1 Nov 2026 | 5 synthetic examples; Colab T4; 8 epochs / 16 steps | No independent held-out quality acceptance; original examples contain unsupported expansions | Report only; host archive recovery unverified, weights excluded |
| Personal-CV corpus | Private source/reconciliation staging | No training-ready export or completed personal-model training | Not distributed |

The [research pre-release](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/releases/tag/training-pilots-v0.1.0)
contains the three available adapters for inspection and failure reproduction.
Its actual asset list determines availability. Public identities and gates are
in [experiments.json](experiments.json); measured evidence is in
[local QA](../docs/LOCAL_FINETUNING_QA.md).

Each archive contains unchanged LoRA safetensors, a publication-copy config,
model card, exact historical fictional train/evaluation JSONL, sanitized training
provenance, publication/change record, file
checksums, upstream LICENSE and NOTICE. The config replaces the original machine
path with `Qwen/Qwen3-0.6B` and its exact pinned revision; this change is explicit,
and original private artifacts remain unchanged. Full base weights and tokenizer
files are not bundled. Use the matching base tokenizer.

All three publication copies loaded with the measured CPU environment and
completed a two-token fictional generation check. This verifies packaging/load
compatibility only; it does not repair their historical quality failures.

Verify the archive against release `SHA256SUMS.txt`, then its internal hashes.
Extract only expected files into a new directory outside the checkout. Checksums
bind bytes, not publisher authenticity, factuality or model quality. No archive
contains candidate CVs, tracker rows, account identifiers or source packets.

All three adapters require revision `c1899de289a04d12100db370d81485cdf75e47ca`.
The download helper resolves the current Hub revision, which can differ: compare
its manifest and stop on mismatch. Never edit identities merely to pass checks.
Redistribution copies do not supply the private source/review bindings required
by the matched runner. Reproduce your own export/training to use that runner.

The 8B pilot needed notebook-specific compatibility repairs. Exact package
versions and its resolved base commit were not captured; its temporary runtime
later disconnected. This is not a reproducible supported Colab recipe. The
local runner remains CPU/CUDA LoRA; this publication does not implement QLoRA.

Contribute code, fictional fixtures and deliberately anonymized aggregate results
through a checked PR. Keep personal corpora and models trained on them private
unless every affected person approved the exact public disclosure. Adapters may
memorize training text even when contact headers were omitted.
