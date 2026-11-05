# Job requirements data pipeline

The local collector/cleaner collects explicitly selected captured JDs, preserves raw
provenance, normalize without changing meaning, deduplicate exact text and create
a source-bound extraction review queue. Reuse the existing assessment, wording
review, learning export and optional trainer for subsequent supervised CV pairs.

The pipeline must support a bounded JSONL snapshot input and an explicit read-only
legacy `jobs` projection. It must not initialize/migrate a tracker, fetch arbitrary
websites, infer candidate skills, invent extraction labels, upload data or train.
Legacy summaries and unknown captures stay labelled; collection does not turn
them into complete primary JDs. Closed or geographically unsuitable roles can
remain research data without becoming application targets.

Required snapshot fields: `id`, `employer`, `job_key`, `source_url`, `raw_text`,
`source_kind` (`full_jd`, `excerpt`, `assessment_summary`, `unknown`). Optional
`captured_utc`, `source_updated_utc` and `requirements` preserve caller observations.
Each supplied requirement has `id`, exact `quote` and `kind` (`required`,
`preferred`, `unknown`). Every quote must occur in that snapshot's raw text.
Classification remains a caller claim pending review, even when structurally valid.

Use NFC, normalized line endings and whitespace only. Keep negation, years,
currency, qualifiers, original bytes/text hashes and all source references.
Exact cleaned document/requirement duplicates may share content records; their
job identities must remain distinct. Conflicting requirement kinds are explicit.
No fuzzy/semantic duplicate or complete extraction guarantee is permitted.

Acceptance requires fictional regressions for invalid/stale quotes, Unicode,
negation/units, duplicate provenance, classification conflict, private output
boundaries, interruption/overwrite refusal, bounded legacy read-only behavior and
no tracker changes. A manifest written last identifies a complete immutable run.
Actual processing time/bytes/counts are measurable; model tokens remain unavailable
because this stage makes no model call. Data stays private, including raw JDs
which may contain identifiers. Normalization is not anonymization.

Next stages use existing contracts: host extraction/review against raw captures,
`import-jd`, complete fact-backed `assess`, source-bound tailoring and independent
wording review, `learning-export`/`learning-check`, grouped evaluation and the
explicit opt-in local trainer. A requirements corpus alone is not a supervised
CV-tailoring dataset and must be rejected by the trainer's existing export checks.
The legacy bridge grants no portable-ledger migration or write authority.

## Run locally

No Docker, model SDK, network access or second AI API is needed for collection.
Use an existing authorized browser/discovery connector to capture sources first.
Do not install a new scraper or infer platform permission from this command.

```console
python scripts/requirements_corpus.py --snapshots ../private/snapshots.jsonl --output ../private/corpora/run-001
python scripts/requirements_corpus.py --legacy-ledger ../private/data/applications.sqlite3 --output ../private/corpora/legacy-001
```

Both inputs are bounded to 1,000 records and 20 MB; a single raw text is at most
1 MB. Expanded requirement provenance also has a 20 MB bound, preventing repeated
quotes from multiplying large metadata without limit. `--limit` can lower the record cap; exceeding it fails rather than silently
omitting jobs. The legacy collector reads one fixed `jobs` projection in SQLite
read-only mode. It preserves unknown capture times as null and uses the recorded
update time separately. It does not label historical summaries as complete JDs.
The portable `workflow.sqlite3` input remains the normal versioned `import-jd`
contract, not this older schema projection.

Optional `--extractions ../private/extractions.json` attaches host-selected
quotes to either input. The sidecar has `schema_version` equal to
`requirements-extractions-v1` and `records` containing `id`, `raw_text_sha256`
and `requirements`. Every snapshot and requirement ID is explicit; a changed
raw hash, absent quote, repeated ID or pre-existing extraction fails the run.
This does not promote source kinds or review status. Input shapes are documented
in [the schema](../schemas/requirements-corpus.schema.json).

The new directory contains:

- `raw_snapshots.jsonl`: unmodified input text, identities and annotations.
- `documents.jsonl`: unique conservatively cleaned text, retaining every source.
- `requirement_candidates.jsonl`: exact-quote candidates, source links, claimed
  kinds, classification conflicts and pending extraction review.
- `manifest.json`: completion marker, file hashes, counts, observed processing
  milliseconds and explicit absent model usage/training/upload.

Without explicit quote annotations, collection produces zero requirement
candidates. It does not guess requirements from menus, summaries or browser AX
trees. Use the host to select source quotes, then run a new export. Review against
the complete JD before importing assessed requirements or preparing model pairs.
Do not feed this corpus directly to the existing LoRA trainer.

## Compatibility and validation

Experimental standard-library CLI. Fictional tests cover current/stale sidecars,
NFC and raw hashes, negation/units, duplicate provenance, kind conflicts, bounded
read-only legacy collection, output boundaries, exclusive exports and CLI errors.
These checks do not verify live source liveness, capture completeness, semantic
review, automatic PII removal or an improvement in a trained model. No native MCP
tool, scheduled collection or automatic retraining is added by this increment.
