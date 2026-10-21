---
name: application-ledger
description: Maintain the single private application tracker with deduplication, exact package provenance, approvals and evidence-backed statuses. Do not mark preparation as submission or store candidate data in the public kit.
---

Read ../../../docs/DATA_CONTRACT.md and ../../../prompts/MASTER_PROMPT.md. Inputs: approved external private directory, job identity, factual events, actor and evidence. The coordinator alone writes the ledger.

Use scripts/kit.py for supported local operations; inspect --help rather than assuming commands. Store raw JD separately, canonical metadata, UTC events displayed in Asia/Ho_Chi_Minh and content hashes. Deduplicate stable IDs; empty requisition IDs must not collapse jobs. Keep meaningful URL parameters and flag fuzzy duplicates for review.

Never equate discovered, assessed, drafted, reviewed, approved, form-prepared or awaiting-manual-submission with submitted. Distinguish observed confirmation, user report and uncertainty. Unsupported lifecycle operations must be recorded explicitly as unavailable rather than simulated. Submitted packages are immutable snapshots; new edits create versions.

Record approval only after a real candidate response, tied to exact company/job/recipient/files/answers/consents/terms. Changed bytes or input invalidate it. A confirmation text file is provenance bookkeeping, not proof that a human authored it. Never manufacture approval or weaken a policy to pass a check.

Output private ledger/status and missing actions. Keep retention configurable; no deletion or public export without instruction. Escape formula-leading CSV cells if export is added. No network, browser or outbound messaging side effects are granted.
